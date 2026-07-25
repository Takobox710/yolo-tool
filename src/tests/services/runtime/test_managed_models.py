from __future__ import annotations

import json

import pytest


def _write_manifest(root, files):
    metadata = root / "_internal" / "yolotool_metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "managed-models.json").write_text(
        json.dumps({"schema_version": 1, "files": files}),
        encoding="utf-8",
    )


def test_remove_managed_models_preserves_user_models(tmp_path):
    from src.services.runtime import remove_managed_models

    models = tmp_path / "data" / "models"
    nested = models / "official"
    nested.mkdir(parents=True)
    managed = nested / "yolo.pt"
    user_model = models / "custom.pt"
    managed.write_bytes(b"official")
    user_model.write_bytes(b"user")
    _write_manifest(tmp_path, {"official/yolo.pt": "ignored-hash"})

    removed = remove_managed_models(tmp_path)

    assert removed == [managed.resolve()]
    assert not managed.exists()
    assert not nested.exists()
    assert user_model.read_bytes() == b"user"


@pytest.mark.parametrize("relative", ["../outside.pt", "/outside.pt", "C:/outside.pt"])
def test_remove_managed_models_rejects_unsafe_paths(tmp_path, relative):
    from src.services.runtime import ReleaseManifestError, remove_managed_models

    _write_manifest(tmp_path, {relative: "hash"})

    with pytest.raises(ReleaseManifestError):
        remove_managed_models(tmp_path)
