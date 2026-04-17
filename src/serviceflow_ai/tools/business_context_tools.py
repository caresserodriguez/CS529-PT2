from typing import Type
from pathlib import Path
import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from crewai.tools import tool
from pathlib import Path
import json
from ._guardrails import validate_text_input, validate_filename, cap_tool_output



def _get_knowledge_file_path(filename: str) -> Path:
    """
    Returns the absolute path to a file inside the project's knowledge folder.
    """
    project_root = Path(__file__).resolve().parents[3]
    return project_root/"knowlege"/ filename


def _load_json_file(filename: str) -> dict:
    """
    Loads and returns JSON data from the knowledge folder.
    """
    validate_filename(filename)
    file_path = _get_knowledge_file_path(filename)

    if not file_path.exists():
        raise FileNotFoundError(f"Knowledge file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Description: This tool gives the agent general background information about the business it is working for
# It tells the agent what kind of company it is, what kind of services it offers, how it generally
# operates, what areas it serves, its hours, and the broad rules it follows for pricing and bookings.

# Why it is useful: Without this tool, the agent would have to guess what kind of business it is working for. This
# tool gives it the core company context so its reasoning stays grounded in the actual business.

# Agents using it: Primarily for Inquiry Analysis Agent
# Potentially for pricng agent, client response agent, profit optimization agent
class BusinessProfileToolInput(BaseModel):
    """
    Input schema for BusinessProfileTool.
    """
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
            business_profile = _load_json_file("company_profile.json")

            return json.dumps(
                {
                    "request_context": request_context,
                    "business_profile": business_profile
                },
                indent=2
            )

        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_business_profile",
                    "message": str(e)
                },
                indent=2
            )
    


# Description: This tool gives the agent the list of services the business offers, along with the basic details
# about each one. It helps the agent understand whether the customer is asking for a service the
# company actually provides, and what that service usually includes. 

# Why it is useful: A customer inquiry can be vague or broad. This tool helps the agent match the inquiry to the
# business's actual service offerings instead of making assumptions. 

# Agents using it: primarily inquiry analysis agent
# potentially pricing agent, client response agent
class ServiceCatalogueToolInput(BaseModel):
    """
    Input schema for ServiceCatalogueTool.
    """
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
            service_catalogue = _load_json_file("service_catalogue.json")

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
                {
                    "error": "failed_to_load_service_catalogue",
                    "message": str(e)
                },
                indent=2
            )


