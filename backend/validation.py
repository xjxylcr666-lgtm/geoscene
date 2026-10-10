def validate_target(target):
    """校验 GeoScene 目标的名称和三维坐标。"""
    errors = []

    name = target.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("name必须是非空字符串")

    position = target.get("position")
    if not isinstance(position, dict):
        errors.append("position必须是包含x、y、z的对象")
    else:
        for axis in ("x", "y", "z"):
            current_number = position.get(axis)
            if not isinstance(current_number, (int, float)) or isinstance(
                current_number, bool
            ):
                errors.append(f"position.{axis}必须是有效数值")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
