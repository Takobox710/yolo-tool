from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request

from src import APP_VERSION
from src.services.runtime.install_instance import load_install_instance
from src.services.runtime.release_environment import (
    environment_asset_version,
    environment_update_available,
    has_environment_asset,
    installed_environment_versions,
)
from src.services.runtime.release_versions import is_newer_version, normalize_release_version


GITHUB_REPOSITORY = "Takobox710/yolo-tool"
GITHUB_LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
_INSTALLER_NAME_PATTERN = re.compile(r"^YOLOTool_Setup_[0-9A-Za-z.-]+\.exe$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ReleaseCheckResult:
    current_version: str
    latest_version: str = ""
    release_url: str = ""
    release_notes: str = ""
    installer_asset_name: str = ""
    installer_asset_url: str = ""
    environment_asset_names: tuple[str, ...] = ()
    environment_asset_urls: tuple[str, ...] = ()
    base_environment_version: str = ""
    extra_environment_version: str = ""
    installed_base_environment_version: str = ""
    installed_extra_environment_version: str = ""
    base_environment_update_available: bool | None = None
    extra_environment_update_available: bool | None = None
    update_available: bool = False
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.error and bool(self.latest_version)


def parse_assets(payload) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    installer_name = ""
    installer_url = ""
    environment_names: list[str] = []
    environment_urls: list[str] = []
    if not isinstance(payload, list):
        return installer_name, installer_url, (), ()
    for asset in payload:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip()
        url = str(asset.get("browser_download_url") or "").strip()
        if not name:
            continue
        if not installer_name and _INSTALLER_NAME_PATTERN.fullmatch(name):
            installer_name, installer_url = name, url
        elif is_environment_asset(name):
            environment_names.append(name)
            environment_urls.append(url)
    return installer_name, installer_url, tuple(environment_names), tuple(environment_urls)


def is_environment_asset(name: str) -> bool:
    lowered = name.casefold()
    return lowered.endswith((".7z", ".zip")) and (
        lowered.startswith("yolotool_baseenv_") or lowered.startswith("yolotool_extraenv_")
    )


def check_latest_release(
    current_version: str = APP_VERSION,
    *,
    timeout: float = 8.0,
    urlopen_fn: Callable = None,
    load_install_instance_fn: Callable = None,
) -> ReleaseCheckResult:
    request = Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "YOLOTool-version-check"},
    )
    if urlopen_fn is None:
        from urllib.request import urlopen as urlopen_fn
    try:
        with urlopen_fn(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        return ReleaseCheckResult(current_version=str(current_version), error=str(exc))
    if not isinstance(payload, dict):
        return ReleaseCheckResult(current_version=str(current_version), error="GitHub Release 返回格式无效")
    latest_version = normalize_release_version(str(payload.get("tag_name") or "").strip())
    if not latest_version:
        return ReleaseCheckResult(current_version=str(current_version), error="GitHub Release 缺少有效版本号")
    names = parse_assets(payload.get("assets"))
    if load_install_instance_fn is None:
        load_install_instance_fn = load_install_instance
    installed_base_version, installed_extra_version = installed_environment_versions(load_install_instance_fn)
    base_version = environment_asset_version(names[2], "baseenv")
    extra_version = environment_asset_version(names[2], "extraenv")
    return ReleaseCheckResult(
        current_version=str(current_version),
        latest_version=latest_version,
        release_url=str(payload.get("html_url") or ""),
        release_notes=str(payload.get("body") or ""),
        installer_asset_name=names[0],
        installer_asset_url=names[1],
        environment_asset_names=names[2],
        environment_asset_urls=names[3],
        base_environment_version=base_version,
        extra_environment_version=extra_version,
        installed_base_environment_version=installed_base_version,
        installed_extra_environment_version=installed_extra_version,
        base_environment_update_available=environment_update_available(
            base_version, installed_base_version, has_environment_asset(names[2], "baseenv")
        ),
        extra_environment_update_available=environment_update_available(
            extra_version, installed_extra_version, has_environment_asset(names[2], "extraenv"), missing_is_update=False
        ),
        update_available=is_newer_version(current_version, latest_version),
    )


__all__ = [
    "GITHUB_LATEST_RELEASE_URL",
    "GITHUB_REPOSITORY",
    "ReleaseCheckResult",
    "check_latest_release",
    "is_environment_asset",
    "parse_assets",
]
