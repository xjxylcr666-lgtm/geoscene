import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.agent_service import AgentConfigurationError, AgentProviderError
from backend.main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_validate_target_endpoint(self):
        response = self.client.post(
            "/validate-target",
            json={
                "name": "观察目标",
                "position": {"x": -4, "y": 1, "z": 3},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"valid": True, "errors": []})

    def test_validate_current_scene_endpoint(self):
        config_path = Path(__file__).resolve().parents[2] / "src" / "scene-config.json"
        scene = json.loads(config_path.read_text(encoding="utf-8"))

        response = self.client.post("/validate-scene", json=scene)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["counts"]["target"], 3)

    def test_converts_saved_usgs_snapshot(self):
        data_path = (
            Path(__file__).resolve().parents[2]
            / "public"
            / "data"
            / "usgs-earthquakes-2025-01-01-to-07.geojson"
        )
        geojson = json.loads(data_path.read_text(encoding="utf-8"))

        response = self.client.post("/geojson/earthquakes-to-targets", json=geojson)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["metadata"]["provider"], "USGS Earthquake Hazards Program")
        self.assertEqual(len(payload["targets"]), 8)
        self.assertEqual(
            payload["metadata"]["coordinateMode"],
            "normalized_geographic_demo",
        )

    def test_rejects_invalid_geojson_endpoint_input(self):
        response = self.client.post(
            "/geojson/earthquakes-to-targets",
            json={"type": "Point"},
        )

        self.assertEqual(response.status_code, 400)

    def test_health_reports_configuration_without_secret(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["agent"]["provider"], "deepseek")
        self.assertNotIn("api_key", payload["agent"])

    def test_agent_instruction_length_is_limited(self):
        response = self.client.post(
            "/agent/plan",
            json={
                "instruction": "x" * 501,
                "available_target_ids": ["target-1"],
            },
        )

        self.assertEqual(response.status_code, 422)

    @patch("backend.main.plan_agent_command")
    def test_agent_plan_endpoint(self, plan):
        plan.return_value = {
            "kind": "tool_call",
            "tool_call_id": "call-1",
            "tool_name": "analyze_visibility",
            "arguments": {"target_id": "target-1"},
        }

        response = self.client.post(
            "/agent/plan",
            json={
                "instruction": "分析target-1",
                "available_target_ids": ["target-1"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["kind"], "tool_call")

    def test_agent_complete_rejects_mismatched_target(self):
        response = self.client.post(
            "/agent/complete",
            json={
                "instruction": "分析target-1",
                "tool_call_id": "call-1",
                "tool_name": "analyze_visibility",
                "arguments": {"target_id": "target-1"},
                "tool_result": {
                    "source": "geoscene_visibility_tool",
                    "target_id": "target-404",
                    "visible": False,
                    "reason": "不存在",
                    "distance": 0,
                    "angle": None,
                },
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_agent_complete_rejects_tool_result_type_mismatch(self):
        response = self.client.post(
            "/agent/complete",
            json={
                "instruction": "列出目标",
                "tool_call_id": "call-2",
                "tool_name": "list_scene_targets",
                "arguments": {},
                "tool_result": {
                    "source": "geoscene_visibility_tool",
                    "target_id": "target-1",
                    "visible": True,
                    "reason": "目标可见",
                    "distance": 7,
                    "angle": 0,
                },
            },
        )

        self.assertEqual(response.status_code, 400)

    @patch("backend.main.plan_agent_command")
    def test_missing_key_maps_to_503(self, plan):
        plan.side_effect = AgentConfigurationError("未配置")

        response = self.client.post(
            "/agent/plan",
            json={"instruction": "分析target-1", "available_target_ids": []},
        )

        self.assertEqual(response.status_code, 503)

    @patch("backend.main.plan_agent_command")
    def test_provider_failure_maps_to_502(self, plan):
        plan.side_effect = AgentProviderError("模型服务失败")

        response = self.client.post(
            "/agent/plan",
            json={"instruction": "分析target-1", "available_target_ids": []},
        )

        self.assertEqual(response.status_code, 502)

    def test_cors_allows_only_development_origin(self):
        allowed = self.client.options(
            "/agent/plan",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        rejected = self.client.options(
            "/agent/plan",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(
            allowed.headers.get("access-control-allow-origin"),
            "http://127.0.0.1:5173",
        )
        self.assertNotIn("access-control-allow-origin", rejected.headers)


if __name__ == "__main__":
    unittest.main()
