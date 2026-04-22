from typing import Type
from pathlib import Path
import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from serviceflow_ai.guardrails import validate_text_input, validate_filename, cap_tool_output


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


class BusinessProfileToolInput(BaseModel):
    request_context: str = Field(
        default="general",
        description="Optional context for why the business profile is being requested."
    )

class BusinessProfileTool(BaseTool):
    name: str = "Business Profile Tool"
    description: str = (
        "Returns the business's core operating profile. Use this tool when you need "
        "general information about the business, including its service categories, "
        "pricing style, operating hours, supported areas, and booking policies."
    )
    args_schema: Type[BaseModel] = BusinessProfileToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            business_profile = _load_uploaded_business_json("company_profile.json")
            return json.dumps(
                {"request_context": request_context, "business_profile": business_profile},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_business_profile", "message": str(e)},
                indent=2
            )


class ServiceCatalogueToolInput(BaseModel):
    requested_service: str = Field(
        default="",
        description="Optional service name or category to look up in the service catalogue."
    )

class ServiceCatalogueTool(BaseTool):
    name: str = "Service Catalogue Tool"
    description: str = (
        "Returns the business's service catalogue and basic service definitions. "
        "Use this tool when you need to determine what services the business offers, "
        "what each service includes, and whether a requested service matches the "
        "business's actual offerings."
    )
    args_schema: Type[BaseModel] = ServiceCatalogueToolInput

    def _run(self, requested_service: str = "") -> str:
        try:
            service_catalogue = _load_uploaded_business_json("service_catalogue.json")

            if requested_service:
                requested_service_lower = requested_service.strip().lower()
                matched_services = [
                    service for service in service_catalogue.get("services", [])
                    if requested_service_lower in service.get("service_name", "").lower()
                    or requested_service_lower in service.get("category", "").lower()
                ]
                return json.dumps(
                    {
                        "requested_service": requested_service,
                        "matched_services": matched_services,
                        "match_count": len(matched_services)
                    },
                    indent=2
                )

            return json.dumps(service_catalogue, indent=2)

        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_service_catalogue", "message": str(e)},
                indent=2
            )
