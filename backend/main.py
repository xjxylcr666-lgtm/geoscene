from typing import Annotated, Any, Literal
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.agent_service import (
    AgentConfigurationError,
    AgentProviderError,
    agent_status,
    complete_agent_command,
    plan_agent_command,
)
from backend.geojson_adapter import GeoJsonConversionError, convert_earthquake_geojson
from backend.scene_validation import validate_scene
from backend.validation import validate_target


app = FastAPI(title="GeoScene", version="0.1.0")
from backend.inspection import router as inspection_router
app.include_router(inspection_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv('GEOSCENE_ALLOWED_ORIGINS', 'http://127.0.0.1:5173').split(',') if origin.strip()],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def read_root():
    return {"message": "GeoScene校验服务正在运行"}


@app.post("/validate-target")
def validate_target_endpoint(target: dict[str, Any]):
    return validate_target(target)


@app.post("/validate-scene")
def validate_scene_endpoint(objects: list[Any]):
    return validate_scene(objects)


@app.post("/geojson/earthquakes-to-targets")
def earthquake_geojson_endpoint(data: dict[str, Any]):
    try:
        return convert_earthquake_geojson(data)
    except GeoJsonConversionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


class AgentPlanRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=500)
    available_target_ids: list[str] = Field(max_length=100)


class VisibilityToolResult(BaseModel):
    source: Literal["geoscene_visibility_tool"]
    target_id: str
    visible: bool
    reason: str
    distance: float
    angle: float | None = None
    coordinate_mode: Literal["local_cartesian", "normalized_geographic_demo"] = (
        "local_cartesian"
    )


class Position3D(BaseModel):
    x: float
    y: float
    z: float


class SceneTargetSummary(BaseModel):
    id: str
    name: str
    position: Position3D


class SceneTargetListToolResult(BaseModel):
    source: Literal["geoscene_target_list_tool"]
    targets: list[SceneTargetSummary]


AgentToolResult = Annotated[
    VisibilityToolResult | SceneTargetListToolResult,
    Field(discriminator="source"),
]


class AgentCompleteRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=500)
    tool_call_id: str = Field(min_length=1, max_length=200)
    tool_name: Literal["analyze_visibility", "list_scene_targets"]
    arguments: dict[str, Any]
    tool_result: AgentToolResult


@app.get("/health")
def health_endpoint():
    return {
        "status": "ok",
        "validation": "ready",
        "agent": agent_status(),
    }


def _run_agent(operation):
    try:
        return operation()
    except AgentConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except AgentProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/agent/plan")
def agent_plan_endpoint(request: AgentPlanRequest):
    return _run_agent(
        lambda: plan_agent_command(
            request.instruction,
            request.available_target_ids,
        )
    )


@app.post("/agent/complete")
def agent_complete_endpoint(request: AgentCompleteRequest):
    if request.tool_name == "analyze_visibility":
        if not isinstance(request.tool_result, VisibilityToolResult):
            raise HTTPException(status_code=400, detail="工具名称与结果类型不一致")
        if request.arguments.get("target_id") != request.tool_result.target_id:
            raise HTTPException(status_code=400, detail="工具结果与目标ID不一致")
    elif not isinstance(request.tool_result, SceneTargetListToolResult):
        raise HTTPException(status_code=400, detail="工具名称与结果类型不一致")

    return _run_agent(
        lambda: complete_agent_command(
            request.instruction,
            request.tool_call_id,
            request.tool_name,
            request.arguments,
            request.tool_result.model_dump(),
        )
    )
