import unittest

from backend.geojson_adapter import GeoJsonConversionError, convert_earthquake_geojson
from backend.validation import validate_target


def earthquake_feature(event_id, magnitude, longitude, latitude, depth=10):
    return {
        "type": "Feature",
        "id": event_id,
        "properties": {
            "mag": magnitude,
            "place": f"测试地点 {event_id}",
            "time": 1736211916734,
            "url": f"https://example.test/{event_id}",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [longitude, latitude, depth],
        },
    }


class GeoJsonAdapterTests(unittest.TestCase):
    def test_converts_points_to_valid_targets(self):
        data = {
            "type": "FeatureCollection",
            "metadata": {"title": "测试地震"},
            "features": [
                earthquake_feature("a", 7.1, 87.3, 28.6),
                earthquake_feature("b", 5.5, -90.0, 10.0),
            ],
        }

        result = convert_earthquake_geojson(data)

        self.assertEqual(len(result["targets"]), 2)
        self.assertEqual(result["metadata"]["coordinateMode"], "normalized_geographic_demo")
        for target in result["targets"]:
            self.assertTrue(validate_target(target)["valid"])
            self.assertEqual(target["sourceData"]["provider"], "USGS")

    def test_magnitude_controls_color_and_height(self):
        data = {
            "type": "FeatureCollection",
            "features": [
                earthquake_feature("large", 7.1, 10, 10),
                earthquake_feature("small", 5.1, 20, 20),
            ],
        }

        result = convert_earthquake_geojson(data)
        large, small = result["targets"]

        self.assertEqual(large["color"], "#ff3344")
        self.assertGreater(large["size"]["height"], small["size"]["height"])

    def test_invalid_features_are_skipped_with_warning(self):
        data = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": None, "properties": {}},
                earthquake_feature("valid", 5.5, 1, 2),
            ],
        }

        result = convert_earthquake_geojson(data)

        self.assertEqual(len(result["targets"]), 1)
        self.assertEqual(len(result["warnings"]), 1)

    def test_rejects_non_feature_collection(self):
        with self.assertRaises(GeoJsonConversionError):
            convert_earthquake_geojson({"type": "Point"})

    def test_rejects_collection_without_valid_points(self):
        with self.assertRaises(GeoJsonConversionError):
            convert_earthquake_geojson(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {"type": "Feature", "geometry": None, "properties": {}},
                    ],
                }
            )


if __name__ == "__main__":
    unittest.main()
