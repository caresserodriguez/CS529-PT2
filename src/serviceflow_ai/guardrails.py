import re
from pathlib import Path

from pypdf import PdfReader
from dataclasses import dataclass, field
from typing import List


MAX_OUTPUT_CHARS = 8000


def validate_email_input(email: str) -> str:
    """
    Validates and normalises an email input from an agent.
    Returns the cleaned lowercase email, or raises ValueError if invalid.

    Why: customer_email is agent-supplied text. A bad or injected value (e.g.
    '../../secrets' or a multi-line string) should be rejected before it reaches
    the data lookup or appears in any downstream output.
    """
    email = email.strip().lower()
    if len(email) > 254:
        raise ValueError("Email input exceeds the maximum allowed length (254 chars).")
    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError(f"Invalid email format received: '{email}'.")
    return email


def validate_text_input(text: str, field_name: str = "input", max_len: int = 100) -> str:
    """
    Validates a short free-text input (e.g. a service name) from an agent.
    Returns the stripped text, or raises ValueError if it fails checks.

    Why: agent-supplied strings can carry prompt-injection payloads or
    abnormally large strings that inflate context usage. Length cap and
    character allowlist keep tool inputs within expected bounds.
    """
    text = text.strip()
    if len(text) > max_len:
        raise ValueError(
            f"'{field_name}' exceeds the maximum allowed length of {max_len} characters."
        )
    if re.search(r'[<>\{\}|\\^`\n\r]', text):
        raise ValueError(
            f"'{field_name}' contains disallowed characters."
        )
    return text


def validate_filename(filename: str) -> None:
    """
    Ensures a filename is a plain basename with no path traversal components.
    Raises ValueError if the filename contains directory separators or dotfile prefixes.

    Why: knowledge file names are currently hardcoded, but this guardrail makes
    _load_json_file safe against any future dynamic filename usage that could
    allow an agent to escape the knowledge directory (e.g. '../../.env').
    """
    p = Path(filename)
    if p.parent != Path(".") or not p.name or p.name.startswith("."):
        raise ValueError(
            f"Invalid knowledge filename: '{filename}'. "
            "Must be a plain filename with no path components."
        )


def cap_tool_output(output: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """
    Truncates tool output to prevent large knowledge files from flooding agent context.

    Why: knowledge files may grow over time. Uncapped JSON dumps can consume a
    disproportionate share of the agent's context window, degrading reasoning
    quality for the rest of the crew.
    """
    if len(output) > max_chars:
        return output[:max_chars] + "\n... [output truncated by tool guardrail]"
    return output


def validate_service_match_status(service_match_status: str) -> tuple[bool, str]:
    """
    Validate that the inquiry analysis returned a valid service match status.
    """
    allowed_statuses = {"full_match", "partial_match", "no_match"}

    if service_match_status not in allowed_statuses:
        return False, f"Invalid service match status: {service_match_status}"

    return True, "Service match status is valid."


def should_block_automatic_quote(
    service_match_status: str,
    clarification_needed: bool,
) -> tuple[bool, str]:
    """
    Decide whether the system should block the automatic quote pipeline.
    """
    if service_match_status == "no_match":
        return True, "Automatic quote blocked: request does not match the service catalogue."

    if service_match_status == "partial_match":
        return True, "Automatic quote blocked: request only partially matches and needs clarification or review."

    if clarification_needed:
        return True, "Automatic quote blocked: clarification is required before quoting."

    return False, "Automatic quote is allowed."


def validate_review_decision(
    approved: bool,
    edited_response: str | None = None,
) -> tuple[bool, str]:
    """
    Validate the human review decision before delivery processing.
    """
    if edited_response is not None and not edited_response.strip():
        return False, "Review decision blocked: edited response was provided but is empty."

    return True, "Review decision is valid."

def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)

    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

MAX_CHARS = 50000

SUSPICIOUS_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "system prompt",
    "developer message",
    "you are chatgpt",
    "reveal the system prompt",
    "do not tell the user",
    "tool call",
    "browse the web",
    "override instructions",
    "send secrets",
    "api key",
    "password",
]


@dataclass
class GuardrailResult:
    cleaned_text: str
    was_truncated: bool
    suspicious_patterns: List[str] = field(default_factory=list)
    risk_score: int = 0
    flagged: bool = False
    reasons: List[str] = field(default_factory=list)



def apply_text_guardrails(raw_text: str, max_chars: int = MAX_CHARS) -> GuardrailResult:
    
    

    reasons = []

    text = raw_text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if not text:
        reasons.append("the text is empty after cleaning.")

    was_truncated = False
    if len(text) > max_chars:
        text = text[:max_chars].strip()
        was_truncated = True
        reasons.append(f"the text was truncated to {max_chars} characters.")

    lower_text = text.lower()
    matched_patterns = [pattern for pattern in SUSPICIOUS_PATTERNS if pattern in lower_text]

    risk_score = 0

    if matched_patterns:
        risk_score += len(matched_patterns)
        reasons.append("suspicious patterns associated with possible prompt injection were detected.")

    

    flagged = risk_score >= 2

    return GuardrailResult(
        cleaned_text=text,
        was_truncated=was_truncated,
        suspicious_patterns=matched_patterns,
        risk_score=risk_score,
        flagged=flagged,
        reasons=reasons,
    )
