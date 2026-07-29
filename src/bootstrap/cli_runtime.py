from __future__ import annotations

import json

from src.bootstrap.cli_common import _parse_key_values

def _run_runtime_probe_cli_impl(argv: list[str]) -> int:
    from src.services.runtime.release_manifest import check_runtime_compatibility

    del argv
    compatibility = check_runtime_compatibility()
    print(
        json.dumps(
            {
                "ok": compatibility.compatible,
                "runtime_version": compatibility.runtime_version,
                "required_runtime_version": compatibility.required_runtime_version,
                "reason": compatibility.reason,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if compatibility.compatible else 1



def _run_remove_managed_models_cli_impl(argv: list[str]) -> int:
    from src.services.runtime import remove_managed_models
    from src.shared.paths import ROOT

    del argv
    try:
        removed = remove_managed_models(ROOT)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {"ok": True, "removed": [str(path) for path in removed]},
            ensure_ascii=False,
        )
    )
    return 0



def run_runtime_probe(argv: list[str]) -> int:
    return _run_runtime_probe_cli_impl(argv)


def run_remove_managed_models(argv: list[str]) -> int:
    return _run_remove_managed_models_cli_impl(argv)


__all__ = ["run_remove_managed_models", "run_runtime_probe"]
