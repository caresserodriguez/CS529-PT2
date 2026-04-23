import os
from typing import Dict, Type

import sendgrid
from sendgrid.helpers.mail import Content, Email, Mail, To
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from serviceflow_ai.guardrails import validate_email_input

# Sender address — override with SERVICEFLOW_FROM_EMAIL env var if needed
FROM_EMAIL = os.environ.get("SERVICEFLOW_FROM_EMAIL", "jmetz@miu.edu")


# ─── Core SendGrid dispatcher ─────────────────────────────────────────────────

def dispatch_email(recipient_email: str, subject: str, html_body: str) -> Dict[str, str]:
    """Send an email via SendGrid. Returns a status dict."""
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        return {"status": "error", "message": "SENDGRID_API_KEY environment variable is not set"}

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        mail = Mail(
            Email(FROM_EMAIL),
            To(recipient_email),
            subject,
            Content("text/html", html_body),
        ).get()
        response = sg.client.mail.send.post(request_body=mail)

        if response.status_code in (200, 202):
            return {"status": "success", "message": f"Email sent to {recipient_email}"}
        return {
            "status": "error",
            "message": f"SendGrid returned status {response.status_code}",
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ─── HTML template builder ────────────────────────────────────────────────────

def build_quote_email_html(body_text: str) -> str:
    """Wraps a plain-text quote draft in a Metro Service Solutions branded HTML email."""
    paragraphs = body_text.strip().split("\n\n")
    html_body = "".join(
        f'<p style="margin:0 0 14px 0;font-size:15px;line-height:1.7;color:#374151;">'
        f'{para.replace(chr(10), "<br>")}</p>'
        for para in paragraphs
        if para.strip()
    )

    return f"""
<html>
  <body style="margin:0;padding:0;background:#EEF2F7;font-family:'Segoe UI',Arial,sans-serif;">
    <div style="max-width:620px;margin:30px auto;background:#ffffff;border-radius:16px;
                overflow:hidden;border:1px solid #dde3ec;box-shadow:0 4px 20px rgba(0,0,0,0.07);">

      <div style="background:linear-gradient(135deg,#0f1f3d 0%,#1a3a6e 100%);
                  padding:28px;text-align:center;">
        <h1 style="margin:0;font-size:22px;font-weight:800;color:#ffffff;letter-spacing:0.02em;">
          &#9881;&#65039; ServiceFlow AI
        </h1>
        <p style="margin:6px 0 0 0;color:#94b4d9;font-size:12px;
                  letter-spacing:0.15em;text-transform:uppercase;">
          Metro Service Solutions &mdash; Service Quote
        </p>
      </div>

      <div style="padding:32px 36px;">
        {html_body}
      </div>

      <div style="background:#f0f4f8;padding:16px;text-align:center;
                  font-size:12px;color:#94a3b8;border-top:1px solid #e2e8f0;">
        Metro Service Solutions &nbsp;&middot;&nbsp; Powered by ServiceFlow AI
      </div>
    </div>
  </body>
</html>"""


# ─── CrewAI tool ──────────────────────────────────────────────────────────────

class SendEmailInput(BaseModel):
    recipient_email: str = Field(..., description="Customer email address to send the quote to")
    subject: str = Field(..., description="Email subject line for the quote")
    body_text: str = Field(..., description="Plain-text email body (the approved draft)")


class SendQuoteEmailTool(BaseTool):
    name: str = "send_quote_email"
    description: str = (
        "Send an approved service quote email to a customer via SendGrid. "
        "Provide the recipient email address, a subject line, and the plain-text "
        "body of the approved draft. The tool wraps it in a branded HTML template "
        "before sending. Returns a confirmation or an error message."
    )
    args_schema: Type[BaseModel] = SendEmailInput

    def _run(self, recipient_email: str, subject: str, body_text: str) -> str:
        try:
            clean_email = validate_email_input(recipient_email)
        except ValueError as exc:
            return f"Email validation failed: {exc}"

        html_body = build_quote_email_html(body_text)
        result = dispatch_email(clean_email, subject, html_body)

        if result["status"] == "success":
            return f"Email successfully sent to {clean_email}."
        return f"Email delivery failed: {result['message']}"
