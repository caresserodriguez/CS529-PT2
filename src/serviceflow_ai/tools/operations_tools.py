from typing import Type
from pathlib import Path
import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from serviceflow_ai.guardrails import validate_filename, cap_tool_output


def _get_uploaded_business_file_path(filename: str) -> Path:
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "data" / "uploads" / "current_business" / filename


def _load_uploaded_business_json(filename: str) -> dict:
    validate_filename(filename)
    file_path = _get_uploaded_business_file_path(filename)
    if not file_path.exists():
        raise FileNotFoundError(f"Uploaded business file not found: {file_path}")
    if file_path.stat().st_size == 0:
        raise ValueError(f"Uploaded business file is empty: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


class StaffingAvailabilityToolInput(BaseModel):
    request_context: str = Field(
        default="general",
        description="Optional context for why staffing availability is being requested."
    )


class StaffingAvailabilityTool(BaseTool):
    name: str = "Staffing Availability Tool"
    description: str = (
        "Returns staffing availability information relevant to the requested job. "
        "Use this tool when you need to assess whether enough staff are available, "
        "whether staffing is tight, or whether overtime may be required."
    )
    args_schema: Type[BaseModel] = StaffingAvailabilityToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            staffing_data = _load_uploaded_business_json("staffing_availability.json")
            return json.dumps(
                {"request_context": request_context, "staffing_availability": staffing_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_staffing_availability", "message": str(e)},
                indent=2
            )


class ScheduleCapacityToolInput(BaseModel):
    request_context: str = Field(
        default="general",
        description="Optional context for why schedule capacity is being requested."
    )


class ScheduleCapacityTool(BaseTool):
    name: str = "Schedule Capacity Tool"
    description: str = (
        "Returns schedule capacity information for the requested time period. "
        "Use this tool when you need to determine whether the current scheduling "
        "capacity is open, tight, or overbooked."
    )
    args_schema: Type[BaseModel] = ScheduleCapacityToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            schedule_data = _load_uploaded_business_json("schedule_capacity.json")
            return json.dumps(
                {"request_context": request_context, "schedule_capacity": schedule_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_schedule_capacity", "message": str(e)},
                indent=2
            )


class ResourceAvailabilityToolInput(BaseModel):
    request_context: str = Field(
        default="general",
        description="Optional context for why resource availability is being requested."
    )


class ResourceAvailabilityTool(BaseTool):
    name: str = "Resource Availability Tool"
    description: str = (
        "Returns availability information for materials, inventory, or other resources "
        "needed for the requested job. Use this tool when you need to assess whether "
        "resource levels are sufficient or whether shortages may affect readiness or cost."
    )
    args_schema: Type[BaseModel] = ResourceAvailabilityToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            resource_data = _load_uploaded_business_json("resource_availability.json")
            return json.dumps(
                {"request_context": request_context, "resource_availability": resource_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_resource_availability", "message": str(e)},
                indent=2
            )


class EquipmentReadinessToolInput(BaseModel):
    request_context: str = Field(
        default="general",
        description="Optional context for why equipment readiness is being requested."
    )


class EquipmentReadinessTool(BaseTool):
    name: str = "Equipment Readiness Tool"
    description: str = (
        "Returns readiness information for tools, machinery, or equipment required "
        "for the job. Use this tool when you need to determine whether the necessary "
        "equipment is available, usable, or limited."
    )
    args_schema: Type[BaseModel] = EquipmentReadinessToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            equipment_data = _load_uploaded_business_json("equipment_readiness.json")
            return json.dumps(
                {"request_context": request_context, "equipment_readiness": equipment_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_equipment_readiness", "message": str(e)},
                indent=2
            )


class TravelServiceAreaToolInput(BaseModel):
    request_context: str = Field(
        default="general",
        description="Optional context for why travel/service area information is being requested."
    )


class TravelServiceAreaTool(BaseTool):
    name: str = "Travel Service Area Tool"
    description: str = (
        "Returns information about whether requested job locations fall within the "
        "business's normal service area and whether travel affects readiness or cost. "
        "Use this tool when location or travel burden matters for the job."
    )
    args_schema: Type[BaseModel] = TravelServiceAreaToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            travel_data = _load_uploaded_business_json("service_area.json")
            return json.dumps(
                {"request_context": request_context, "travel_service_area": travel_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_travel_service_area", "message": str(e)},
                indent=2
            )


class RiskFlaggingToolInput(BaseModel):
    request_context: str = Field(
        default="general",
        description="Optional context for why risk flags are being requested."
    )


class RiskFlaggingTool(BaseTool):
    name: str = "Risk Flagging Tool"
    description: str = (
        "Returns operational risk flags related to the requested job. Use this tool "
        "when you need to identify warning signs such as urgency, understaffing, "
        "unclear scope, shortages, or other business risks."
    )
    args_schema: Type[BaseModel] = RiskFlaggingToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            risk_data = _load_uploaded_business_json("risk_flags.json")
            return json.dumps(
                {"request_context": request_context, "risk_flags": risk_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_risk_flags", "message": str(e)},
                indent=2
            )


class JobComplexityToolInput(BaseModel):
    request_context: str = Field(
        default="general",
        description="Optional context for why job complexity information is being requested."
    )


class JobComplexityTool(BaseTool):
    name: str = "Job Complexity Tool"
    description: str = (
        "Returns a general complexity assessment framework for service jobs. Use this "
        "tool when you need to estimate whether a job is simple, moderate, or complex "
        "and how that may affect cost or operations."
    )
    args_schema: Type[BaseModel] = JobComplexityToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            complexity_data = _load_uploaded_business_json("job_complexity.json")
            return json.dumps(
                {"request_context": request_context, "job_complexity": complexity_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_job_complexity", "message": str(e)},
                indent=2
            )
