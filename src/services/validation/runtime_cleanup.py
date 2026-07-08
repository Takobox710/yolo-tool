from __future__ import annotations

import gc


def release_inference_runtime() -> None:
    torch = None
    try:
        import torch as _torch

        torch = _torch
    except Exception:
        torch = None
    gc.collect()
    if torch is None:
        return
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass
