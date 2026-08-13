from __future__ import annotations


def training_device_options(
    *, cuda_available: bool, gpu_count: int
) -> list[tuple[str, str]]:
    """根据 CUDA 可用性与 GPU 数量生成 (显示标签, 设备值) 训练设备选项。"""
    if not cuda_available or gpu_count <= 0:
        return [("CPU", "cpu")]
    options = [
        ("GPU" if index == 0 else f"GPU {index}", str(index))
        for index in range(gpu_count)
    ]
    options.append(("CPU", "cpu"))
    return options


def default_training_device(*, cuda_available: bool, gpu_count: int) -> str:
    return "0" if cuda_available and gpu_count >= 1 else "cpu"


__all__ = ["default_training_device", "training_device_options"]
