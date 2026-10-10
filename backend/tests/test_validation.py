import unittest

from backend.validation import validate_target


class ValidateTargetTests(unittest.TestCase):
    def test_valid_target(self):
        target = {
            "name": "观察目标",
            "position": {"x": -4, "y": 1, "z": 3},
        }

        self.assertEqual(
            validate_target(target),
            {"valid": True, "errors": []},
        )

    def test_empty_name(self):
        target = {
            "name": "   ",
            "position": {"x": -4, "y": 1, "z": 3},
        }

        result = validate_target(target)

        self.assertFalse(result["valid"])
        self.assertIn("name必须是非空字符串", result["errors"])

    def test_missing_coordinate(self):
        target = {
            "name": "观察目标",
            "position": {"x": -4, "y": 1},
        }

        result = validate_target(target)

        self.assertFalse(result["valid"])
        self.assertIn("position.z必须是有效数值", result["errors"])

    def test_string_and_boolean_coordinates(self):
        target = {
            "name": "观察目标",
            "position": {"x": "-4", "y": True, "z": 3},
        }

        result = validate_target(target)

        self.assertFalse(result["valid"])
        self.assertIn("position.x必须是有效数值", result["errors"])
        self.assertIn("position.y必须是有效数值", result["errors"])

    def test_position_must_be_object(self):
        target = {"name": "观察目标", "position": [1, 2, 3]}

        result = validate_target(target)

        self.assertEqual(
            result,
            {
                "valid": False,
                "errors": ["position必须是包含x、y、z的对象"],
            },
        )


if __name__ == "__main__":
    unittest.main()
