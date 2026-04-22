from __future__ import annotations

from pathlib import Path

# Compatibility shim: actual backend package lives in back/nexusgate.
_BACK_PACKAGE = Path(__file__).resolve().parent.parent / "back" / "nexusgate"
__path__ = [str(_BACK_PACKAGE)] if _BACK_PACKAGE.exists() else []

