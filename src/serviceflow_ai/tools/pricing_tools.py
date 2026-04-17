from crewai.tools import tool
from pathlib import Path
import json
from ._guardrails import validate_filename, cap_tool_output


def _get_knowledge_file_path(filename: str) -> Path:
    """
    Returns the absolute path to a file inside the project's knowledge folder.
    """
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "knowledge" / filename


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


# This tool gives the agent the internal business-side cost factors that may affect how
# expensive the job is to perform.
# It tells the agent what kinds of internal costs the business needs to think about, such
# as labor, materials, equipment use, travel, urgency, or coordination burden.
#
# The Costing Agent should not invent cost drivers from scratch. This tool gives it the
# internal cost factors the business cares about so the cost estimate is grounded in
# business logic.


class InternalCostFactorsToolInput(BaseModel):
    """
    Input schema for InternalCostFactorsTool.
    """
    request_context: str = Field(
        default="general",
        description="Optional context for why the internal cost factors are being requested."
    )


class InternalCostFactorsTool(BaseTool):
    name: str = "Internal Cost Factors Tool"
    description: str = (
        "Returns the internal cost factors the business considers when estimating "
        "the cost of a job. Use this tool when you need guidance on labor, materials, "
        "equipment, travel, urgency, or other business-side cost drivers."
    )
    args_schema: Type[BaseModel] = InternalCostFactorsToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            internal_cost_factors = _load_json_file("internal_cost_factors.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "internal_cost_factors": internal_cost_factors
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_internal_cost_factors",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent the business's general pricing rules and pricing approach.
# It tells the agent how the business usually turns internal cost and job scope into a
# customer-facing price.
#
# The Pricing Agent needs a consistent pricing framework instead of making up the quote
# logic each time.


class PricingPolicyToolInput(BaseModel):
    """
    Input schema for PricingPolicyTool.
    """
    request_context: str = Field(
        default="general",
        description="Optional context for why the pricing policy is being requested."
    )


class PricingPolicyTool(BaseTool):
    name: str = "Pricing Policy Tool"
    description: str = (
        "Returns the business's general pricing policy and quote-building rules. "
        "Use this tool when you need guidance on base pricing, markups, minimum "
        "charges, surcharges, or standard pricing adjustments."
    )
    args_schema: Type[BaseModel] = PricingPolicyToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            pricing_policy = _load_json_file("pricing_policy.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "pricing_policy": pricing_policy
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_pricing_policy",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent the business rules for what must appear in a valid quote and
# how quotes should be presented. It tells the agent what a proper quote needs to include,
# such as assumptions, clarifications, conditions, approval requirements, or validity rules.
#
# The Client Response Agent needs to know not just the price, but how the quote should be
# structured and what business rules should appear in it.


class QuotePolicyToolInput(BaseModel):
    """
    Input schema for QuotePolicyTool.
    """
    request_context: str = Field(
        default="general",
        description="Optional context for why the quote policy is being requested."
    )


class QuotePolicyTool(BaseTool):
    name: str = "Quote Policy Tool"
    description: str = (
        "Returns the business rules for how quotes should be structured and what "
        "they must include. Use this tool when you need quote-format guidance, "
        "assumption rules, clarification requirements, or approval-related conditions."
    )
    args_schema: Type[BaseModel] = QuotePolicyToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            quote_policy = _load_json_file("quote_policy.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "quote_policy": quote_policy
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_quote_policy",
                    "message": str(e)
                },
                indent=2
            )


# This tool gives the agent the business's profitability expectations. It tells the agent what
# counts as an acceptable margin or business outcome so it can decide whether a job should be
# accepted, revised, escalated, or declined.
#
# The Profit Maximization Agent needs a business standard for profitability instead of relying
# only on vague judgement.


class ProfitThresholdToolInput(BaseModel):
    """
    Input schema for ProfitThresholdTool.
    """
    request_context: str = Field(
        default="general",
        description="Optional context for why the profitability thresholds are being requested."
    )


class ProfitThresholdTool(BaseTool):
    name: str = "Profit Threshold Tool"
    description: str = (
        "Returns the business's profitability thresholds and margin expectations. "
        "Use this tool when you need to determine whether a proposed job is financially "
        "strong enough to accept, revise, escalate, or decline."
    )
    args_schema: Type[BaseModel] = ProfitThresholdToolInput

    def _run(self, request_context: str = "general") -> str:
        try:
            profit_thresholds = _load_json_file("profit_thresholds.json")
            return json.dumps(
                {
                    "request_context": request_context,
                    "profit_thresholds": profit_thresholds
                },
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": "failed_to_load_profit_thresholds",
                    "message": str(e)
                },
                indent=2
            )
