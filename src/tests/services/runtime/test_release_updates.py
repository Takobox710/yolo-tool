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


def test_latest_release_detects_a_new_version(monkeypatch):
    from src.services.runtime import release_updates

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["user_agent"] = request.get_header("User-agent")
        captured["timeout"] = timeout
        return _Response(
            {
                "tag_name": "v1.4.0",
                "html_url": "https://github.com/example/release",
                "body": "- 修复版本检查\n- 优化设置页",
                "assets": [
                    {
                        "name": "YOLOTool_Setup_1.4.0.exe",
                        "browser_download_url": "https://github.com/example/setup.exe",
                    },
                    {
                        "name": "YOLOTool_BaseEnv_v2.7z",
                        "browser_download_url": "https://github.com/example/base.7z",
                    },
                ],
            }
        )

    monkeypatch.setattr(release_updates, "urlopen", fake_urlopen)

    result = release_updates.check_latest_release("1.3.1")

    assert result.latest_version == "1.4.0"
    assert result.update_available is True
    assert result.release_url.endswith("/release")
    assert result.release_notes == "- 修复版本检查\n- 优化设置页"
    assert result.installer_asset_name == "YOLOTool_Setup_1.4.0.exe"
    assert result.installer_asset_url.endswith("setup.exe")
    assert result.environment_asset_names == ("YOLOTool_BaseEnv_v2.7z",)
    assert result.environment_asset_urls == ("https://github.com/example/base.7z",)
    assert result.base_environment_version == "2.0.0"
    assert result.installed_base_environment_version == "2.0.0"
    assert result.base_environment_update_available is False
    assert captured["url"].endswith("/releases/latest")
    assert captured["user_agent"] == "YOLOTool-version-check"
    assert captured["timeout"] == 8.0


def test_latest_release_does_not_mark_equal_or_older_versions(monkeypatch):
    from src.services.runtime import release_updates

    monkeypatch.setattr(
        release_updates,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"tag_name": "v1.3.0"}),
    )
    assert release_updates.check_latest_release("1.3.1").update_available is False

    monkeypatch.setattr(
        release_updates,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"tag_name": "v1.2.9"}),
    )
    assert release_updates.check_latest_release("1.3.1").update_available is False


def test_latest_release_failure_is_reported_without_raising(monkeypatch):
    from urllib.error import URLError

    from src.services.runtime import release_updates

    monkeypatch.setattr(
        release_updates,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")),
    )

    result = release_updates.check_latest_release("1.3.1")

    assert result.succeeded is False
    assert result.update_available is False
    assert "offline" in result.error


def test_release_version_normalization_and_comparison():
    from src.services.runtime.release_updates import (
        is_newer_version,
        normalize_environment_version,
        normalize_release_version,
    )

    assert normalize_release_version("v2") == "2.0.0"
    assert normalize_release_version("2.1.5") == "2.1.5"
    assert normalize_release_version("release-latest") == ""
    assert normalize_environment_version("v2") == "2.0.0"
    assert normalize_environment_version("base-runtime-models-2") == "2.0.0"
    assert normalize_environment_version("model-export-runtime-2") == "2.0.0"
    assert is_newer_version("1.3.9", "1.4.0") is True


def test_environment_update_requires_a_higher_package_version(monkeypatch):
    from src.services.runtime import release_updates

    monkeypatch.setattr(
        release_updates,
        "load_install_instance",
        lambda: {
            "base_package_version": "base-runtime-models-2",
            "model_export_version": "model-export-runtime-2",
        },
    )
    monkeypatch.setattr(
        release_updates,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "tag_name": "v1.4.0",
                "assets": [
                    {
                        "name": "YOLOTool_BaseEnv_v2.7z",
                        "browser_download_url": "https://github.com/example/base.7z",
                    },
                    {
                        "name": "YOLOTool_ExtraEnv_v2.7z",
                        "browser_download_url": "https://github.com/example/extra.7z",
                    },
                ],
            }
        ),
    )

    result = release_updates.check_latest_release("1.3.1")

    assert result.base_environment_update_available is False
    assert result.extra_environment_update_available is False


def test_environment_update_is_detected_when_release_package_is_newer(monkeypatch):
    from src.services.runtime import release_updates

    monkeypatch.setattr(
        release_updates,
        "load_install_instance",
        lambda: {
            "base_package_version": "v1",
            "model_export_version": "runtime-1",
        },
    )
    monkeypatch.setattr(
        release_updates,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "tag_name": "v1.4.0",
                "assets": [
                    {
                        "name": "YOLOTool_BaseEnv_v2.7z",
                        "browser_download_url": "https://github.com/example/base.7z",
                    },
                    {
                        "name": "YOLOTool_ExtraEnv_v2.7z",
                        "browser_download_url": "https://github.com/example/extra.7z",
                    },
                ],
            }
        ),
    )

    result = release_updates.check_latest_release("1.3.1")

    assert result.installed_base_environment_version == "1.0.0"
    assert result.installed_extra_environment_version == "1.0.0"
    assert result.base_environment_update_available is True
    assert result.extra_environment_update_available is True


def test_missing_extra_environment_is_optional_not_an_update():
    from src.services.runtime.release_environment import environment_update_available

    assert (
        environment_update_available(
            "2.0.0",
            "",
            True,
            missing_is_update=False,
        )
        is False
    )


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
