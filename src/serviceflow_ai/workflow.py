from serviceflow_ai.models import InquiryAnalysisOutput, QuoteReviewPackage
from serviceflow_ai.guardrails import (
    validate_service_match_status,
    should_block_automatic_quote,
    validate_review_decision,
)

def route_after_inquiry(inquiry_result: InquiryAnalysisOutput) -> str:
    """
    Decide what workflow path to take after inquiry analysis.

    Returns one of:
    - normal_quote_flow
    - clarification_review_flow
    - out_of_scope_flow
    - manual_review_flow
    """
    is_valid, _ = validate_service_match_status(inquiry_result.service_match_status)

    if not is_valid:
        return "manual_review_flow"

    status = inquiry_result.service_match_status

    if status == "full_match":
        return "normal_quote_flow"

    if status == "partial_match":
        return "clarification_review_flow"

    if status == "no_match":
        return "out_of_scope_flow"

    return "manual_review_flow"

def determine_quote_path(inquiry_result: InquiryAnalysisOutput) -> str:
    """
    Decide the safe workflow path after inquiry analysis, using guardrails.
    """
    is_valid, _ = validate_service_match_status(inquiry_result.service_match_status)

    if not is_valid:
        return "manual_review_flow"

    should_block, _ = should_block_automatic_quote(
        inquiry_result.service_match_status,
        inquiry_result.clarification_needed,
    )

    if should_block:
        if inquiry_result.service_match_status == "no_match":
            return "out_of_scope_flow"
        return "clarification_review_flow"

    return "normal_quote_flow"

def build_review_package(
    inquiry_result: InquiryAnalysisOutput,
    service_summary: str,
    quoted_price: float,
    recommendation_status: str,
    draft_response: str,
) -> QuoteReviewPackage:
    """
    Build the package that will be shown to the human reviewer before approval.
    """
    return QuoteReviewPackage(
        customer_email=inquiry_result.customer_email,
        service_summary=service_summary,
        quoted_price=quoted_price,
        recommendation_status=recommendation_status,
        draft_response=draft_response,
        service_match_status=inquiry_result.service_match_status,
        matched_service=inquiry_result.matched_service,
        clarification_needed=inquiry_result.clarification_needed,
    )


def process_quote_review(
    review_package: QuoteReviewPackage,
    approved: bool,
    edited_response: str | None = None,
) -> dict:
    """
    Process the human review decision.

    If approved, return the final response that is ready for delivery.
    If rejected, stop the flow.
    If edited_response is provided, use that instead of the original draft.
    """
    is_valid, message = validate_review_decision(
        approved=approved,
        edited_response=edited_response,
    )

    if not is_valid:
        return {
            "status": "blocked",
            "message": message,
            "approval_status": review_package.approval_status,
        }

    if not approved:
        review_package.approval_status = "rejected"
        return {
            "status": "not_sent",
            "message": "Quote was rejected during human review.",
            "approval_status": review_package.approval_status,
        }

    review_package.approval_status = "approved"

    final_response = edited_response.strip() if edited_response else review_package.draft_response
    review_package.edited_response = edited_response

    return {
        "status": "ready_for_delivery",
        "approval_status": review_package.approval_status,
        "customer_email": review_package.customer_email,
        "final_response": final_response,
        "review_package": review_package.model_dump(),
    }

def build_route_response(
    inquiry_result: InquiryAnalysisOutput,
    review_package: QuoteReviewPackage,
) -> dict:
    """
    Build the backend response shown to the human reviewer based on the safe route.
    """
    route = determine_quote_path(inquiry_result)

    if route == "normal_quote_flow":
        return {
            "status": "ready_for_review",
            "route": route,
            "message": "Quote draft is ready for human review before delivery.",
            "review_package": review_package.model_dump(),
        }

    if route == "clarification_review_flow":
        return {
            "status": "needs_clarification",
            "route": route,
            "message": "This request only partially matches a known service or needs clarification before automatic quoting.",
            "review_package": review_package.model_dump(),
        }

    if route == "out_of_scope_flow":
        return {
            "status": "out_of_scope",
            "route": route,
            "message": "This request does not match the business service catalogue and should not be automatically quoted.",
            "review_package": review_package.model_dump(),
        }

    return {
        "status": "manual_review",
        "route": route,
        "message": "Manual review is required before continuing.",
        "review_package": review_package.model_dump(),
    }


def prepare_review_stage(
    inquiry_result: InquiryAnalysisOutput,
    service_summary: str,
    quoted_price: float,
    recommendation_status: str,
    draft_response: str,
) -> dict:
    """
    Prepare the human review stage after the draft quote has been generated.
    """
    review_package = build_review_package(
        inquiry_result=inquiry_result,
        service_summary=service_summary,
        quoted_price=quoted_price,
        recommendation_status=recommendation_status,
        draft_response=draft_response,
    )

    return build_route_response(
        inquiry_result=inquiry_result,
        review_package=review_package,
    )