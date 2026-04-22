from typing import List, Optional
from pydantic import BaseModel, Field


class InquiryAnalysisOutput(BaseModel):
    service_type: Optional[str] = Field(
        default=None,
        description="Type of service requested"
    )
    job_scope: str = Field(
       ...,
        description="Scope or description of the requested job"
    )
    preferred_schedule: Optional[str] = Field(
        default=None,
        description="Requested timing or scheduling preference"
    )
    requested_extras: List[str] = Field(
        default_factory=list,
        description="Requested extras, add-ons, or special requirements"
    )
    urgency: Optional[str] = Field(
        default=None,
        description="Urgency level of the inquiry"
    )
    customer_email: Optional[str] = Field(
        default=None,
        description="Customer email if present"
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Missing details needed for later steps"
    )
    service_match_status: str = Field(
        ...,
        description='Service match result: "full_match", "partial_match", or "no_match"'
    )
    matched_service: Optional[str] = Field(
        default=None,
        description="Best matched service from the catalogue, if any"
    )
    match_confidence: Optional[str] = Field(
        default=None,
        description='Confidence level of the service match: "high", "medium", or "low"'
    )
    unmatched_elements: List[str] = Field(
        default_factory=list,
        description="Parts of the request that do not clearly match the service catalogue"
    )
    clarification_needed: bool = Field(
        default=False,
        description="Whether clarification is needed before continuing"
    )


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


class QuoteReviewPackage(BaseModel):
    customer_email: Optional[str] = None
    service_summary: str
    quoted_price: float
    recommendation_status: str
    draft_response: str
    approval_status: str = "pending"
    edited_response: Optional[str] = None
    service_match_status: str
    matched_service: Optional[str] = None
    clarification_needed: bool = False