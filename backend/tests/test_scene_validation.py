import copy
import json
import unittest
from pathlib import Path

from backend.scene_validation import validate_scene


CONFIG_PATH = Path(__file__).resolve().parents[2] / "src" / "scene-config.json"


class SceneValidationTests(unittest.TestCase):
    def setUp(self):
        self.scene = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_current_scene_is_valid(self):
        result = validate_scene(self.scene)

        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["counts"]["target"], 3)
        self.assertEqual(result["counts"]["observer"], 1)

    def test_duplicate_id_is_rejected(self):
        scene = copy.deepcopy(self.scene)
        scene[1]["id"] = scene[0]["id"]

        result = validate_scene(scene)

        self.assertFalse(result["valid"])
        self.assertTrue(any("重复" in error for error in result["errors"]))

    def test_zero_observer_direction_is_rejected(self):
        scene = copy.deepcopy(self.scene)
        observer = next(item for item in scene if item["type"] == "observer")
        observer["direction"] = {"x": 0, "y": 0, "z": 0}

        result = validate_scene(scene)

        self.assertFalse(result["valid"])
        self.assertTrue(any("零向量" in error for error in result["errors"]))

    def test_negative_size_is_rejected(self):
        scene = copy.deepcopy(self.scene)
        target = next(item for item in scene if item["type"] == "target")
        target["size"]["width"] = -1

        result = validate_scene(scene)

        self.assertFalse(result["valid"])
        self.assertTrue(any("size.width" in error for error in result["errors"]))

    def test_unknown_type_is_rejected(self):
        scene = copy.deepcopy(self.scene)
        scene[0]["type"] = "building"

        result = validate_scene(scene)

        self.assertFalse(result["valid"])
        self.assertTrue(any("type" in error for error in result["errors"]))

    def test_scene_requires_exactly_one_observer(self):
        scene = [item for item in copy.deepcopy(self.scene) if item["type"] != "observer"]

        result = validate_scene(scene)

        self.assertFalse(result["valid"])
        self.assertIn("场景必须且只能包含一个observer", result["errors"])


if __name__ == "__main__":
    unittest.main()
