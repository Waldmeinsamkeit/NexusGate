import unittest

from nexusgate.gateway import LiteLLMGateway


class GatewayRoutingTests(unittest.TestCase):
    def test_llmapi_prefix_injects_api_base_and_key(self) -> None:
        gateway = LiteLLMGateway(
            llmapi_base_url="https://example-llmapi.com/v1",
            llmapi_api_key="sk-third-party",
        )
        payload = {"model": "llmapi/gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]}
        routed = gateway._inject_third_party_route(dict(payload))

        self.assertEqual(routed["model"], "openai/gpt-4o-mini")
        self.assertEqual(routed["api_base"], "https://example-llmapi.com/v1")
        self.assertEqual(routed["api_key"], "sk-third-party")

    def test_non_prefixed_model_keeps_original_payload(self) -> None:
        gateway = LiteLLMGateway(
            llmapi_base_url="https://example-llmapi.com/v1",
            llmapi_api_key="sk-third-party",
        )
        payload = {"model": "claude-sonnet-4-5-20250929", "messages": [{"role": "user", "content": "hi"}]}
        routed = gateway._inject_third_party_route(dict(payload))

        self.assertEqual(routed["model"], payload["model"])
        self.assertNotIn("api_base", routed)
        self.assertNotIn("api_key", routed)


if __name__ == "__main__":
    unittest.main()

