import re
from pathlib import Path


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
