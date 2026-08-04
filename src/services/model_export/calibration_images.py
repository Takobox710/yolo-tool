from __future__ import annotations

from pathlib import Path


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
SAM2_IMAGE_MEAN = (0.485, 0.456, 0.406)
SAM2_IMAGE_STD = (0.229, 0.224, 0.225)


def load_image_tensor(
    path: str | Path,
    *,
    height: int,
    width: int,
    batch: int = 1,
):
    import numpy as np
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB").resize((width, height), Image.Resampling.BILINEAR)
        array = np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0
    tensor = array[None, ...]
    if batch > 1:
        tensor = np.repeat(tensor, batch, axis=0)
    return tensor


def load_sam2_image_tensor(
    path: str | Path,
    *,
    height: int = 1024,
    width: int = 1024,
    batch: int = 1,
):
    import numpy as np

    tensor = load_image_tensor(path, height=height, width=width, batch=batch)
    mean = np.asarray(SAM2_IMAGE_MEAN, dtype=np.float32).reshape(1, 3, 1, 1)
    std = np.asarray(SAM2_IMAGE_STD, dtype=np.float32).reshape(1, 3, 1, 1)
    return (tensor - mean) / std


__all__ = ["IMAGE_SUFFIXES", "SAM2_IMAGE_MEAN", "SAM2_IMAGE_STD", "load_image_tensor", "load_sam2_image_tensor"]
