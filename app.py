"""
ServiceFlow AI — Gradio front-end
Run:  python app.py
"""

import gradio as gr
import pdfplumber
import docx
from dotenv import load_dotenv
load_dotenv()

from serviceflow_ai.crew import ServiceflowAi
from serviceflow_ai.document_processor import process_business_document, DOCUMENT_TYPES

# ─── Styling ──────────────────────────────────────────────────────────────────

CSS = """
/* ── Force light mode everywhere ── */
body, .gradio-container, .main, .wrap, .panel, .block,
[data-testid], .form, .gap, .padded, .compact {
    background-color: #f4f6f9 !important;
    color: #1e2d45 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}

/* ── Header ── */
#sf-header { background: linear-gradient(135deg, #0f1f3d 0%, #1a3a6e 100%) !important;
             padding: 24px 32px; border-radius: 12px; margin-bottom: 20px; }
#sf-header h1 { color: #ffffff !important; font-size: 1.75rem; font-weight: 700; margin: 0 0 4px 0; }
#sf-header p  { color: #94b4d9 !important; font-size: 0.9rem; margin: 0; }

/* ── Panels ── */
#form-panel, #results-panel {
    text-color:#000; background: #ffffff !important; border-radius: 12px !important;
    padding: 24px !important; box-shadow: 0 1px 6px rgba(0,0,0,0.07) !important; }

/* ── All labels ── */
label, .label-wrap span { font-weight: 600 !important; color: #1e2d45 !important; }

/* ── Inputs and textareas ── */
input, textarea, .input-wrap { background: #ffffff !important; color: #1e2d45 !important;
    border-color: #d4dde8 !important; border-radius: 8px !important; }
input:focus, textarea:focus { border-color: #1a3a6e !important; box-shadow: 0 0 0 2px rgba(26,58,110,0.12) !important; }

/* ── Submit button ── */
#submit-btn { background: #1a3a6e !important; color: #ffffff !important; font-weight: 700 !important;
              border-radius: 8px !important; font-size: 1rem !important; border: none !important; }
#submit-btn:hover { background: #0f1f3d !important; }

/* ── Tabs ── */
.tab-nav button,
button[role="tab"] { font-weight: 600 !important; color: #000000 !important; background: transparent !important;
                     padding-top: 10px !important; padding-bottom: 10px !important; }
.tab-nav button.selected,
button[role="tab"][aria-selected="true"] { background: #1a3a6e !important; color: #ffffff !important;
                                           border-radius: 6px 6px 0 0 !important; border-bottom: none !important;
                                           padding-top: 10px !important; padding-bottom: 10px !important; }

/* ── Markdown tables ── */
.prose table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.prose th { background: #f0f4f8 !important; color: #1e2d45 !important; padding: 8px 12px; font-weight: 600; }
.prose td { padding: 8px 12px; border-bottom: 1px solid #e8ecf0; color: #374151; }

/* ── Draft email box ── */
#draft-box textarea { font-family: 'Georgia', serif !important; font-size: 0.92rem !important;
                      line-height: 1.65 !important; background: #fafcff !important;
                      border: 1px solid #d0dce8 !important; }

/* ── Divider ── */
.or-divider { display:flex; align-items:center; gap:10px; margin:8px 0;
              color:#94a3b8; font-size:0.78rem; font-weight:600; letter-spacing:0.8px; text-transform:uppercase; }
.or-divider::before, .or-divider::after { content:''; flex:1; height:1px; background:#e2e8f0; }

/* ── Upload box — compact & styled ── */
#upload-box { margin-top: 0 !important; }
#upload-box > .block { padding: 0 !important; }
/* outer container */
#upload-box .upload-container,
#upload-box [data-testid="upload-container"] {
    min-height: 88px !important; max-height: 88px !important;
    border: 2px dashed #c7d8ee !important; border-radius: 10px !important;
    background: #f8fafd !important; transition: all 0.2s; }
#upload-box .upload-container:hover,
#upload-box [data-testid="upload-container"]:hover {
    border-color: #1a3a6e !important; background: #eef4ff !important; }
/* shrink the icon */
#upload-box svg { width: 20px !important; height: 20px !important; color: #1a3a6e !important; }
/* caption text */
#upload-box .upload-container p,
#upload-box [data-testid="upload-container"] p {
    font-size: 0.82rem !important; color: #64748b !important; margin: 2px 0 !important; }

/* ── Loading spinner ── */
@keyframes sf-spin { to { transform: rotate(360deg); } }
.sf-spinner { width:26px; height:26px; border:3px solid rgba(148,180,217,0.25);
              border-top-color:#94b4d9; border-radius:50%;
              animation:sf-spin 0.75s linear infinite; flex-shrink:0; }

/* ── HITL review panel ── */
#hitl-panel { border-left: 4px solid #f59e0b !important; border-radius: 0 12px 12px 0 !important;
              background: #fffbeb !important; margin: 12px 0 !important; padding: 4px 0 !important; }
#hitl-draft-box textarea { font-family: 'Georgia', serif !important; font-size: 0.92rem !important;
                           line-height: 1.65 !important; }
#approve-btn { background: #059669 !important; border-color: #059669 !important; color: #fff !important;
               font-weight: 700 !important; }
#approve-btn:hover { background: #047857 !important; }
#reject-btn  { background: #dc2626 !important; border-color: #dc2626 !important; color: #fff !important;
               font-weight: 700 !important; }
#reject-btn:hover  { background: #b91c1c !important; }
"""

HEADER_HTML = """
<div id="sf-header">
  <h1>⚙️ Buckets & Bucks AI</h1>
  <p>Buckets & Bucks — AI-Powered Quote Generation Engine &nbsp;·&nbsp; 7-Agent Sequential Crew</p>
</div>
"""

EMPTY_SUMMARY_HTML = """
<div style="background:#f4f6f9;border-radius:10px;padding:20px;text-align:center;color:#8a9bb0;font-size:0.9rem; border: solid #000;">
  Submit an inquiry to see the quote summary here.
</div>
"""

LOADING_SUMMARY_HTML = """
<div style="background:linear-gradient(135deg,#0f1f3d,#1a3a6e);border-radius:10px;
            padding:20px 24px;display:flex;align-items:center;gap:16px;">
  <div class="sf-spinner"></div>
  <div>
    <p style="color:#ffffff;font-size:1rem;font-weight:600;margin:0;">Generating Quote&hellip;</p>
    <p style="color:#94b4d9;font-size:0.8rem;margin:4px 0 0 0;">
      Running 6 specialist agents &mdash; please wait 30&ndash;90 seconds
    </p>
  </div>
</div>
"""

SENDING_SUMMARY_HTML = """
<div style="background:linear-gradient(135deg,#064e3b,#065f46);border-radius:10px;
            padding:20px 24px;display:flex;align-items:center;gap:16px;">
  <div class="sf-spinner" style="border-top-color:#6ee7b7;"></div>
  <div>
    <p style="color:#ffffff;font-size:1rem;font-weight:600;margin:0;">Sending Email&hellip;</p>
    <p style="color:#6ee7b7;font-size:0.8rem;margin:4px 0 0 0;">
      Dispatching the approved quote to the customer
    </p>
  </div>
</div>
"""

SUCCESS_SUMMARY_HTML = """
<div style="background:linear-gradient(135deg,#064e3b,#065f46);border-radius:10px;
            padding:20px 24px;display:flex;align-items:center;gap:16px;">
  <div style="font-size:2rem;line-height:1;">&#10003;</div>
  <div>
    <p style="color:#ffffff;font-size:1.1rem;font-weight:700;margin:0;">Successful</p>
    <p style="color:#6ee7b7;font-size:0.88rem;margin:4px 0 0 0;">
      Quote Generated and Email Sent Successfully
    </p>
  </div>
</div>
"""


# ─── Output formatters ────────────────────────────────────────────────────────

def _safe(tasks: list, index: int):
    """Returns the pydantic output of a task, or None on any failure."""
    try:
        out = tasks[index]
        return out.pydantic if out else None
    except (IndexError, AttributeError):
        return None


def _raw(tasks: list, index: int) -> str:
    try:
        return tasks[index].raw or ""
    except (IndexError, AttributeError):
        return ""


def _currency(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _list_items(items: list) -> str:
    if not items:
        return "None"
    return "\n".join(f"- {i}" for i in items)


def fmt_inquiry(o) -> str:
    if o is None:
        return "_Analysis not available._"
    return f"""
| Field | Detail |
|---|---|
| **Service Type** | {o.service_type} |
| **Job Scope** | {o.job_scope} |
| **Preferred Schedule** | {o.preferred_schedule} |
| **Urgency** | {o.urgency} |
| **Customer Email** | {o.customer_email or "—"} |

**Requested Extras**
{_list_items(o.requested_extras)}

**Missing Information**
{_list_items(o.missing_information)}
"""


def fmt_readiness(o) -> str:
    if o is None:
        return "_Readiness check not available._"
    return f"""
| Area | Status |
|---|---|
| **Staffing** | {o.staffing_status} |
| **Resources & Materials** | {o.resource_material_status} |
| **Tools & Equipment** | {o.tools_equipment_status} |
| **Scheduling Feasibility** | {o.scheduling_feasibility} |
| **Overall Readiness** | **{o.overall_readiness}** |

**Readiness Risks**
{_list_items(o.readiness_risks)}

**Cost Impact Notes**
{_list_items(o.cost_impact_notes)}
"""


def fmt_costing(o) -> str:
    if o is None:
        return "_Costing not available._"
    return f"""
| Cost Component | Amount |
|---|---|
| **Labour** | {_currency(o.labor_cost)} |
| **Materials & Resources** | {_currency(o.materials_resources_cost)} |
| **Equipment & Operations** | {_currency(o.equipment_operational_cost)} |
| **Additional Burden** | {_currency(o.additional_burden_cost)} |
| **Total Internal Cost** | **{_currency(o.total_internal_cost)}** |

**Main Cost Drivers**
{_list_items(o.main_cost_drivers)}
"""


def fmt_pricing(o) -> str:
    if o is None:
        return "_Pricing not available._"
    return f"""
| Pricing Component | Amount |
|---|---|
| **Base Customer Price** | {_currency(o.base_customer_price)} |
| **Extras Total** | {_currency(o.extras_price_total)} |
| **Business Adjustments** | {_currency(o.business_adjustments)} |
| **Final Quoted Price** | **{_currency(o.final_quoted_price)}** |

**Pricing Rationale**

{o.pricing_rationale}
"""


def fmt_profit(o) -> str:
    if o is None:
        return "_Profit analysis not available._"
    return f"""
| Field | Detail |
|---|---|
| **Recommendation** | **{o.recommendation_status}** |
| **Profitability Assessment** | {o.profitability_assessment} |
| **Suggested Action** | {o.suggested_action} |

**Margin Commentary**

{o.estimated_margin_commentary}

**Rationale**

{o.rationale}
"""


def fmt_delivery(o) -> str:
    if o is None:
        return "_Delivery status not available._"
    icon = "✅" if o.sent else "🚫"
    return f"""
| Field | Detail |
|---|---|
| **Status** | {icon} {o.status_message} |
| **Recipient** | {o.recipient or "—"} |
| **Sent** | {"Yes" if o.sent else "No — awaiting approval"} |
"""


def build_summary_card(pricing_o, profit_o, readiness_o) -> str:
    """Builds the top-level KPI card shown above the tabs."""
    price   = _currency(pricing_o.final_quoted_price) if pricing_o else "—"
    rec     = profit_o.recommendation_status if profit_o else "—"
    margin  = profit_o.estimated_margin_commentary if profit_o else "—"
    ready   = readiness_o.overall_readiness if readiness_o else "—"

    rec_upper = rec.upper() if rec else ""
    if "ACCEPT" in rec_upper:
        badge_style = "background:#d1fae5;color:#065f46;border:1px solid #6ee7b7;"
    elif "DECLINE" in rec_upper or "NOT" in rec_upper:
        badge_style = "background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;"
    else:
        badge_style = "background:#fef3c7;color:#92400e;border:1px solid #fcd34d;"

    return f"""
<div id="summary-card" style="background:linear-gradient(135deg,#0f1f3d,#1a3a6e);border-radius:10px;padding:20px 24px;">
  <p style="color:#94b4d9;font-size:0.78rem;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px 0;">Quote Summary</p>
  <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start;">

    <div style="flex:1;min-width:120px;">
      <p style="color:#94b4d9;font-size:0.75rem;margin:0 0 4px 0;">FINAL QUOTE</p>
      <p style="color:#ffffff;font-size:1.9rem;font-weight:700;margin:0;">{price}</p>
    </div>

    <div style="flex:1;min-width:120px;">
      <p style="color:#94b4d9;font-size:0.75rem;margin:0 0 6px 0;">RECOMMENDATION</p>
      <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.85rem;{badge_style}">{rec}</span>
    </div>

    <div style="flex:1;min-width:120px;">
      <p style="color:#94b4d9;font-size:0.75rem;margin:0 0 4px 0;">READINESS</p>
      <p style="color:#e2e8f0;font-size:0.95rem;font-weight:600;margin:0;">{ready}</p>
    </div>

    <div style="flex:2;min-width:180px;">
      <p style="color:#94b4d9;font-size:0.75rem;margin:0 0 4px 0;">MARGIN NOTE</p>
      <p style="color:#cbd5e1;font-size:0.85rem;margin:0;line-height:1.4;">{margin}</p>
    </div>

  </div>
</div>
"""


# ─── File upload parser ───────────────────────────────────────────────────────

def parse_uploaded_file(file):
    """Extracts plain text from a .txt, .pdf, or .docx upload and streams status to the inquiry box."""
    if file is None:
        yield ""
        return

    yield "Parsing file & extracting text…"

    path = file.name if hasattr(file, "name") else str(file)
    ext = path.rsplit(".", 1)[-1].lower()
    try:
        if ext == "txt":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                yield f.read().strip()
                return
        if ext == "pdf":
            pages = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text.strip())
            yield "\n\n".join(pages)
            return
        if ext in ("docx", "doc"):
            doc = docx.Document(path)
            yield "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return
    except Exception as exc:
        yield f"[Could not read file: {exc}]"
        return
    yield ""


# ─── Crew runner — Phase 1: analysis + draft generation ──────────────────────

def run_phase1(inquiry: str, email: str):
    if not inquiry.strip():
        raise gr.Error("Customer inquiry cannot be empty.")
    if not email.strip():
        raise gr.Error("Customer email cannot be empty.")

    # ── Immediate loading feedback (streamed to UI before crew starts) ────────
    yield (
        gr.update(),                    # inquiry_output   — leave as-is
        gr.update(),                    # readiness_output
        gr.update(),                    # costing_output
        gr.update(),                    # pricing_output
        gr.update(),                    # profit_output
        "Generating quote, please wait…",  # draft_output
        gr.update(),                    # hitl_draft
        LOADING_SUMMARY_HTML,           # summary_card — spinner card
        gr.update(visible=False),       # hitl_section
        gr.update(value=""),            # delivery_output — clear previous
        None,                           # phase1_state
        gr.update(visible=False),       # delivery_section — keep hidden
    )

    inputs = {
        "customer_inquiry": inquiry.strip(),
        "customer_email": email.strip(),
    }

    try:
        result = ServiceflowAi().phase1_crew().kickoff(inputs=inputs)
    except Exception as exc:
        raise gr.Error(f"Crew execution failed: {exc}")

    t = result.tasks_output

    pricing_o   = _safe(t, 3)
    profit_o    = _safe(t, 4)
    readiness_o = _safe(t, 1)
    draft_text  = _raw(t, 5) or ""

    state = {"customer_email": email.strip(), "customer_inquiry": inquiry.strip()}

    # ── Final results (streamed to UI after crew finishes) ────────────────────
    yield (
        fmt_inquiry(_safe(t, 0)),
        fmt_readiness(readiness_o),
        fmt_costing(_safe(t, 2)),
        fmt_pricing(pricing_o),
        fmt_profit(profit_o),
        draft_text,
        draft_text,
        build_summary_card(pricing_o, profit_o, readiness_o),
        gr.update(visible=True),
        gr.update(value=""),
        state,
        gr.update(visible=False),       # delivery_section — hidden until decision
    )


# ─── HITL handlers — approve and reject ──────────────────────────────────────

def approve_quote(draft_text: str, state: dict):
    if not state:
        raise gr.Error("No active quote session — please generate a quote first.")

    # ── Immediate sending feedback ────────────────────────────────────────────
    yield (
        "_Sending email to customer…_",
        gr.update(visible=False),
        SENDING_SUMMARY_HTML,
        None,                           # reset state so HITL cannot be resubmitted
        gr.update(visible=False),       # delivery_section — still hidden while sending
    )

    inputs = {
        "human_approved": "true",
        "customer_email": state["customer_email"],
        "draft_email_content": draft_text.strip(),
    }

    try:
        result = ServiceflowAi().phase2_crew().kickoff(inputs=inputs)
    except Exception as exc:
        raise gr.Error(f"Email delivery failed: {exc}")

    t = result.tasks_output
    delivery = _safe(t, 0)

    # ── Final delivery result ─────────────────────────────────────────────────
    yield (
        fmt_delivery(delivery),
        gr.update(visible=False),
        SUCCESS_SUMMARY_HTML if (delivery and delivery.sent) else gr.update(),
        None,
        gr.update(visible=True),        # delivery_section — reveal after result
    )


def reject_quote(_: str, state: dict):
    if not state:
        raise gr.Error("No active quote session — please generate a quote first.")

    gr.Info("Quote rejected. No email was sent.")

    yield (
        "_Quote rejected by operator. No email was sent._",
        gr.update(visible=False),
        gr.update(),                    # summary_card unchanged
        None,                           # reset state
        gr.update(visible=True),        # delivery_section — reveal after rejection
    )


# ─── UI layout ────────────────────────────────────────────────────────────────

PLACEHOLDER_INQUIRY = (
    "e.g. Hi, I need a quote for a deep clean on my 3-bedroom house next Tuesday "
    "or Wednesday. We haven't had a professional clean in about three months and "
    "the oven definitely needs attention. Happy to add a carpet steam clean if the "
    "price is reasonable. Let me know — thanks, Sarah."
)

with gr.Blocks(title="ServiceFlow AI — Quote Generator", theme=gr.themes.Soft()) as demo:

    gr.HTML(HEADER_HTML)

    with gr.Tabs():

        # ── Tab 1: Quote Generator ────────────────────────────────────────────
        with gr.Tab("Quote Generator"):
            with gr.Row(equal_height=False):

        # ── Left: input form ──────────────────────────────────────────────────
        with gr.Column(scale=2, elem_id="form-panel"):
            gr.Markdown("<h3 style='text-align:center; padding-top: 10px; padding-bottom: 10px; color:#000;'>New Service Inquiry</h3>")

            inquiry_input = gr.Textbox(
                label="Customer Inquiry",
                placeholder=PLACEHOLDER_INQUIRY,
                lines=8,
                max_lines=16,
            )
            gr.HTML('<div class="or-divider">or upload a document</div>')
            file_upload = gr.File(
                label="Attach File  (.txt · .pdf · .docx)",
                file_types=[".txt", ".pdf", ".docx", ".doc"],
                file_count="single",
                elem_id="upload-box",
            )
            email_input = gr.Textbox(
                label="Customer Email",
                placeholder="customer@example.com",
                lines=1,
            )
            submit_btn = gr.Button(
                "⚡  Generate Quote",
                variant="primary",
                elem_id="submit-btn",
            )
            gr.Markdown(
                "<br><small style='color:#8a9bb0;'>Runs 6 analysis agents then pauses "
                "for your review before sending. Allow 30–90 seconds.</small>"
            )

        # ── Right: results ────────────────────────────────────────────────────
        with gr.Column(scale=3, elem_id="results-panel"):
            gr.Markdown("<h3 style='color:#000000; padding-top:10px; padding-bottom:10px; text-align:center;'>Here's What I Think</h3>")
            summary_card = gr.HTML(value=EMPTY_SUMMARY_HTML)

            # ── HITL review panel (hidden until Phase 1 completes) ────────────
            phase1_state = gr.State(None)
            with gr.Group(elem_id="hitl-panel", visible=False) as hitl_section:
                gr.HTML("""
                <div style="padding:14px 18px 6px 18px;">
                  <strong style="color:#92400e;font-size:1.05rem;">⏸ Human Review Required</strong>
                  <p style="color:#78350f;margin:6px 0 0 0;font-size:0.88rem;">
                    Review the draft quote email below. Edit it if needed, then
                    <strong>Approve &amp; Send</strong> to dispatch to the customer,
                    or <strong>Reject</strong> to cancel delivery entirely.
                  </p>
                </div>
                """)
                hitl_draft = gr.Textbox(
                    label="Draft Quote Email (editable)",
                    lines=12,
                    interactive=True,
                    elem_id="hitl-draft-box",
                )
                with gr.Row():
                    approve_btn = gr.Button(
                        "✅  Approve & Send", elem_id="approve-btn", scale=2
                    )
                    reject_btn = gr.Button(
                        "❌  Reject", elem_id="reject-btn", scale=1
                    )

            with gr.Tabs():

                with gr.Tab("📄 Quote & Recommendation"):
                    gr.Markdown("<h3 style='color: #000; padding-top: 10px; padding-bottom:10px; text-align:center;'>Draft Quote Email</h3>")
                    draft_output = gr.Textbox(
                        label=None,
                        show_label=False,
                        lines=14,
                        interactive=False,
                        elem_id="draft-box",
                    )
                    with gr.Column(visible=False) as delivery_section:
                        gr.Markdown("<h3 style='color: #000; padding-top: 10px; padding-bottom:10px; text-align:center;'>Email Delivery Status</h3>")
                        delivery_output = gr.Markdown()

                        with gr.Tab("🔍 Full Agent Analysis"):
                            with gr.Accordion("1 · Inquiry Analysis", open=True):
                                inquiry_output = gr.Markdown()
                            with gr.Accordion("2 · Operational Readiness", open=False):
                                readiness_output = gr.Markdown()
                            with gr.Accordion("3 · Internal Costing", open=False):
                                costing_output = gr.Markdown()
                            with gr.Accordion("4 · Customer Pricing", open=False):
                                pricing_output = gr.Markdown()
                            with gr.Accordion("5 · Profit Optimisation", open=False):
                                profit_output = gr.Markdown()

    hitl_draft.change(
        fn=lambda text: text,
        inputs=[hitl_draft],
        outputs=[draft_output],
    )

    file_upload.change(
        fn=parse_uploaded_file,
        inputs=[file_upload],
        outputs=[inquiry_input],
    )

    # Phase 1: analysis + draft — reveals HITL panel on completion
    submit_btn.click(
        fn=run_phase1,
        inputs=[inquiry_input, email_input],
        outputs=[
            inquiry_output,
            readiness_output,
            costing_output,
            pricing_output,
            profit_output,
            draft_output,
            hitl_draft,
            summary_card,
            hitl_section,
            delivery_output,
            phase1_state,
            delivery_section,
        ],
    )

    # HITL: approve — shows "Sending…" immediately, then dispatches via crew
    approve_btn.click(
        fn=approve_quote,
        inputs=[hitl_draft, phase1_state],
        outputs=[delivery_output, hitl_section, summary_card, phase1_state, delivery_section],
    )

    # HITL: reject — shows rejection message immediately, no crew call needed
    reject_btn.click(
        fn=reject_quote,
        inputs=[hitl_draft, phase1_state],
        outputs=[delivery_output, hitl_section, summary_card, phase1_state, delivery_section],
    )


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",   # required for AWS — binds to all interfaces
        server_port=7860,
        show_error=True,
        css=CSS,
    )
