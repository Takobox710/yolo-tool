"""Small image factories shared by service tests."""

from pathlib import Path


def make_image(path: Path, size=(100, 100), color="white") -> Path:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path
