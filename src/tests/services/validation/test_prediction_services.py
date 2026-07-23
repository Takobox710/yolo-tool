import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_video_prediction_writes_mp4_without_frame_labels(monkeypatch, tmp_path):
    import cv2
    import numpy as np
    import types

    from src.train_cli import run_predict_cli
    import src.services.validation as validation_services

    monkeypatch.setattr(validation_services, "release_inference_runtime", lambda: None)

    input_path = tmp_path / "demo.mp4"
    input_path.write_bytes(b"fake-video")
    frames = [np.full((12, 16, 3), value, dtype=np.uint8) for value in (32, 64, 96)]
    written_frames = []

    class FakeCapture:
        def __init__(self, _source):
            self._frames = iter(frames)
            self._open = True

        def isOpened(self):
            return self._open

        def get(self, prop):
            return len(frames) if prop == cv2.CAP_PROP_FRAME_COUNT else 5.0

        def read(self):
            try:
                return True, next(self._frames)
            except StopIteration:
                self._open = False
                return False, None

        def release(self):
            self._open = False

    class FakeWriter:
        def __init__(self, path, *_args):
            Path(path).touch()

        def isOpened(self):
            return True

        def write(self, frame):
            written_frames.append(frame.copy())

        def release(self):
            pass

    monkeypatch.setattr(cv2, "VideoCapture", FakeCapture)
    monkeypatch.setattr(cv2, "VideoWriter", FakeWriter)
    monkeypatch.setattr(cv2, "VideoWriter_fourcc", lambda *_args: 0)
    monkeypatch.setattr(cv2, "imwrite", lambda path, _frame: Path(path).touch() or True)

    class FakeResult:
        names = {}
        boxes = None
        obb = None

        def plot(self, img=None):
            return img

    class FakeYOLO:
        def __init__(self, _model_path):
            pass

        def predict(self, **_kwargs):
            return [FakeResult()]

    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=FakeYOLO))
    events = []
    monkeypatch.setattr(
        "src.train_cli._emit_structured",
        lambda event, **payload: events.append((event, payload)),
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "model_path": str(tmp_path / "model.pt"),
                "source_mode": "视频检测",
                "source_path": str(input_path.parent),
                "save_dir": str(tmp_path / "results"),
                "confidence": 0.25,
                "iou": 0.45,
                "imgsz": 32,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert run_predict_cli([str(config_path)]) == 0

    result_dirs = list((tmp_path / "results").iterdir())
    result_video = result_dirs[0] / "demo_result.mp4"
    assert result_video.exists()
    assert not (result_dirs[0] / "labels").exists()
    assert len(written_frames) == 3
    completed = [payload for event, payload in events if event == "video_completed"]
    assert completed
    assert completed[-1]["payload"]["result_path"] == str(result_video)


def test_detection_source_collection_supports_folder_and_single_file(tmp_path):
    from src.services.validation import collect_prediction_sources

    folder = tmp_path / "inputs"
    folder.mkdir()
    image = folder / "a.jpg"
    video = folder / "b.mp4"
    ignored = folder / "c.txt"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    ignored.write_text("skip", encoding="utf-8")

    assert collect_prediction_sources("图片检测", folder) == [image]
    assert collect_prediction_sources("视频检测", folder) == [video]
    assert collect_prediction_sources("图片/视频文件夹", folder) == [image, video]
    assert collect_prediction_sources("图片/视频", image) == [image]
    assert collect_prediction_sources("图片/视频", video) == [video]
    assert collect_prediction_sources("图片检测", image) == [image.resolve()]
    assert collect_prediction_sources("视频检测", video) == [video.resolve()]
    assert collect_prediction_sources("摄像头", folder) == []
    assert collect_prediction_sources("摄像头检测", folder) == []


def test_detection_source_collection_supports_dataset_yaml_scopes(tmp_path):
    from src.services.validation import collect_prediction_sources

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
        "图片检测",
        "",
        dataset_yaml=dataset_yaml,
        source_scope="全部图片",
    ) == [train_image.resolve(), val_image.resolve(), test_image.resolve()]
    assert collect_prediction_sources(
        "图片检测",
        "",
        dataset_yaml=dataset_yaml,
        source_scope="训练图片",
    ) == [train_image.resolve()]
    assert collect_prediction_sources(
        "图片检测",
        "",
        dataset_yaml=dataset_yaml,
        source_scope="验证图片",
    ) == [val_image.resolve()]
    assert collect_prediction_sources(
        "图片检测",
        "",
        dataset_yaml=dataset_yaml,
        source_scope="测试图片",
    ) == [test_image.resolve()]


def test_stream_result_rendering_uses_current_frame_as_plot_background():
    import numpy as np
    from src.services.validation import render_result_image_from_frame

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


def test_save_detection_label_file_writes_detect_and_obb_formats(tmp_path):
    from src.services.validation import normalize_detection_item, save_detection_label_file

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

    label_path = label_dir / "obb.txt"
    item = normalize_detection_item(
        "weld", 0.9, [(10, 20), (30, 10), (40, 30), (20, 40)]
    )

    save_detection_label_file(label_path, [item], 100, 100)

    assert label_path.read_text(encoding="utf-8").strip() == (
        "0 0.100000 0.200000 0.300000 0.100000 0.400000 0.300000 0.200000 0.400000"
    )


def test_ultralytics_compat_patches_missing_cv2_highgui_symbols(monkeypatch):
    from src.services.ultralytics_compat import ensure_cv2_highgui_compat

    fake_cv2 = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    ensure_cv2_highgui_compat()

    assert callable(fake_cv2.imshow)
    assert callable(fake_cv2.namedWindow)
    assert callable(fake_cv2.destroyAllWindows)
    assert fake_cv2.waitKey() == -1
