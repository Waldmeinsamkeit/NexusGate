import json
import tempfile
import unittest
from pathlib import Path

from nexusgate.app import (
    _anthropic_request_to_openai,
    _anthropic_response_from_openai,
    _responses_request_to_openai,
    _responses_response_from_openai,
    _responses_stream_from_openai,
    _responses_response_output_text,
)
from nexusgate.local_proxy import ClientSyncService, LocalKeyManager


class LocalProxyTests(unittest.TestCase):
    def test_local_key_manager_generates_and_reuses_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "secrets.json"
            manager = LocalKeyManager(configured_key=None, store_path=str(store))
            first = manager.resolve()
            self.assertTrue(first.api_key.startswith("ng-"))
            self.assertIn(first.source, {"generated_store", "store"})

            manager2 = LocalKeyManager(configured_key=None, store_path=str(store))
            second = manager2.resolve()
            self.assertEqual(first.api_key, second.api_key)
            self.assertEqual(second.source, "store")

    def test_client_sync_updates_codex_and_claude_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex = Path(tmp) / "config.toml"
            claude = Path(tmp) / "settings.json"
            codex.write_text(
                '[model_providers.OpenAI]\nname = "OpenAI"\nbase_url = "https://old.example/v1"\n',
                encoding="utf-8",
            )
            claude.write_text("{}", encoding="utf-8")

            service = ClientSyncService(
                codex_config_path=str(codex),
                claude_settings_path=str(claude),
                codex_base_url="http://127.0.0.1:8000/v1",
                claude_base_url="http://127.0.0.1:8000",
            )
            status = service.sync_all("ng-local-key")
            self.assertEqual(status.status, "ok")
            self.assertEqual(set(status.synced_clients), {"codex", "claude"})

            codex_text = codex.read_text(encoding="utf-8")
            self.assertIn('base_url = "http://127.0.0.1:8000/v1"', codex_text)
            self.assertIn("requires_openai_auth = false", codex_text)
            self.assertIn('wire_api = "responses"', codex_text)

            claude_obj = json.loads(claude.read_text(encoding="utf-8"))
            self.assertEqual(claude_obj["env"]["ANTHROPIC_BASE_URL"], "http://127.0.0.1:8000")
            self.assertEqual(claude_obj["env"]["ANTHROPIC_AUTH_TOKEN"], "ng-local-key")

    def test_anthropic_openai_mapping_and_response(self) -> None:
        req = {
            "model": "claude-sonnet-test",
            "system": "you are helpful",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
            "stream": False,
        }
        mapped = _anthropic_request_to_openai(req)
        self.assertEqual(mapped["model"], "claude-sonnet-test")
        self.assertEqual(mapped["messages"][0]["role"], "system")
        self.assertEqual(mapped["messages"][1]["content"], "hi")

        openai_payload = {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        anthropic_payload = _anthropic_response_from_openai(openai_payload, model="claude-sonnet-test")
        self.assertEqual(anthropic_payload["type"], "message")
        self.assertEqual(anthropic_payload["content"][0]["text"], "hello")
        self.assertEqual(anthropic_payload["usage"]["input_tokens"], 10)
        self.assertEqual(anthropic_payload["usage"]["output_tokens"], 5)

    def test_responses_openai_mapping_and_response(self) -> None:
        req = {
            "model": "gpt-4o-mini",
            "instructions": "be brief",
            "input": "hello",
            "stream": False,
            "max_output_tokens": 64,
        }
        mapped = _responses_request_to_openai(req)
        self.assertEqual(mapped["model"], "gpt-4o-mini")
        self.assertEqual(mapped["messages"][0]["role"], "system")
        self.assertEqual(mapped["messages"][1]["content"], "hello")
        self.assertEqual(mapped["max_tokens"], 64)

        openai_payload = {
            "choices": [{"message": {"content": "NEXUS_OK"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15},
        }
        responses_payload = _responses_response_from_openai(openai_payload, model="gpt-4o-mini")
        self.assertEqual(responses_payload["object"], "response")
        self.assertEqual(responses_payload["output_text"], "NEXUS_OK")
        self.assertEqual(responses_payload["usage"]["total_tokens"], 15)

    def test_responses_stream_emits_delta_and_completed(self) -> None:
        chunks = [
            {"choices": [{"delta": {"content": "NEXUS_"}}]},
            {"choices": [{"delta": {"content": "OK"}}]},
        ]
        events = b"".join(_responses_stream_from_openai(chunks, model="gpt-4o-mini")).decode("utf-8")
        self.assertIn("event: response.created", events)
        self.assertIn("event: response.output_item.added", events)
        self.assertIn("event: response.content_part.added", events)
        self.assertIn("event: response.output_text.delta", events)
        self.assertIn("event: response.output_item.done", events)
        self.assertIn("event: response.output_text.done", events)
        self.assertIn("event: response.completed", events)
        self.assertIn("NEXUS_OK", events)

    def test_responses_output_text_extracts_from_output_array(self) -> None:
        payload = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "NEXUS_"},
                        {"type": "output_text", "text": "OK"},
                    ],
                }
            ]
        }
        self.assertEqual(_responses_response_output_text(payload), "NEXUS_OK")


if __name__ == "__main__":
    unittest.main()
