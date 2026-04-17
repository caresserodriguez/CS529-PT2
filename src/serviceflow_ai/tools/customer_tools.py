from pathlib import Path
from crewai.tools import tool
import json
from ._guardrails import validate_email_input, validate_filename, cap_tool_output


def _get_knowledge_file_path(filename: str) -> Path:
    """
    Returns the absolute path to a file inside the project's knowledge folder.
    """
    project_root = Path(__file__).resolve().parents[3]
    return project_root/ "knowledge" / filename

def _load_json_file(filename: str) -> dict:
    """
    Loads and returns JSON data from the knowledge folder.
    """
    validate_filename(filename)
    file_path = _get_knowledge_file_path(filename)

    if not file_path.exists():
        raise FileNotFoundError(f"Knowlege file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# This tool gives the agent background informaiton about the customer based on past
# interactions or stored customer records. It tells the agent whether this is a
# returning customer and gives any useful past context, such as their service history,
# preferences, common requests, or communication style.


# Without this tool, the agent would treat every customer like a brand new one. This
# tool helps the agent personalize its reaosning and responses using what is already
# known about the customer.

# Agents using it: Inquiry analysis agent, client response agent
# potentially profit optimization agent
class CustomerHistoryToolInput(BaseModel):
    """
    Input schema for CustomerHistoryTool.
    """
    customer_email: str = Field(
        default="",
        description="Customer email used to look up prior customer history."
    )

class CustomerHistoryTool(BaseTool):
    name: str = "Customer History Tool"
    description: str = (
        "Returns customer history and prior context for the current customer. "
        "Use this tool when you need background information such as past services, "
        "preferences, communication style, recurring requests, or other useful "
        "customer-specific notes."
    )

    args_schema: Type[BaseModel] = CustomerHistoryToolInput

    def _run(self, customer_email: str = "") -> str:
        try:
            customer_history_data = _load_json_file("customer_history.json")
 
            if customer_email:
                customer_email_lower = customer_email.strip().lower()
                customer_record = customer_history_data.get("customers", {}).get(customer_email_lower)

                if customer_record:
                    return json.dumps(
                        {
                            "customer_email": customer_email,
                            "customer_found": True,
                            "customer_history": customer_record
                        },
                        indent=2
                    )

                return json.dumps(
                    {
                        "customer_email": customer_email,
                        "customer_found": False,
                        "message": "No prior customer history found."
                    },
                    indent=2
                )

            return json.dumps(customer_history_data, indent=2)

        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_customer_history",
                    "message": str(e)
                },
                indent=2
            )
