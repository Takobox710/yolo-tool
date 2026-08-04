from __future__ import annotations

import json

from src.bootstrap.runtime_protocol import emit_runtime_error, emit_runtime_response

def _run_sam_assist_runtime_cli_impl(argv: list[str]) -> int:
    import sys

    from src.services.annotation.sam_runtime import SamAssistRuntime

    del argv
    runtime = SamAssistRuntime()

    emit_response = emit_runtime_response
    emit_error = emit_runtime_error

    try:
        for raw_line in sys.stdin:
            line = str(raw_line).strip()
            if not line:
                continue
            try:
                command = json.loads(line)
            except json.JSONDecodeError:
                continue
            request_id = str(command.get("request_id") or "")
            action = str(command.get("action") or "")
            try:
                if action == "shutdown":
                    emit_response(request_id, {"state": "shutdown"})
                    return 0
                if action == "load_model":
                    result = runtime.load_model(
                        str(command.get("checkpoint_path") or ""),
                        str(command.get("config_name") or ""),
                        int(command.get("model_generation") or 0),
                        str(command.get("runtime_kind") or "sam2"),
                    )
                    emit_response(request_id, result)
                    continue
                if action == "set_image":
                    result = runtime.set_image(
                        str(command.get("image_path") or ""),
                        int(command.get("image_generation") or 0),
                        int(command.get("model_generation") or 0),
                    )
                    emit_response(request_id, result)
                    continue
                if action == "predict_point":
                    result = runtime.predict_point(
                        float(command.get("x") or 0.0),
                        float(command.get("y") or 0.0),
                        int(command.get("image_generation") or 0),
                        int(command.get("model_generation") or 0),
                        bool(command.get("multimask_output", False)),
                        float(command.get("minimum_score") or 0.0),
                        int(command.get("minimum_area") or 4),
                        float(command.get("simplification_ratio") or 0.002),
                    )
                    result["x"] = float(command.get("x") or 0.0)
                    result["y"] = float(command.get("y") or 0.0)
                    emit_response(request_id, result)
                    continue
                emit_error(request_id, f"不支持的 SAM 运行时命令：{action}")
            except Exception as exc:
                emit_error(request_id, str(exc))
        return 0
    finally:
        runtime.close()

