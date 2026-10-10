import json
import unittest
from pathlib import Path

from backend.validation import validate_target


CONFIG_PATH = Path(__file__).resolve().parents[2] / "src" / "scene-config.json"


class SceneConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.objects = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_object_ids_are_unique(self):
        ids = [item["id"] for item in self.objects]

        self.assertEqual(len(ids), len(set(ids)))

    def test_all_targets_pass_shared_validation(self):
        targets = [item for item in self.objects if item["type"] == "target"]

        self.assertGreaterEqual(len(targets), 3)
        for target in targets:
            with self.subTest(target_id=target["id"]):
                self.assertEqual(
                    validate_target(target),
                    {"valid": True, "errors": []},
                )

    def test_demo_target_positions_are_stable(self):
        targets = {
            item["id"]: item
            for item in self.objects
            if item["type"] == "target"
        }

        self.assertEqual(targets["target-1"]["position"], {"x": -4, "y": 1, "z": 3})
        self.assertEqual(targets["target-2"]["position"], {"x": 2, "y": 1, "z": 0})
        self.assertEqual(targets["target-3"]["position"], {"x": 6, "y": 1, "z": 0})


if __name__ == "__main__":
    unittest.main()
