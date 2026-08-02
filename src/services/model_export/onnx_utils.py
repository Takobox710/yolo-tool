from __future__ import annotations

import json
import shutil
from pathlib import Path


def simplify_onnx_graph(source: str | Path, target: str | Path | None = None) -> Path:
    import onnxslim

    source = Path(source)
    destination = Path(target) if target is not None else source
    if destination.resolve() == source.resolve():
        temporary = source.with_name(f".{source.stem}.slim.onnx")
        onnxslim.slim(str(source), str(temporary))
        temporary.replace(source)
        return source
    onnxslim.slim(str(source), str(destination))
    return destination


def constrain_onnx_dynamic_axes(
    model_path: str | Path,
    *,
    dynamic_batch: bool,
    dynamic_height: bool,
    dynamic_width: bool,
    batch: int,
    imgsz: int,
) -> Path:
    import onnx

    path = Path(model_path)
    model = onnx.load(str(path), load_external_data=False)
    if not model.graph.input:
        raise ValueError("ONNX 模型没有输入。")
    input_tensor = model.graph.input[0]
    dimensions = input_tensor.type.tensor_type.shape.dim
    _set_dimension(dimensions, 0, dynamic_batch, "batch", batch)
    _set_dimension(dimensions, 2, dynamic_height, "height", imgsz)
    _set_dimension(dimensions, 3, dynamic_width, "width", imgsz)
    for output in model.graph.output:
        output_dimensions = output.type.tensor_type.shape.dim
        _set_dimension(output_dimensions, 0, dynamic_batch, "batch", batch)
    onnx.save(model, str(path))
    return path


def check_onnx(path: str | Path) -> None:
    import onnx

    model = onnx.load(str(path), load_external_data=False)
    onnx.checker.check_model(model)


def update_onnx_metadata(path: str | Path, values: dict[str, object]) -> Path:
    import onnx

    model_path = Path(path)
    model = onnx.load(str(model_path), load_external_data=False)
    metadata = {item.key: item.value for item in model.metadata_props}
    for key, value in values.items():
        if isinstance(value, (dict, list, tuple)):
            metadata[str(key)] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        else:
            metadata[str(key)] = str(value)
    model.ClearField("metadata_props")
    for key, value in metadata.items():
        item = model.metadata_props.add()
        item.key = key
        item.value = value
    onnx.save(model, str(model_path))
    return model_path


def topologically_sort_onnx_graph(model):
    """Restore node order after converters insert cast or quantization nodes."""

    available = {
        item.name
        for item in model.graph.input
        if item.name
    }
    available.update(item.name for item in model.graph.initializer if item.name)
    pending = list(model.graph.node)
    ordered = []
    while pending:
        progressed = False
        remaining = []
        for node in pending:
            inputs = {value for value in node.input if value}
            if inputs.issubset(available):
                ordered.append(node)
                available.update(value for value in node.output if value)
                progressed = True
            else:
                remaining.append(node)
        if not progressed:
            raise ValueError("ONNX 图包含无法排序的节点依赖。")
        pending = remaining
    model.graph.ClearField("node")
    model.graph.node.extend(ordered)
    return model


def _set_dimension(dimensions, index: int, dynamic: bool, name: str, fixed: int) -> None:
    if index >= len(dimensions):
        return
    dimension = dimensions[index]
    dimension.ClearField("dim_value")
    dimension.ClearField("dim_param")
    if dynamic:
        dimension.dim_param = name
    else:
        dimension.dim_value = int(fixed)


__all__ = [
    "check_onnx",
    "constrain_onnx_dynamic_axes",
    "simplify_onnx_graph",
    "topologically_sort_onnx_graph",
    "update_onnx_metadata",
]
