from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile


class _Response:
    def __init__(self, payload: bytes):
        self._stream = BytesIO(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size: int):
        return self._stream.read(size)


def _archive(*names: str) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w") as package:
        for name in names:
            package.writestr(name, b"fixture")
    return stream.getvalue()


def test_generic_calibration_pack_downloads_and_reuses_cache(tmp_path):
    from src.services.model_export.calibration_pack import (
        download_generic_calibration_pack,
        generic_calibration_pack_path,
    )

    payload = _archive("coco128/images/train2017/000000000001.jpg")
    calls = []
    progress = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        return _Response(payload)

    result = download_generic_calibration_pack(
        cache_root=tmp_path,
        progress=lambda downloaded, total: progress.append((downloaded, total)),
        urlopen_fn=fake_urlopen,
    )

    assert result == generic_calibration_pack_path(tmp_path)
    assert (result / "SOURCE.txt").is_file()
    assert list(result.rglob("*.jpg"))
    assert calls
    assert progress[-1] == (len(payload), len(payload))

    reused = download_generic_calibration_pack(
        cache_root=tmp_path,
        urlopen_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()),
    )
    assert reused == result


def test_generic_calibration_pack_rejects_zip_slip(tmp_path):
    from src.services.model_export.calibration_pack import download_generic_calibration_pack

    payload = _archive("../outside.jpg")

    try:
        download_generic_calibration_pack(
            cache_root=tmp_path,
            urlopen_fn=lambda *_args, **_kwargs: _Response(payload),
        )
    except ValueError as exc:
        assert "非法路径" in str(exc)
    else:
        raise AssertionError("expected zip-slip validation failure")
