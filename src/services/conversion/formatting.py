from __future__ import annotations

from src.services.conversion.types import ConversionConfig, ConversionResult


def format_conversion_result(
    result: ConversionResult, config: ConversionConfig, preview: bool = False
) -> str:
    total_images = (
        result.labeled_train_count
        + result.labeled_val_count
        + result.labeled_test_count
    )
    title = "转换预览" if preview else "转换完成"
    operation = (
        "Labelme 转 YOLO 并分组"
        if config.source_format == "labelme"
        else "YOLO 标注分组"
    )
    lines = [
        f"{title}！",
        "",
        f"模式: {operation}",
        f"任务类型: {config.task_mode}",
        "",
        "数据集划分:",
        _format_split_line("训练集", "train", result.labeled_train_count, result.stats),
        _format_split_line("验证集", "val", result.labeled_val_count, result.stats),
        _format_split_line("测试集", "test", result.labeled_test_count, result.stats),
        "",
        "总体统计:",
        f"  - 有标注图片: {total_images} 张",
        f"  - 无标注图片: {result.unlabeled_count} 张",
        f"  - 标注总数: {result.total_boxes}",
        "",
        "类别统计:",
    ]
    class_names = getattr(result, "class_names", None) or config.class_names or []
    for class_name in class_names:
        train = result.stats.get("train", {}).get(class_name, 0)
        val = result.stats.get("val", {}).get(class_name, 0)
        test = result.stats.get("test", {}).get(class_name, 0)
        lines.append(
            f"  - {class_name}: train={train}, val={val}, test={test}, total={train + val + test}"
        )
    if result.missing_labels:
        lines.extend(["", "跳过或未知标签:"])
        for label, names in sorted(result.missing_labels.items()):
            sample = ", ".join(names[:5])
            more = f" 等 {len(names)} 项" if len(names) > 5 else ""
            lines.append(f"  - 标签 '{label}': {sample}{more}")
    lines.extend(
        [
            "",
            "输出路径:",
            f"  - 数据集目录: {result.yaml_path.parent}",
            f"  - YAML 配置: {result.yaml_path}",
            f"  - 汇总标签: {result.labels_dir}",
        ]
    )
    if getattr(result, "backup_dir", None):
        lines.append(f"  - 备份目录: {result.backup_dir}")
    if preview:
        lines.extend(["", "预览模式未执行任何写入。"])
    return "\n".join(lines)


def _format_split_line(
    label: str, split: str, image_count: int, stats: dict[str, dict[str, int]]
) -> str:
    box_count = sum(stats.get(split, {}).values())
    return f"  - {label}（{split}）: {image_count} 张图片, {box_count} 个标注"
