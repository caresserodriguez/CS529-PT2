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


def _load_uploaded_business_text(filename: str) -> str:
    validate_filename(filename)
    file_path = _get_uploaded_business_file_path(filename)
    if not file_path.exists():
        raise FileNotFoundError(f"Uploaded business file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


class InternalCostFactorsToolInput(BaseModel):
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
            pricing_data = _load_uploaded_business_json("pricing_data.json")
            return json.dumps(
                {"request_context": request_context, "internal_cost_factors": pricing_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_internal_cost_factors", "message": str(e)},
                indent=2
            )


class PricingPolicyToolInput(BaseModel):
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
            pricing_data = _load_uploaded_business_json("pricing_data.json")
            return json.dumps(
                {"request_context": request_context, "pricing_policy": pricing_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_pricing_policy", "message": str(e)},
                indent=2
            )


class QuotePolicyToolInput(BaseModel):
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
            policy_text = _load_uploaded_business_text("business_policies.txt")
            return json.dumps(
                {"request_context": request_context, "quote_policy": policy_text},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_quote_policy", "message": str(e)},
                indent=2
            )


class ProfitThresholdToolInput(BaseModel):
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
            pricing_data = _load_uploaded_business_json("pricing_data.json")
            return json.dumps(
                {"request_context": request_context, "profit_thresholds": pricing_data},
                indent=2
            )
        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_profit_thresholds", "message": str(e)},
                indent=2
            )
