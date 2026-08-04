from __future__ import annotations


def test_model_export_facades_keep_legacy_symbols():
    from src.services.model_export import calibration, sam_onnx

    assert "CalibrationSet" in calibration.__all__
    assert "export_sam2_model_to_directory" in sam_onnx.__all__
    assert calibration.CalibrationSet.__module__.endswith("calibration_sources")


def test_annotation_document_facade_preserves_model_identity():
    from src.services.annotation import editable_document
    from src.services.annotation.annotation_models import EditableAnnotation

    assert editable_document.EditableAnnotation is EditableAnnotation
    assert "save_labelme_annotations" in editable_document.__all__


def test_devtool_facades_keep_cli_build_symbols():
    from src.devtools import base_runtime_builder, model_export_package

    assert callable(base_runtime_builder.build_base_runtime_archive)
    assert callable(model_export_package.build_model_export_archive)
    assert model_export_package.OPTIONAL_DISTRIBUTIONS
