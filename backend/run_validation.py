import json

from validation import validate_target


valid_target = {
    "name": "lcr",
    "position": {
        "x": 5,
        "y": 4,
        "z": 3,
    },
}

invalid_target = {
    "name": "   ",
    "position": {
        "x": 5,
        "y": "4",
        "z": 3,
    },
}

for label, target in (
    ("正确样本", valid_target),
    ("错误样本", invalid_target),
):
    result = validate_target(target)
    print(label)
    print(json.dumps(result, ensure_ascii=False, indent=2))
