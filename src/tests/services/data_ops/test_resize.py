import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

from src.tests.helpers.images import make_image


def test_resize_can_skip_backup_by_default(tmp_path):
    from src.services.data_ops import ResizeConfig, run_resize

    source = tmp_path / "images"
    source.mkdir()
    make_image(source / "a.jpg", size=(640, 480), color="blue")

    result = run_resize(
        ResizeConfig(
            source_dir=source,
            output_dir=tmp_path / "out",
            backup_dir=tmp_path / "backup",
            long_edge=320,
            canvas_size=320,
            background="white",
            backup_enabled=False,
        )
    )

    assert result.processed_count == 1
    assert (tmp_path / "out" / "a.jpg").exists()
    assert not (tmp_path / "backup").exists()


def test_resize_recursively_scans_and_preserves_relative_structure(tmp_path):
    from src.services.data_ops import ResizeConfig, preview_resize, run_resize

    source = tmp_path / "images"
    nested = source / "10" / "2"
    nested.mkdir(parents=True)
    make_image(source / "1.jpg", size=(1000, 500), color="red")
    make_image(source / "10.jpg", size=(500, 1000), color="green")
    make_image(nested / "3.jpg", size=(1200, 600), color="blue")

    config = ResizeConfig(
        source_dir=source,
        output_dir=tmp_path / "out",
        backup_dir=tmp_path / "backup",
        canvas_size=800,
        background="white",
        backup_enabled=True,
    )

    preview = preview_resize(config)
    result = run_resize(config)

    assert [str(item.source.relative_to(source)) for item in preview.items] == [
        "1.jpg",
        str(Path("10") / "2" / "3.jpg"),
        "10.jpg",
    ]
    assert [item.output.relative_to(tmp_path / "out") for item in preview.items] == [
        Path("1.jpg"),
        Path("10") / "2" / "3.jpg",
        Path("10.jpg"),
    ]
    assert (tmp_path / "out" / "10" / "2" / "3.jpg").exists()
    assert (tmp_path / "backup" / "10" / "2" / "3.jpg").exists()
    assert result.processed_count == 3


def test_canvas_resize_outputs_selected_ratio_with_centered_padding(tmp_path):
    from PIL import Image

    from src.services.data_ops import ResizeConfig, run_resize

    source = tmp_path / "images"
    source.mkdir()
    make_image(source / "wide.jpg", size=(1200, 600), color="red")

    run_resize(
        ResizeConfig(
            source_dir=source,
            output_dir=tmp_path / "out",
            backup_dir=tmp_path / "backup",
            aspect_ratio="4:3",
            resolution="640×480",
            background="black",
        )
    )

    with Image.open(tmp_path / "out" / "wide.jpg") as image:
        assert image.size == (640, 480)
        assert image.getpixel((10, 10)) == (0, 0, 0)
        red = image.getpixel((320, 240))
        assert red[0] > 200 and red[1] < 30 and red[2] < 30


def test_crop_resize_center_crops_to_selected_ratio_and_resolution(tmp_path):
    from PIL import Image

    from src.services.data_ops import (
        RESIZE_MODE_CROP,
        ResizeConfig,
        preview_resize,
        run_resize,
    )

    source = tmp_path / "images"
    source.mkdir()
    image = Image.new("RGB", (1200, 600), "red")
    image.paste("blue", (0, 0, 300, 600))
    image.paste("green", (900, 0, 1200, 600))
    image.save(source / "wide.jpg")
    config = ResizeConfig(
        source_dir=source,
        output_dir=tmp_path / "out",
        backup_dir=tmp_path / "backup",
        mode=RESIZE_MODE_CROP,
        aspect_ratio="4:3",
        resolution="640×480",
    )

    preview = preview_resize(config)
    result = run_resize(config)

    assert preview.items[0].crop_box == (200, 0, 1000, 600)
    assert preview.items[0].output_size == (640, 480)
    assert result.processed_count == 1
    with Image.open(tmp_path / "out" / "wide.jpg") as image:
        assert image.size == (640, 480)
        pixel = image.getpixel((320, 240))
        assert pixel[0] > 200 and pixel[1] < 30 and pixel[2] < 30
