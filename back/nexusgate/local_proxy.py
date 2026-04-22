from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LocalKeyState:
    api_key: str
    source: str


class LocalKeyManager:
    def __init__(self, configured_key: str | None, store_path: str) -> None:
        self.configured_key = configured_key.strip() if configured_key else None
        self.store_path = Path(store_path).expanduser()

    def resolve(self) -> LocalKeyState:
        if self.configured_key:
            return LocalKeyState(api_key=self.configured_key, source="env")

        stored = self._load_stored_key()
        if stored:
            return LocalKeyState(api_key=stored, source="store")

        generated = f"ng-{secrets.token_urlsafe(24)}"
        self._save_key(generated)
        return LocalKeyState(api_key=generated, source="generated_store")

    def _load_stored_key(self) -> str | None:
        if not self.store_path.exists():
            return None
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        value = payload.get("local_api_key")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _save_key(self, key: str) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps({"local_api_key": key}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


@dataclass(slots=True)
class SyncStatus:
    status: str = "ok"
    synced_clients: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ClientSyncService:
    def __init__(
        self,
        codex_config_path: str,
        claude_settings_path: str,
        codex_base_url: str,
        claude_base_url: str,
    ) -> None:
        self.codex_config_path = Path(codex_config_path).expanduser()
        self.claude_settings_path = Path(claude_settings_path).expanduser()
        self.codex_base_url = codex_base_url
        self.claude_base_url = claude_base_url

    def sync_all(self, local_api_key: str) -> SyncStatus:
        state = SyncStatus()

        try:
            self._sync_codex(local_api_key)
            state.synced_clients.append("codex")
        except Exception as exc:
            state.errors.append(f"codex: {exc}")

        try:
            self._sync_claude(local_api_key)
            state.synced_clients.append("claude")
        except Exception as exc:
            state.errors.append(f"claude: {exc}")

        if state.errors:
            state.status = "degraded"
        return state

    def _sync_codex(self, local_api_key: str) -> None:
        text = ""
        if self.codex_config_path.exists():
            text = self.codex_config_path.read_text(encoding="utf-8")

        if "[model_providers.OpenAI]" not in text:
            if text and not text.endswith("\n"):
                text += "\n"
            text += (
                "\n[model_providers.OpenAI]\n"
                'name = "OpenAI"\n'
                f'base_url = "{self.codex_base_url}"\n'
                'wire_api = "responses"\n'
                "requires_openai_auth = true\n"
            )
        else:
            pattern = r"(\[model_providers\.OpenAI\][\s\S]*?\n)base_url\s*=\s*\"[^\"]*\""
            if re.search(pattern, text):
                text = re.sub(
                    pattern,
                    rf'\1base_url = "{self.codex_base_url}"',
                    text,
                    count=1,
                )
            else:
                text = text.replace(
                    "[model_providers.OpenAI]\n",
                    f'[model_providers.OpenAI]\nbase_url = "{self.codex_base_url}"\n',
                    1,
                )

        text = self._upsert_provider_kv(text, "wire_api", '"responses"')
        text = self._upsert_provider_kv(text, "requires_openai_auth", "false")

        self.codex_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.codex_config_path.write_text(text, encoding="utf-8")
        self._set_user_env("OPENAI_API_KEY", local_api_key)

    @staticmethod
    def _upsert_provider_kv(text: str, key: str, value: str) -> str:
        section_pat = r"(\[model_providers\.OpenAI\][\s\S]*?)(\n\[|$)"
        match = re.search(section_pat, text)
        if not match:
            return text
        section = match.group(1)
        if re.search(rf"(?m)^\s*{re.escape(key)}\s*=", section):
            section = re.sub(
                rf"(?m)^(\s*{re.escape(key)}\s*=\s*).*$",
                rf"\1{value}",
                section,
            )
        else:
            if not section.endswith("\n"):
                section += "\n"
            section += f"{key} = {value}\n"
        return text[: match.start(1)] + section + text[match.end(1) :]

    def _sync_claude(self, local_api_key: str) -> None:
        data: dict[str, Any] = {}
        if self.claude_settings_path.exists():
            try:
                data = json.loads(self.claude_settings_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        env = data.get("env")
        if not isinstance(env, dict):
            env = {}
        env["ANTHROPIC_BASE_URL"] = self.claude_base_url
        env["ANTHROPIC_AUTH_TOKEN"] = local_api_key
        data["env"] = env

        self.claude_settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.claude_settings_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _set_user_env(key: str, value: str) -> None:
        os.environ[key] = value
        if os.name != "nt":
            return
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                0,
                winreg.KEY_SET_VALUE,
            ) as env_key:
                winreg.SetValueEx(env_key, key, 0, winreg.REG_EXPAND_SZ, value)
        except Exception:
            return
