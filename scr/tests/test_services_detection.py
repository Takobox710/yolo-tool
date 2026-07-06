import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_detection_source_collection_supports_folder_and_single_file(tmp_path):
    from scr.services.detection_service import collect_prediction_sources

    folder = tmp_path / "inputs"
    folder.mkdir()
    image = folder / "a.jpg"
    video = folder / "b.mp4"
    ignored = folder / "c.txt"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    ignored.write_text("skip", encoding="utf-8")

    assert collect_prediction_sources("图片/视频文件夹", folder) == [image, video]
    assert collect_prediction_sources("图片/视频", image) == [image]
    assert collect_prediction_sources("图片/视频", video) == [video]
    assert collect_prediction_sources("摄像头", folder) == []


def test_detection_source_collection_supports_dataset_yaml_scopes(tmp_path):
    from scr.services.detection_service import collect_prediction_sources

    dataset_root = tmp_path / "data"
    train_dir = dataset_root / "train" / "images"
    val_dir = dataset_root / "val" / "images"
    test_dir = dataset_root / "test" / "images"
    train_dir.mkdir(parents=True)
    val_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)
    train_image = train_dir / "1.jpg"
    val_image = val_dir / "2.jpg"
    test_image = test_dir / "3.jpg"
    train_image.write_bytes(b"train")
    val_image.write_bytes(b"val")
    test_image.write_bytes(b"test")
    dataset_yaml = dataset_root / "data.yaml"
    dataset_yaml.write_text(
        "\n".join(
            [
                "path: .",
                "train: train/images",
                "val: val/images",
                "test: test/images",
                "names: ['weld']",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert collect_prediction_sources(
        "图片/视频文件夹",
        "",
        dataset_yaml=dataset_yaml,
        source_scope="全部图片",
    ) == [train_image.resolve(), val_image.resolve(), test_image.resolve()]
    assert collect_prediction_sources(
        "图片/视频文件夹",
        "",
        dataset_yaml=dataset_yaml,
        source_scope="训练图片",
    ) == [train_image.resolve()]
    assert collect_prediction_sources(
        "图片/视频文件夹",
        "",
        dataset_yaml=dataset_yaml,
        source_scope="验证图片",
    ) == [val_image.resolve()]
    assert collect_prediction_sources(
        "图片/视频文件夹",
        "",
        dataset_yaml=dataset_yaml,
        source_scope="测试图片",
    ) == [test_image.resolve()]


def test_detection_source_collection_prefers_custom_folder_over_dataset_yaml(tmp_path):
    from scr.services.detection_service import collect_prediction_sources

    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    custom_image = custom_dir / "custom.jpg"
    custom_image.write_bytes(b"custom")

    dataset_root = tmp_path / "data"
    train_dir = dataset_root / "train" / "images"
    train_dir.mkdir(parents=True)
    (train_dir / "train.jpg").write_bytes(b"train")
    dataset_yaml = dataset_root / "data.yaml"
    dataset_yaml.write_text(
        "path: .\ntrain: train/images\nval: val/images\nnames: ['weld']\n",
        encoding="utf-8",
    )

    assert collect_prediction_sources(
        "图片/视频文件夹",
        custom_dir,
        dataset_yaml=dataset_yaml,
        source_scope="训练图片",
    ) == [custom_image]


def test_detection_source_collection_uses_natural_numeric_sort(tmp_path):
    from scr.services.detection_service import collect_prediction_sources

    folder = tmp_path / "inputs"
    folder.mkdir()
    for name in ["1.jpg", "10.jpg", "100.jpg", "2.jpg", "3.jpg"]:
        (folder / name).write_bytes(b"image")

    assert [path.name for path in collect_prediction_sources("图片/视频文件夹", folder)] == [
        "1.jpg",
        "2.jpg",
        "3.jpg",
        "10.jpg",
        "100.jpg",
    ]


def test_stream_result_rendering_uses_current_frame_as_plot_background():
    import numpy as np
    from scr.services.detection_service import render_result_image_from_frame

    class FakeResult:
        def __init__(self):
            self.received = None

        def plot(self, img=None):
            self.received = img.copy() if img is not None else None
            return img

    frame = np.full((4, 5, 3), 127, dtype=np.uint8)
    result = FakeResult()

    rendered = render_result_image_from_frame(result, frame)

    assert result.received is not None
    assert np.array_equal(result.received, frame)
    assert rendered.size == (5, 4)


def test_save_detection_label_file_writes_detect_format(tmp_path):
    from scr.services.detection_service import normalize_detection_item, save_detection_label_file

    label_dir = tmp_path / "labels"
    label_dir.mkdir()
    label_path = label_dir / "detect.txt"
    item = normalize_detection_item(
        "weld", 0.9, [(40, 30), (60, 30), (60, 70), (40, 70)]
    )

    save_detection_label_file(label_path, [item], 100, 100)

    assert (
        label_path.read_text(encoding="utf-8").strip()
        == "0 0.500000 0.500000 0.200000 0.400000"
    )


def test_save_detection_label_file_writes_obb_format(tmp_path):
    from scr.services.detection_service import normalize_detection_item, save_detection_label_file

    label_dir = tmp_path / "labels"
    label_dir.mkdir()
    label_path = label_dir / "obb.txt"
    item = normalize_detection_item(
        "weld", 0.9, [(10, 20), (30, 10), (40, 30), (20, 40)]
    )

    save_detection_label_file(label_path, [item], 100, 100)

    assert label_path.read_text(encoding="utf-8").strip() == (
        "0 0.100000 0.200000 0.300000 0.100000 0.400000 0.300000 0.200000 0.400000"
    )


def test_ultralytics_compat_patches_missing_cv2_highgui_symbols(monkeypatch):
    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    fake_cv2 = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    ensure_cv2_highgui_compat()

    assert callable(fake_cv2.imshow)
    assert callable(fake_cv2.namedWindow)
    assert callable(fake_cv2.destroyAllWindows)
    assert fake_cv2.waitKey() == -1
