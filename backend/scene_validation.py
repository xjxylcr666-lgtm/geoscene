from collections import Counter
from typing import Any

from backend.validation import validate_target


SUPPORTED_TYPES = {"box", "target", "wall", "observer"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_scene(objects: Any) -> dict[str, Any]:
    """Validate a complete GeoScene configuration before scene creation."""
    if not isinstance(objects, list):
        return {
            "valid": False,
            "errors": ["场景配置必须是对象数组"],
            "counts": {},
        }

    errors: list[str] = []
    counts: Counter[str] = Counter()
    seen_ids: set[str] = set()

    for index, item in enumerate(objects):
        prefix = f"objects[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}必须是对象")
            continue

        object_id = item.get("id")
        if not isinstance(object_id, str) or not object_id.strip():
            errors.append(f"{prefix}.id必须是非空字符串")
        elif object_id in seen_ids:
            errors.append(f"{prefix}.id与其他对象重复：{object_id}")
        else:
            seen_ids.add(object_id)

        object_type = item.get("type")
        if object_type not in SUPPORTED_TYPES:
            errors.append(f"{prefix}.type不是支持的场景类型")
            continue
        counts[object_type] += 1

        shared_result = validate_target(item)
        for error in shared_result["errors"]:
            errors.append(f"{prefix}.{error}")

        if object_type in {"box", "target", "wall"}:
            size = item.get("size")
            if not isinstance(size, dict):
                errors.append(f"{prefix}.size必须是包含width、height、depth的对象")
            else:
                for field in ("width", "height", "depth"):
                    value = size.get(field)
                    if not _is_number(value) or value <= 0:
                        errors.append(f"{prefix}.size.{field}必须是正数")

            color = item.get("color")
            if not isinstance(color, str) or not color.strip():
                errors.append(f"{prefix}.color必须是非空字符串")

        if object_type == "observer":
            direction = item.get("direction")
            if not isinstance(direction, dict):
                errors.append(f"{prefix}.direction必须是包含x、y、z的对象")
            else:
                direction_values = [direction.get(axis) for axis in ("x", "y", "z")]
                for axis, value in zip(("x", "y", "z"), direction_values):
                    if not _is_number(value):
                        errors.append(f"{prefix}.direction.{axis}必须是有效数值")
                if all(_is_number(value) for value in direction_values) and all(
                    value == 0 for value in direction_values
                ):
                    errors.append(f"{prefix}.direction不能是零向量")

            fov = item.get("fov")
            if not _is_number(fov) or not 0 < fov <= 180:
                errors.append(f"{prefix}.fov必须是0到180之间的数值")

            max_distance = item.get("maxDistance")
            if not _is_number(max_distance) or max_distance <= 0:
                errors.append(f"{prefix}.maxDistance必须是正数")

    if counts.get("observer", 0) != 1:
        errors.append("场景必须且只能包含一个observer")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "counts": dict(sorted(counts.items())),
    }
