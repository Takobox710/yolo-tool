from __future__ import annotations

import json

def _run_model_labels_cli_impl(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("Usage: --yolo-model-labels <model-path>")
    from src.services.annotation import load_model_labels

    labels = load_model_labels(argv[0])
    sys_stdout = json.dumps(labels, ensure_ascii=False)
    print(sys_stdout, flush=True)
    return 0

