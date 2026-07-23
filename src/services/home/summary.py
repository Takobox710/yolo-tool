from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from src.services.home.distribution import (
    build_distribution_data,
    build_folder_distribution_data,
    count_annotation_files,
    count_dataset_annotated_images,
    count_dataset_split_images,
    count_image_files,
    count_labelme_annotation_files,
    count_yolo_annotation_files,
    has_split_annotation_data,
    read_label_class_id_counts,
    read_label_class_ids,
    resolve_dataset_class_names,
)
from src.services.training import read_results_csv_for_curves, read_train_metrics
from src.services.validation import scan_candidate_models


def build_home_summary(
    *,
    images_dir: Path,
    annotations_dir: Path,
    labels_dir: Path,
    dataset_dir: Path,
    result_dir: Path,
    configured_class_names: Sequence[str],
) -> dict[str, Any]:
    single_counts, multi_counts, class_names = build_distribution_data(
        dataset_dir, configured_class_names
    )
    folder_counts, folder_class_names = build_folder_distribution_data(
        images_dir, annotations_dir, labels_dir, class_names
    )
    distribution_source = "dataset"
    if not has_split_annotation_data(dataset_dir) and folder_counts["total_images"]:
        class_names = folder_class_names
        multi_counts = folder_counts["class_counts"]
        distribution_source = "folder"

    image_count = count_image_files(images_dir)
    split_image_counts = count_dataset_split_images(dataset_dir)
    if not image_count:
        image_count = sum(split_image_counts.values())
    annotated_images = folder_counts["annotated_images"]
    if not count_image_files(images_dir):
        annotated_images = count_dataset_annotated_images(dataset_dir)
    return {
        "image_count": image_count,
        "label_count": count_annotation_files(annotations_dir, labels_dir),
        "single_counts": single_counts,
        "multi_counts": multi_counts,
        "class_names": class_names,
        "distribution_source": distribution_source,
        "folder_counts": folder_counts,
        "standard_counts": {
            "total_images": image_count,
            "split_counts": split_image_counts,
            "unannotated_images": max(image_count - annotated_images, 0),
        },
        "curve_data": read_results_csv_for_curves(result_dir),
        "history_entries": collect_home_history_entries(result_dir),
    }


def collect_home_history_entries(
    result_dir: Path, *, limit: int = 8
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for candidate in scan_candidate_models(result_dir)[:limit]:
        run_dir = candidate.parent.parent
        model_name = candidate.name
        entries.append(
            {
                "train_id": run_dir.name,
                "model_name": model_name,
                "metrics": read_train_metrics(run_dir, model_name),
            }
        )
    return entries
