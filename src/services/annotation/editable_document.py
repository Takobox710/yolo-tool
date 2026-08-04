"""Compatibility façade for editable annotation codecs."""

from src.services.annotation.annotation_models import EditableAnnotation
from src.services.annotation.geometry import (
    detect_points_to_rect as _detect_points_to_rect,
    points_to_min_area_obb as _points_to_min_area_obb,
)
from src.services.annotation.labelme_document import (
    load_labelme_annotations,
    save_labelme_annotations,
)
from src.services.annotation.yolo_document import (
    annotation_to_seg_points,
    load_editable_annotations,
    save_editable_annotations,
)

__all__ = [
    "EditableAnnotation",
    "annotation_to_seg_points",
    "_detect_points_to_rect",
    "_points_to_min_area_obb",
    "load_editable_annotations",
    "load_labelme_annotations",
    "save_labelme_annotations",
    "save_editable_annotations",
]
