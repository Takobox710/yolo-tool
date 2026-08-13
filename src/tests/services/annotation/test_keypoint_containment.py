from __future__ import annotations

import pytest

from src.services.annotation.annotation_models import EditableAnnotation
from src.services.annotation.geometry import annotation_contains_point, uncontained_keypoint_indices


@pytest.mark.parametrize(
    "annotation",
    [
        EditableAnnotation(0, "rect", [(0, 0), (10, 0), (10, 10), (0, 10)]),
        EditableAnnotation(0, "circle", [(0, 0), (10, 0), (10, 10), (0, 10)]),
        EditableAnnotation(0, "obb_single", [(2, 0), (10, 4), (8, 10), (0, 6)]),
        EditableAnnotation(0, "polygon", [(0, 0), (10, 0), (8, 10), (2, 10)]),
    ],
)
def test_annotation_contains_point_supports_every_non_point_shape(annotation):
    assert annotation_contains_point(annotation, (5, 5)) is True
    assert annotation_contains_point(annotation, (20, 20)) is False


def test_uncontained_keypoint_indices_ignores_classes_and_accepts_boundaries():
    annotations = [
        EditableAnnotation(1, "rect", [(0, 0), (10, 0), (10, 10), (0, 10)]),
        EditableAnnotation(0, "point", [(0, 5)]),
        EditableAnnotation(1, "point", [(20, 20)]),
    ]

    assert uncontained_keypoint_indices(annotations) == {2}
