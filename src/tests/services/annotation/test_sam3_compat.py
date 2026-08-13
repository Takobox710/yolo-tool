from __future__ import annotations

import builtins
import sys
from pathlib import Path


def test_sam3_compat_imports_vendor_runtime_when_pkg_resources_is_missing(
    monkeypatch,
):
    from src.services.annotation.sam3_compat import load_sam3_components

    original_import = builtins.__import__
    monkeypatch.delitem(sys.modules, "pkg_resources", raising=False)
    for name in list(sys.modules):
        if name == "sam3" or name.startswith("sam3."):
            monkeypatch.delitem(sys.modules, name)

    def import_without_pkg_resources(name, *args, **kwargs):
        if name == "pkg_resources" and name not in sys.modules:
            raise ModuleNotFoundError("No module named 'pkg_resources'", name=name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_pkg_resources)

    processor, builder = load_sam3_components()
    from sam3 import model_builder

    resource = model_builder.pkg_resources.resource_filename(
        "sam3", "assets/bpe_simple_vocab_16e6.txt.gz"
    )

    assert processor is not None
    assert builder is model_builder.build_sam3_image_model
    assert Path(resource).is_file()
    assert "pkg_resources" not in sys.modules
