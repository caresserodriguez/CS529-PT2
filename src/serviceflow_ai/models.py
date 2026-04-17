from typing import List, Optional
from pydantic import BaseModel, Field


class InquiryAnalysisOutput(BaseModel):
    service_type: str = Field(..., description="Type of service requested")
    job_scope: str = Field(..., description="Scope or description of the requested job")
    preferred_schedule: str = Field(..., description="Requested timing or scheduling preference")
    requested_extras: List[str] = Field(default_factory=list, description="Requested extras or add-ons")
    urgency: str = Field(..., description="Urgency level of the inquiry")
    customer_email: Optional[str] = Field(default=None, description="Customer email if present")
    missing_information: List[str] = Field(default_factory=list, description="Missing details needed later")


class ReadinessCheckOutput(BaseModel):
    staffing_status: str
    resource_material_status: str
    tools_equipment_status: str
    scheduling_feasibility: str
    readiness_risks: List[str] = Field(default_factory=list)
    cost_impact_notes: List[str] = Field(default_factory=list)
    overall_readiness: str


class CostingOutput(BaseModel):
    labor_cost: float
    materials_resources_cost: float
    equipment_operational_cost: float
    additional_burden_cost: float
    total_internal_cost: float
    main_cost_drivers: List[str] = Field(default_factory=list)


class PricingOutput(BaseModel):
    base_customer_price: float
    extras_price_total: float
    business_adjustments: float
    final_quoted_price: float
    pricing_rationale: str


class ProfitRecommendationOutput(BaseModel):
    recommendation_status: str
    profitability_assessment: str
    estimated_margin_commentary: str
    suggested_action: str
    rationale: str


class EmailDeliveryOutput(BaseModel):
    sent: bool
    status_message: str
    recipient: Optional[str] = None