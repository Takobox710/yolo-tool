import json

import pytest


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

@pytest.mark.parametrize(
    ("installed", "expected_base", "expected_extra"),
    [
        (
            {
                "base_package_version": "base-runtime-models-2",
                "model_export_version": "model-export-runtime-3",
            },
            False,
            False,
        ),
        (
            {"base_package_version": "v1", "model_export_version": "runtime-1"},
            True,
            True,
        ),
    ],
    ids=["same_versions", "newer_release_packages"],
)
def test_environment_update_flags_follow_installed_versions(
    monkeypatch, installed, expected_base, expected_extra
):
    from src.services.runtime import release_updates

    monkeypatch.setattr(release_updates, "load_install_instance", lambda: installed)
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
                        "name": "YOLOTool_ExtraEnv_v3.7z",
                        "browser_download_url": "https://github.com/example/extra.7z",
                    },
                ],
            }
        ),
    )

    result = release_updates.check_latest_release("1.3.3")

    assert result.base_environment_update_available is expected_base
    assert result.extra_environment_update_available is expected_extra

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
