import json


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

def test_download_and_launch_installer_writes_to_target_directory(monkeypatch, tmp_path):
    from src.services.runtime import release_updates

    class _BinaryResponse:
        headers = {"Content-Length": "6"}

        def __init__(self):
            self._data = b"setup!"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            data, self._data = self._data, b""
            return data

    launched = []
    progress = []
    monkeypatch.setattr(release_updates, "urlopen", lambda *_args, **_kwargs: _BinaryResponse())
    monkeypatch.setattr(release_updates, "launch_installer", launched.append)

    path = release_updates.download_and_launch_installer(
        "https://github.com/example/setup.exe",
        "YOLOTool_Setup_1.4.0.exe",
        download_dir=tmp_path,
        progress=lambda downloaded, total: progress.append((downloaded, total)),
    )

    assert path == tmp_path / "YOLOTool_Setup_1.4.0.exe"
    assert path.read_bytes() == b"setup!"
    assert launched == [path]
    assert progress[-1] == (6, 6)

def test_downloads_directory_uses_windows_known_folder_resolution(monkeypatch, tmp_path):
    from src.services.runtime import release_updates

    monkeypatch.setattr(
        release_updates,
        "_windows_downloads_directory",
        lambda: tmp_path,
    )

    assert release_updates.downloads_directory() == tmp_path

def test_download_release_assets_downloads_selected_program_and_environment(
    monkeypatch, tmp_path
):
    from src.services.runtime import release_updates

    class _BinaryResponse:
        def __init__(self, data):
            self.headers = {"Content-Length": str(len(data))}
            self._data = data

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            data, self._data = self._data, b""
            return data

    payloads = {
        "https://github.com/example/setup.exe": b"setup",
        "https://github.com/example/base.7z": b"base",
    }
    progress = []
    monkeypatch.setattr(
        release_updates,
        "urlopen",
        lambda request, **_kwargs: _BinaryResponse(payloads[request.full_url]),
    )

    paths = release_updates.download_release_assets(
        (
            ("YOLOTool_Setup_1.4.0.exe", "https://github.com/example/setup.exe"),
            ("YOLOTool_BaseEnv_v2.7z", "https://github.com/example/base.7z"),
        ),
        download_dir=tmp_path,
        progress=lambda *items: progress.append(items),
    )

    assert [path.name for path in paths] == [
        "YOLOTool_Setup_1.4.0.exe",
        "YOLOTool_BaseEnv_v2.7z",
    ]
    assert (tmp_path / "YOLOTool_Setup_1.4.0.exe").read_bytes() == b"setup"
    assert (tmp_path / "YOLOTool_BaseEnv_v2.7z").read_bytes() == b"base"
    assert progress[-1] == ("YOLOTool_BaseEnv_v2.7z", 1, 2, 4, 4)
