from __future__ import annotations

import os
import subprocess


def hidden_subprocess_kwargs() -> dict[str, int]:
    if os.name != "nt":
        return {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return {"creationflags": flag} if flag else {}
