from typing import Type
from pathlib import Path
import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from crewai.tools import tool
from pathlib import Path
import json
from ._guardrails import validate_filename, cap_tool_output


def _get_knowledge_file_path(filename: str) -> Path:
    """
    Returns the absolute path to a file inside the project's knowledge folder.
    """
    project_root = Path(__file__).resolve().parents[3]
    return project_root/ "knowledge" / filename

def _load_json_file(filename: str) -> dict:
    """
    Loads and returns JSON data from the knowledge dolfer
    """
    validate_filename(filename)
    file_path = _get_knowledge_file_path(filename)

    if not file_path.exists():
        raise FileNotFoundError(f"Knowledge file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# This tool gives the agent information about whether enough staff are available to
# handle the requested job. It tells the agent what the current staffing situation
# looks like, such as whether enough people are available, whether staffing is tight,
# and whether overtime might be needed.
#
# The Readiness Check Agent needs to know whether the business has enough people to
# actually take on the job before making recommendations.


class StaffingAvailabilityToolInput(BaseModel):
    """
    Input schema for StaffingAvailabilityTool.
    """
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
            staffing_data = _load_json_file("staffing_availability.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "staffing_availability": staffing_data
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_staffing_availability",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent information about schedule availability and workload for
# the requested time period. It tells the agent whether the requested slot is open,
# tight, or overbooked, and whether alternate time windows may be available.
#
# A business may have staff and resources available overall, but still not have room
# in the schedule for the requested date or time.


class ScheduleCapacityToolInput(BaseModel):
    """
    Input schema for ScheduleCapacityTool.
    """
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
            schedule_data = _load_json_file("schedule_capacity.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "schedule_capacity": schedule_data
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_schedule_capacity",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent information about materials, inventory, consumables, or
# other job-related resources. It tells the agent whether the business has enough of
# the non-staff resources needed to complete the job.
#
# A business may have the time and people for a job, but still not have enough materials
# or resources to do it properly.


class ResourceAvailabilityToolInput(BaseModel):
    """
    Input schema for ResourceAvailabilityTool.
    """
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
            resource_data = _load_json_file("resource_availability.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "resource_availability": resource_data
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_resource_availability",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent information whether the required tools, machinery, or
# equipment are ready and available. It tells the agent whether the business has the
# equipment needed for the job, whether that equipment is usable, and whether there
# are any limitations.
#
# It is useful because some jobs cannot be completed without specific tools or equipment,
# so the business needs to know if those are available before quoting confidently.


class EquipmentReadinessToolInput(BaseModel):
    """
    Input schema for EquipmentReadinessTool.
    """
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
            equipment_data = _load_json_file("equipment_readiness.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "equipment_readiness": equipment_data
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_equipment_readiness",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent information about whether the requested location falls
# within the business's normal service area. It tells the agent whether the business
# normally serves that area and whether travel affects feasibility or cost.
#
# A business may offer a service, but not in the customer's location. Travel can also
# affect cost, schedule, and whether the job should be accepted.


class TravelServiceAreaToolInput(BaseModel):
    """
    Input schema for TravelServiceAreaTool.
    """
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
            travel_data = _load_json_file("travel_service_area.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "travel_service_area": travel_data
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_travel_service_area",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent common risk signals related to the job. It highlights warning
# signs that may make the job harder, riskier, or less attractive for the business.
#
# This helps the system identify issues early instead of letting the agents overlook
# important operational red flags.


class RiskFlaggingToolInput(BaseModel):
    """
    Input schema for RiskFlaggingTool.
    """
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
            risk_data = _load_json_file("risk_flags.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "risk_flags": risk_data
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_risk_flags",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent a general sense of how simple or complex the requested job
# appears to be. It helps the agent judge whether the job is likely to be straightforward,
# moderate, or complex.
#
# Job complexity can affect staffing needs, cost, pricing, and whether the job is worth
# taking.


class JobComplexityToolInput(BaseModel):
    """
    Input schema for JobComplexityTool.
    """
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
            complexity_data = _load_json_file("job_complexity.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "job_complexity": complexity_data
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_job_complexity",
                    "message": str(e)
                },
                indent=2
            )
