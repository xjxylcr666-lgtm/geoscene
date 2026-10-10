import unittest
from types import SimpleNamespace

from backend.agent_service import (
    AgentProviderError,
    complete_agent_command,
    parse_tool_plan,
    plan_agent_command,
)


def tool_message(arguments, name="analyze_visibility", call_id="call-1"):
    return SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id=call_id,
                function=SimpleNamespace(name=name, arguments=arguments),
            )
        ],
    )


class FailingCompletions:
    def create(self, **kwargs):
        raise RuntimeError("provider unavailable")


class FixedCompletions:
    def __init__(self, message):
        self.message = message

    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=self.message)]
        )


class AgentServiceTests(unittest.TestCase):
    def test_valid_tool_call(self):
        result = parse_tool_plan(
            tool_message('{"target_id":"target-1"}'),
            ["target-1"],
        )

        self.assertEqual(result["kind"], "tool_call")
        self.assertEqual(result["arguments"], {"target_id": "target-1"})

    def test_list_targets_tool_has_no_required_arguments(self):
        result = parse_tool_plan(
            tool_message("{}", name="list_scene_targets"),
            ["target-1", "target-2"],
        )

        self.assertEqual(result["kind"], "tool_call")
        self.assertEqual(result["tool_name"], "list_scene_targets")
        self.assertEqual(result["arguments"], {})

    def test_missing_target_parameter(self):
        result = parse_tool_plan(tool_message("{}"), ["target-1"])

        self.assertEqual(result["kind"], "error")
        self.assertEqual(result["code"], "missing_target_id")

    def test_invalid_target_object(self):
        result = parse_tool_plan(
            tool_message('{"target_id":"target-404"}'),
            ["target-1"],
        )

        self.assertEqual(result["kind"], "error")
        self.assertEqual(result["code"], "invalid_target_id")

    def test_provider_execution_failure(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=FailingCompletions())
        )

        with self.assertRaises(AgentProviderError):
            plan_agent_command("分析target-1", ["target-1"], client=client)

    def test_missing_information_returns_model_message(self):
        message = SimpleNamespace(
            content="请告诉我要分析哪个目标ID。",
            tool_calls=None,
        )

        result = parse_tool_plan(message, ["target-1"])

        self.assertEqual(result["kind"], "message")
        self.assertIn("目标ID", result["message"])

    def test_model_cannot_overwrite_geometry_result(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=FixedCompletions(
                    SimpleNamespace(content="模型错误地声称目标可见")
                )
            )
        )
        tool_result = {
            "source": "geoscene_visibility_tool",
            "target_id": "target-1",
            "visible": False,
            "reason": "位于视野外",
            "distance": 3.162277,
            "angle": 71.565,
        }

        result = complete_agent_command(
            "分析target-1",
            "call-1",
            "analyze_visibility",
            {"target_id": "target-1"},
            tool_result,
            client=client,
        )

        self.assertEqual(
            result["message"],
            "target-1 不可见：位于视野外（距离约 3.16，角度约 71.56°）。",
        )

    def test_model_cannot_invent_target_list(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=FixedCompletions(
                    SimpleNamespace(content="模型声称还有target-404")
                )
            )
        )
        tool_result = {
            "source": "geoscene_target_list_tool",
            "targets": [
                {
                    "id": "target-1",
                    "name": "观察目标",
                    "position": {"x": -4, "y": 1, "z": 3},
                }
            ],
        }

        result = complete_agent_command(
            "有哪些目标",
            "call-2",
            "list_scene_targets",
            {},
            tool_result,
            client=client,
        )

        self.assertEqual(
            result["message"],
            "当前场景共有 1 个目标：target-1（观察目标）。",
        )

    def test_list_result_can_trigger_visibility_follow_up(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=FixedCompletions(
                    tool_message('{"target_id":"target-2"}')
                )
            )
        )
        tool_result = {
            "source": "geoscene_target_list_tool",
            "targets": [
                {
                    "id": "target-2",
                    "name": "正前方目标",
                    "position": {"x": 2, "y": 1, "z": 0},
                }
            ],
        }

        result = complete_agent_command(
            "先查看场景目标，再分析正前方目标",
            "call-list",
            "list_scene_targets",
            {},
            tool_result,
            client=client,
        )

        self.assertEqual(result["kind"], "tool_call")
        self.assertEqual(result["tool_name"], "analyze_visibility")
        self.assertEqual(result["arguments"], {"target_id": "target-2"})

    def test_follow_up_cannot_select_target_outside_real_list(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=FixedCompletions(
                    tool_message('{"target_id":"target-404"}')
                )
            )
        )
        tool_result = {
            "source": "geoscene_target_list_tool",
            "targets": [
                {
                    "id": "target-2",
                    "name": "正前方目标",
                    "position": {"x": 2, "y": 1, "z": 0},
                }
            ],
        }

        result = complete_agent_command(
            "分析不存在的目标",
            "call-list",
            "list_scene_targets",
            {},
            tool_result,
            client=client,
        )

        self.assertEqual(result["kind"], "error")
        self.assertEqual(result["code"], "invalid_target_id")


if __name__ == "__main__":
    unittest.main()
