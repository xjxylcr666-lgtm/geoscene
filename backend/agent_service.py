import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

VISIBILITY_TOOL_NAME = "analyze_visibility"
LIST_TARGETS_TOOL_NAME = "list_scene_targets"


class AgentConfigurationError(RuntimeError):
    pass


class AgentProviderError(RuntimeError):
    pass


def _client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise AgentConfigurationError("DeepSeek API Key尚未在本机配置")

    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        timeout=30.0,
        max_retries=1,
    )


def _model_name() -> str:
    return os.getenv("DEEPSEEK_MODEL", "deepseek-flash")


def agent_status() -> dict[str, Any]:
    return {
        "provider": "deepseek",
        "model": _model_name(),
        "api_key_configured": bool(os.getenv("DEEPSEEK_API_KEY", "").strip()),
    }


def _usage(response: Any) -> dict[str, int] | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": LIST_TARGETS_TOOL_NAME,
                "description": (
                    "读取当前GeoScene浏览器实际加载的目标列表，"
                    "返回每个目标的ID、名称和三维位置。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": VISIBILITY_TOOL_NAME,
                "description": (
                    "调用当前GeoScene浏览器中的真实可见性分析。"
                    "它检查距离、视野角度和场景障碍物，不能由模型自行计算。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_id": {
                            "type": "string",
                            "description": "要分析的场景目标ID，例如target-1",
                        }
                    },
                    "required": ["target_id"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def parse_tool_plan(message: Any, available_target_ids: list[str]) -> dict[str, Any]:
    tool_calls = getattr(message, "tool_calls", None)
    content = getattr(message, "content", None)

    if not tool_calls:
        return {
            "kind": "message",
            "message": content or "请提供要分析的目标ID。",
        }

    tool_call = tool_calls[0]
    function = getattr(tool_call, "function", None)
    tool_name = getattr(function, "name", "")
    arguments_text = getattr(function, "arguments", "")

    if tool_name not in {VISIBILITY_TOOL_NAME, LIST_TARGETS_TOOL_NAME}:
        return {
            "kind": "error",
            "code": "unsupported_tool",
            "message": f"模型请求了不允许的工具：{tool_name or '未知工具'}",
        }

    try:
        arguments = json.loads(arguments_text)
    except (TypeError, json.JSONDecodeError):
        return {
            "kind": "error",
            "code": "invalid_arguments",
            "message": "模型生成的工具参数不是有效JSON。",
        }

    if not isinstance(arguments, dict):
        return {
            "kind": "error",
            "code": "invalid_arguments",
            "message": "模型生成的工具参数必须是JSON对象。",
        }

    if tool_name == LIST_TARGETS_TOOL_NAME:
        return {
            "kind": "tool_call",
            "tool_call_id": getattr(tool_call, "id", ""),
            "tool_name": LIST_TARGETS_TOOL_NAME,
            "arguments": {},
        }

    target_id = arguments.get("target_id")
    if not isinstance(target_id, str) or not target_id.strip():
        return {
            "kind": "error",
            "code": "missing_target_id",
            "message": "工具调用缺少有效的target_id。",
        }

    target_id = target_id.strip()
    if target_id not in available_target_ids:
        return {
            "kind": "error",
            "code": "invalid_target_id",
            "message": f"场景中不存在目标ID：{target_id}",
        }

    return {
        "kind": "tool_call",
        "tool_call_id": getattr(tool_call, "id", ""),
        "tool_name": VISIBILITY_TOOL_NAME,
        "arguments": {"target_id": target_id},
    }


def plan_agent_command(
    instruction: str,
    available_target_ids: list[str],
    client: Any | None = None,
) -> dict[str, Any]:
    provider = client or _client()
    target_list = ", ".join(available_target_ids) or "无"
    messages = [
        {
            "role": "system",
            "content": (
                "你是GeoScene场景分析Agent。你不能自行判断目标是否可见。"
                f"当前可用目标ID：{target_list}。"
                f"用户询问当前有哪些目标时，调用{LIST_TARGETS_TOOL_NAME}。"
                "如果用户要求先查看目标、再按名称分析可见性，必须先调用目标列表工具。"
                "用户明确提供现有目标ID并要求分析可见性时，"
                f"调用{VISIBILITY_TOOL_NAME}。缺少目标ID时应提问；"
                "目标不存在时应说明。不能凭空编造目标列表或几何结论。"
            ),
        },
        {"role": "user", "content": instruction},
    ]

    try:
        response = provider.chat.completions.create(
            model=_model_name(),
            messages=messages,
            tools=_tool_definitions(),
            tool_choice="auto",
            temperature=0,
        )
    except Exception as error:
        raise AgentProviderError("DeepSeek请求失败") from error

    message = response.choices[0].message
    plan = parse_tool_plan(message, available_target_ids)
    plan["instruction"] = instruction
    plan["usage"] = _usage(response)
    return plan


def complete_agent_command(
    instruction: str,
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    tool_result: dict[str, Any],
    client: Any | None = None,
) -> dict[str, Any]:
    provider = client or _client()
    arguments_json = json.dumps(arguments, ensure_ascii=False)
    result_json = json.dumps(tool_result, ensure_ascii=False)
    messages = [
        {
            "role": "system",
            "content": (
                "你是GeoScene场景分析Agent。工具结果是唯一可信的几何结论。"
                "禁止修改工具返回字段，禁止编造目标或额外计算。"
                "如果刚执行的是目标列表工具，而用户还要求分析列表中的某个目标，"
                "请根据真实名称找到ID并调用可见性工具；不要重复调用列表工具。"
                "否则用一句简短中文说明结果。"
            ),
        },
        {"role": "user", "content": instruction},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": arguments_json,
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result_json,
        },
    ]

    request: dict[str, Any] = {
        "model": _model_name(),
        "messages": messages,
        "temperature": 0,
    }
    if tool_name == LIST_TARGETS_TOOL_NAME:
        request["tools"] = _tool_definitions()
        request["tool_choice"] = "auto"

    try:
        response = provider.chat.completions.create(**request)
    except Exception as error:
        raise AgentProviderError("DeepSeek结果说明请求失败") from error

    # The second model call completes the tool-call conversation, but it is not
    # allowed to overwrite the measured geometry result shown to the user.
    response_message = response.choices[0].message
    if tool_name == LIST_TARGETS_TOOL_NAME and getattr(
        response_message, "tool_calls", None
    ):
        available_ids = [target["id"] for target in tool_result["targets"]]
        next_plan = parse_tool_plan(response_message, available_ids)
        next_plan["instruction"] = instruction
        next_plan["usage"] = _usage(response)
        return next_plan

    model_acknowledgement = response_message.content or ""
    if tool_name == VISIBILITY_TOOL_NAME:
        visible_text = "可见" if tool_result["visible"] else "不可见"
        distance_text = f'{tool_result["distance"]:.2f}'
        angle = tool_result.get("angle")
        angle_text = "" if angle is None else f"，角度约 {angle:.2f}°"
        verified_message = (
            f'{tool_result["target_id"]} {visible_text}：{tool_result["reason"]}'
            f"（距离约 {distance_text}{angle_text}）。"
        )
        if tool_result.get("coordinate_mode") == "normalized_geographic_demo":
            verified_message += " 当前使用归一化演示坐标，距离不代表真实地理距离。"
    elif tool_name == LIST_TARGETS_TOOL_NAME:
        targets = tool_result["targets"]
        target_text = "、".join(
            f'{target["id"]}（{target["name"]}）' for target in targets
        )
        verified_message = (
            f"当前场景共有 {len(targets)} 个目标：{target_text}。"
            if targets
            else "当前场景没有目标。"
        )
    else:
        raise ValueError(f"不支持的工具：{tool_name}")

    return {
        "message": verified_message,
        "tool_result": tool_result,
        "model_acknowledged": bool(model_acknowledgement.strip()),
        "usage": _usage(response),
    }
