"""Quote Generator page — all logic, formatters, and UI."""
import re

import docx
import gradio as gr
import pdfplumber

from serviceflow_ai.crew import ServiceflowAi

# ─── HTML snippets ────────────────────────────────────────────────────────────

EMPTY_SUMMARY_HTML = """
<div style="background:#f4f6f9;border-radius:10px;padding:20px;text-align:center;
            color:#8a9bb0;font-size:0.9rem;border:solid #000;">
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

PLACEHOLDER_INQUIRY = (
    "e.g. Hi, I need a quote for a deep clean on my 3-bedroom house next Tuesday "
    "or Wednesday. We haven't had a professional clean in about three months and "
    "the oven definitely needs attention. Happy to add a carpet steam clean if the "
    "price is reasonable. Let me know — thanks, Sarah."
)


# ─── Output formatters ────────────────────────────────────────────────────────

def _safe(tasks: list, index: int):
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


# ─── Summary / carousel builders ─────────────────────────────────────────────

def _most_profitable_index(quotes: list) -> int:
    best_idx, best_profit = 0, -float("inf")
    for i, q in enumerate(quotes):
        p = q.get("pricing")
        c = q.get("costing")
        profit = (p.final_quoted_price if p else 0) - (c.total_internal_cost if c else 0)
        if profit > best_profit:
            best_profit, best_idx = profit, i
    return best_idx


def _loading_multi_html(current: int, total: int) -> str:
    return f"""
<div style="background:linear-gradient(135deg,#0f1f3d,#1a3a6e);border-radius:10px;
            padding:20px 24px;display:flex;align-items:center;gap:16px;">
  <div class="sf-spinner"></div>
  <div>
    <p style="color:#ffffff;font-size:1rem;font-weight:600;margin:0;">
      Generating Quote {current} of {total}&hellip;
    </p>
    <p style="color:#94b4d9;font-size:0.8rem;margin:4px 0 0 0;">
      Running 6 specialist agents &mdash; please wait
    </p>
  </div>
</div>"""


def _next_pending_idx(statuses: dict, current_idx: int, total: int):
    for i in list(range(current_idx + 1, total)) + list(range(0, current_idx)):
        if statuses.get(i, "pending") == "pending":
            return i
    return None


def _build_delivery_summary(quotes: list, statuses: dict) -> str:
    if not quotes:
        return ""
    rows = []
    for i, q in enumerate(quotes):
        status = statuses.get(i, "pending")
        label = q.get("label", f"Request {i + 1}")
        if status == "approved":
            rows.append(f"| **{label}** | ✅ Email sent to {q.get('customer_email', '—')} |")
        elif status == "rejected":
            rows.append(f"| **{label}** | ❌ Rejected — no email sent |")
        elif status == "failed":
            rows.append(f"| **{label}** | 🚫 Send failed — check SendGrid logs |")
        else:
            rows.append(f"| **{label}** | ⏳ Pending review |")
    return "| Quote | Status |\n|---|---|\n" + "\n".join(rows)


def build_carousel_slide(quotes: list, idx: int, best_idx: int, statuses: dict = None) -> str:
    if not quotes:
        return EMPTY_SUMMARY_HTML
    statuses = statuses or {}
    q = quotes[idx]
    total = len(quotes)
    pricing_o   = q.get("pricing")
    profit_o    = q.get("profit")
    readiness_o = q.get("readiness")

    price       = pricing_o.final_quoted_price if pricing_o else 0
    rec         = profit_o.recommendation_status if profit_o else "—"
    ready       = readiness_o.overall_readiness if readiness_o else "—"
    margin_note = profit_o.estimated_margin_commentary if profit_o else "—"

    rec_upper = (rec or "").upper()
    if "ACCEPT" in rec_upper:
        badge_style = "background:#d1fae5;color:#065f46;border:1px solid #6ee7b7;"
    elif "DECLINE" in rec_upper or "NOT" in rec_upper:
        badge_style = "background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;"
    else:
        badge_style = "background:#fef3c7;color:#92400e;border:1px solid #fcd34d;"

    profitable_badge = ""
    if total > 1 and idx == best_idx:
        profitable_badge = (
            '<span style="background:#fef9c3;color:#a16207;border:1px solid #fcd34d;'
            'border-radius:20px;padding:3px 10px;font-size:0.78rem;font-weight:700;">'
            "⭐ Most Profitable</span>"
        )

    def _dot(i):
        s = statuses.get(i, "pending")
        color = (
            "#ffffff" if i == idx
            else "#6ee7b7" if s == "approved"
            else "#fca5a5" if s == "rejected"
            else "rgba(255,255,255,0.35)"
        )
        return f'<span style="color:{color};font-size:1rem;margin:0 3px;">●</span>'

    dots = "".join(_dot(i) for i in range(total))
    slide_label = f"Quote {idx + 1} of {total}" if total > 1 else "Quote Summary"

    current_status = statuses.get(idx, "pending")
    if current_status == "approved":
        status_banner = (
            '<div style="background:rgba(110,231,183,0.15);border-radius:8px;padding:8px 12px;'
            'margin-top:12px;text-align:center;">'
            '<span style="color:#6ee7b7;font-weight:600;">✅ Approved — email sent</span></div>'
        )
    elif current_status == "rejected":
        status_banner = (
            '<div style="background:rgba(252,165,165,0.15);border-radius:8px;padding:8px 12px;'
            'margin-top:12px;text-align:center;">'
            '<span style="color:#fca5a5;font-weight:600;">❌ Rejected — not sent</span></div>'
        )
    elif current_status == "failed":
        status_banner = (
            '<div style="background:rgba(252,165,165,0.15);border-radius:8px;padding:8px 12px;'
            'margin-top:12px;text-align:center;">'
            '<span style="color:#fca5a5;font-weight:600;">🚫 Send failed</span></div>'
        )
    else:
        status_banner = ""

    return f"""
<div id="summary-card" style="background:linear-gradient(135deg,#0f1f3d,#1a3a6e);
                               border-radius:10px;padding:20px 24px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <p style="color:#94b4d9;font-size:0.78rem;text-transform:uppercase;
              letter-spacing:1px;margin:0;">{slide_label}</p>
    {profitable_badge}
  </div>
  <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start;">
    <div style="flex:1;min-width:120px;">
      <p style="color:#94b4d9;font-size:0.75rem;margin:0 0 4px 0;">FINAL QUOTE</p>
      <p style="color:#ffffff;font-size:1.9rem;font-weight:700;margin:0;">{_currency(price)}</p>
    </div>
    <div style="flex:1;min-width:120px;">
      <p style="color:#94b4d9;font-size:0.75rem;margin:0 0 6px 0;">RECOMMENDATION</p>
      <span style="display:inline-block;padding:4px 14px;border-radius:20px;
                   font-weight:700;font-size:0.85rem;{badge_style}">{rec}</span>
    </div>
    <div style="flex:1;min-width:120px;">
      <p style="color:#94b4d9;font-size:0.75rem;margin:0 0 4px 0;">READINESS</p>
      <p style="color:#e2e8f0;font-size:0.95rem;font-weight:600;margin:0;">{ready}</p>
    </div>
    <div style="flex:2;min-width:180px;">
      <p style="color:#94b4d9;font-size:0.75rem;margin:0 0 4px 0;">MARGIN NOTE</p>
      <p style="color:#cbd5e1;font-size:0.85rem;margin:0;line-height:1.4;">{margin_note}</p>
    </div>
  </div>
  {status_banner}
  {f'<div style="text-align:center;margin-top:14px;">{dots}</div>' if total > 1 else ''}
</div>
"""


# ─── File upload helpers ──────────────────────────────────────────────────────

def _extract_email_from_text(text: str) -> str:
    match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    return match.group(0).lower() if match else ""


def _extract_text_from_path(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "txt":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    if ext == "pdf":
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
        return "\n\n".join(pages)
    if ext in ("docx", "doc"):
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return ""


def parse_uploaded_file(files):
    _no_change = (gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
    if not files:
        yield "", [], *_no_change
        return

    file_list = (files if isinstance(files, list) else [files])[:3]
    count = len(file_list)
    label = "file" if count == 1 else f"{count} files"
    yield f"Parsing {label} & extracting text…", [], *_no_change

    individual_texts, emails = [], []
    for f in file_list:
        path = f.name if hasattr(f, "name") else str(f)
        try:
            text = _extract_text_from_path(path)
            individual_texts.append(text if text else "")
            emails.append(_extract_email_from_text(text) if text else "")
        except Exception as exc:
            individual_texts.append(f"[Could not read {path}: {exc}]")
            emails.append("")

    def _email_update(i):
        val = emails[i] if i < len(emails) else ""
        return gr.update(
            value=val,
            interactive=not bool(val),
            label=f"Customer Email — Request {i + 1}" if count > 1 else "Customer Email",
        )

    combined = "\n\n---\n\n".join(t for t in individual_texts if t)
    yield (
        combined,
        individual_texts,
        _email_update(0),
        _email_update(1),
        gr.update(visible=count >= 2),
        _email_update(2),
        gr.update(visible=count >= 3),
    )


# ─── Signature injector ───────────────────────────────────────────────────────

def _inject_signature(draft: str, profile: dict) -> str:
    """Replace the AI placeholder closing block with the owner's real details."""
    name    = (profile.get("name")          or "").strip()
    biz     = (profile.get("business_name") or "").strip()
    email   = (profile.get("email")         or "").strip()
    contact = (profile.get("contact")       or "").strip()

    sig = "Best regards,\n\n"
    if name:    sig += f"{name}\n"
    if biz:     sig += f"{biz}\n"
    if email:   sig += f"{email}\n"
    if contact: sig += f"{contact}"

    replaced = re.sub(r'best\s+regards.*', sig, draft, flags=re.IGNORECASE | re.DOTALL)
    if replaced == draft:
        replaced = draft.rstrip() + "\n\n" + sig
    return replaced


# ─── Crew runners ─────────────────────────────────────────────────────────────

def run_phase1(inquiry: str, individual_texts: list, email_1: str, email_2: str, email_3: str, user_id: int | None = None):
    from serviceflow_ai import user_context
    from serviceflow_ai.doc_manager import has_documents

    if user_id and not has_documents(user_id):
        raise gr.Error(
            "No business documents found for your account. "
            "Please upload at least one document from the Dashboard before generating a quote."
        )

    texts = [t for t in (individual_texts or []) if t.strip()]
    if len(texts) <= 1:
        texts = [inquiry.strip()]
    texts = texts[:3]

    email_list = [email_1 or "", email_2 or "", email_3 or ""]

    if not texts[0]:
        raise gr.Error("Customer inquiry cannot be empty.")
    if not email_list[0].strip():
        raise gr.Error("Customer email cannot be empty.")

    total = len(texts)

    def _loading_yield(msg, card, done_quotes):
        return (
            gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
            msg, gr.update(),
            card,
            gr.update(visible=False),
            gr.update(value=""),
            None,
            gr.update(visible=False),
            done_quotes, 0, 0,
            gr.update(visible=False), "",
            {},
        )

    yield _loading_yield("Generating quote, please wait…", _loading_multi_html(1, total), [])

    quotes = []
    for i, text in enumerate(texts):
        if i > 0:
            yield _loading_yield(
                f"Generating quote {i + 1} of {total}, please wait…",
                _loading_multi_html(i + 1, total),
                quotes,
            )

        raw_email = email_list[i] if i < len(email_list) and email_list[i] else email_list[0]
        inputs = {"customer_inquiry": text, "customer_email": raw_email.strip()}
        try:
            if user_id:
                user_context.set_active_user(user_id)
            result = ServiceflowAi().phase1_crew().kickoff(inputs=inputs)
        except Exception as exc:
            raise gr.Error(f"Crew execution failed on request {i + 1}: {exc}")
        finally:
            user_context.clear_active_user()

        t           = result.tasks_output
        pricing_o   = _safe(t, 3)
        profit_o    = _safe(t, 4)
        readiness_o = _safe(t, 1)
        costing_o   = _safe(t, 2)
        draft_text  = _raw(t, 5) or ""

        if user_id and draft_text:
            from serviceflow_ai.auth import get_user_profile
            draft_text = _inject_signature(draft_text, get_user_profile(user_id))

        llm_email   = (getattr(_safe(t, 0), "customer_email", None) or "").strip()
        final_email = llm_email or raw_email.strip()

        quotes.append({
            "label":         f"Request {i + 1}",
            "draft":         draft_text,
            "pricing":       pricing_o,
            "profit":        profit_o,
            "readiness":     readiness_o,
            "costing":       costing_o,
            "inquiry_md":    fmt_inquiry(_safe(t, 0)),
            "readiness_md":  fmt_readiness(readiness_o),
            "costing_md":    fmt_costing(costing_o),
            "pricing_md":    fmt_pricing(pricing_o),
            "profit_md":     fmt_profit(profit_o),
            "customer_email":    final_email,
            "customer_inquiry":  text,
        })

    best_idx = _most_profitable_index(quotes)
    first_q  = quotes[best_idx]
    state    = {
        "customer_email":    first_q["customer_email"],
        "customer_inquiry":  first_q["customer_inquiry"],
        "user_id":           user_id,
    }
    multi = len(quotes) > 1

    yield (
        first_q["inquiry_md"],
        first_q["readiness_md"],
        first_q["costing_md"],
        first_q["pricing_md"],
        first_q["profit_md"],
        first_q["draft"],
        first_q["draft"],
        build_carousel_slide(quotes, best_idx, best_idx),
        gr.update(visible=True),
        gr.update(value=""),
        state,
        gr.update(visible=False),
        quotes,
        best_idx,
        best_idx,
        gr.update(visible=multi),
        f"{best_idx + 1} / {len(quotes)}" if multi else "",
        {i: "pending" for i in range(len(quotes))},
    )


def _hitl_outputs(delivery_md, hitl_visible, summary, state, statuses, disp_idx, next_q, total, best_idx):
    multi = total > 1
    return (
        delivery_md,
        gr.update(visible=hitl_visible),
        summary,
        state,
        gr.update(visible=True),
        statuses,
        disp_idx,
        next_q["draft"],
        next_q["draft"],
        f"{disp_idx + 1} / {total}" if multi else "",
        next_q["inquiry_md"],
        next_q["readiness_md"],
        next_q["costing_md"],
        next_q["pricing_md"],
        next_q["profit_md"],
    )


def approve_quote(draft_text: str, state: dict, idx: int, quotes: list, best_idx: int, statuses: dict):
    if not state:
        raise gr.Error("No active quote session — please generate a quote first.")
    if not quotes:
        raise gr.Error("No quotes available.")

    statuses = dict(statuses)
    total    = len(quotes)

    yield (
        _build_delivery_summary(quotes, statuses),
        gr.update(visible=False),
        SENDING_SUMMARY_HTML,
        state,
        gr.update(visible=False),
        statuses, idx,
        gr.update(), gr.update(), gr.update(),
        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
    )

    customer_email = quotes[idx].get("customer_email") or state.get("customer_email", "")
    inputs = {
        "human_approved":     "true",
        "customer_email":     customer_email,
        "draft_email_content": draft_text.strip(),
    }

    try:
        result = ServiceflowAi().phase2_crew().kickoff(inputs=inputs)
    except Exception as exc:
        raise gr.Error(f"Email delivery failed: {exc}")

    t        = result.tasks_output
    delivery = _safe(t, 0)
    sent     = delivery and delivery.sent

    statuses[idx] = "approved" if sent else "failed"
    if sent:
        uid = (state or {}).get("user_id")
        if uid:
            from serviceflow_ai.doc_manager import record_decision
            record_decision(uid, "approved")
    next_idx  = _next_pending_idx(statuses, idx, total)
    all_done  = next_idx is None
    disp_idx  = next_idx if next_idx is not None else idx
    next_q    = quotes[disp_idx]

    summary = (
        SUCCESS_SUMMARY_HTML
        if all_done and any(s == "approved" for s in statuses.values())
        else build_carousel_slide(quotes, disp_idx, best_idx, statuses)
    )

    yield _hitl_outputs(
        _build_delivery_summary(quotes, statuses),
        not all_done,
        summary,
        state if not all_done else None,
        statuses, disp_idx, next_q, total, best_idx,
    )


def reject_quote(_: str, state: dict, idx: int, quotes: list, best_idx: int, statuses: dict):
    if not state:
        raise gr.Error("No active quote session — please generate a quote first.")
    if not quotes:
        raise gr.Error("No quotes available.")

    statuses = dict(statuses)
    total    = len(quotes)

    statuses[idx] = "rejected"
    uid = (state or {}).get("user_id")
    if uid:
        from serviceflow_ai.doc_manager import record_decision
        record_decision(uid, "rejected")
    gr.Info(f"Quote {idx + 1} rejected. No email will be sent.")

    next_idx = _next_pending_idx(statuses, idx, total)
    all_done  = next_idx is None
    disp_idx  = next_idx if next_idx is not None else idx
    next_q    = quotes[disp_idx]

    summary = (
        gr.update()
        if all_done and not any(s == "approved" for s in statuses.values())
        else build_carousel_slide(quotes, disp_idx, best_idx, statuses)
    )

    yield _hitl_outputs(
        _build_delivery_summary(quotes, statuses),
        not all_done,
        summary,
        state if not all_done else None,
        statuses, disp_idx, next_q, total, best_idx,
    )


def nav_carousel(direction: int, idx: int, quotes: list, best_idx: int, statuses: dict):
    if not quotes:
        return 0, EMPTY_SUMMARY_HTML, "", "", "", "", "", "", "", ""
    total   = len(quotes)
    new_idx = max(0, min(total - 1, idx + direction))
    q       = quotes[new_idx]
    return (
        new_idx,
        build_carousel_slide(quotes, new_idx, best_idx, statuses),
        q["draft"],
        q["draft"],
        f"{new_idx + 1} / {total}",
        q["inquiry_md"],
        q["readiness_md"],
        q["costing_md"],
        q["pricing_md"],
        q["profit_md"],
    )


# ─── UI ──────────────────────────────────────────────────────────────────────

def render(user_id_state: gr.State = None):
    """Render the quote-generator section inside the active gr.Blocks context.

    Parameters
    ----------
    user_id_state : gr.State  —  shared state holding the logged-in user's integer ID

    Returns
    -------
    section       : gr.Group  (hidden by default)
    back_dash_btn : gr.Button
    """
    with gr.Group(elem_id="quote-section", visible=False) as section:

        quote_title_html = gr.HTML("", elem_id="quote-title")

        with gr.Row(elem_id="back-btn-row"):
            back_dash_btn = gr.Button(
                "← Back to Dashboard", elem_id="back-dash-btn", min_width=80
            )

        with gr.Row(equal_height=False):

            # ── Left: input form ─────────────────────────────────────────────
            with gr.Column(scale=2, elem_id="form-panel"):
                gr.Markdown(
                    "<h3 style='text-align:center;padding-top:10px;padding-bottom:10px;"
                    "color:#000;'>New Service Inquiry</h3>"
                )
                inquiry_input = gr.Textbox(
                    label="Customer Inquiry",
                    placeholder=PLACEHOLDER_INQUIRY,
                    lines=8,
                    max_lines=16,
                )
                gr.HTML('<div class="or-divider">or upload a document</div>')
                file_upload = gr.File(
                    label="Attach Files  (.txt · .pdf · .docx — up to 3)",
                    file_types=[".txt", ".pdf", ".docx", ".doc"],
                    file_count="multiple",
                    elem_id="upload-box",
                )
                email_input_1 = gr.Textbox(
                    label="Customer Email", placeholder="customer@example.com", lines=1
                )
                with gr.Column(visible=False) as email_row_2:
                    email_input_2 = gr.Textbox(
                        label="Customer Email — Request 2",
                        placeholder="extracted from document",
                        lines=1,
                        interactive=False,
                    )
                with gr.Column(visible=False) as email_row_3:
                    email_input_3 = gr.Textbox(
                        label="Customer Email — Request 3",
                        placeholder="extracted from document",
                        lines=1,
                        interactive=False,
                    )
                submit_btn = gr.Button(
                    "⚡  Generate Quote", variant="primary", elem_id="submit-btn"
                )
                gr.Markdown(
                    "<br><small style='color:#8a9bb0;'>Runs 6 analysis agents then pauses "
                    "for your review before sending. Allow 30–90 seconds.</small>"
                )

            # ── Right: results ───────────────────────────────────────────────
            with gr.Column(scale=3, elem_id="results-panel"):
                gr.Markdown(
                    "<h3 style='color:#000000;padding-top:10px;padding-bottom:10px;"
                    "text-align:center;'>Here's What I Think</h3>"
                )
                summary_card = gr.HTML(value=EMPTY_SUMMARY_HTML)

                with gr.Row(visible=False, elem_id="carousel-nav") as carousel_nav:
                    carousel_prev      = gr.Button("‹", scale=1, size="sm", elem_id="carousel-prev")
                    carousel_indicator = gr.HTML("")
                    carousel_next      = gr.Button("›", scale=1, size="sm", elem_id="carousel-next")

                phase1_state           = gr.State(None)
                quotes_state           = gr.State([])
                carousel_idx           = gr.State(0)
                best_idx_state         = gr.State(0)
                individual_texts_state = gr.State([])
                quote_statuses         = gr.State({})

                with gr.Group(elem_id="hitl-panel", visible=False) as hitl_section:
                    gr.HTML("""
                    <div style="padding:14px 18px 6px 18px;">
                      <strong style="color:#92400e;font-size:1.05rem;">
                        ⏸ Human Review Required
                      </strong>
                      <p style="color:#78350f;margin:6px 0 0 0;font-size:0.88rem;">
                        Review the draft quote email below. Edit it if needed, then
                        <strong>Approve &amp; Send</strong> to dispatch to the customer,
                        or <strong>Reject</strong> to cancel delivery entirely.
                      </p>
                    </div>""")
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
                        reject_btn = gr.Button("❌  Reject", elem_id="reject-btn", scale=1)

                with gr.Tabs():
                    with gr.Tab("📄 Quote & Recommendation"):
                        gr.Markdown(
                            "<h3 style='color:#000;padding-top:10px;padding-bottom:10px;"
                            "text-align:center;'>Draft Quote Email</h3>"
                        )
                        draft_output = gr.Textbox(
                            label=None, show_label=False,
                            lines=14, interactive=False, elem_id="draft-box",
                        )
                        with gr.Column(visible=False) as delivery_section:
                            gr.Markdown(
                                "<h3 style='color:#000;padding-top:10px;padding-bottom:10px;"
                                "text-align:center;'>Email Delivery Status</h3>"
                            )
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

    # ── Internal event wiring ────────────────────────────────────────────────

    hitl_draft.change(fn=lambda t: t, inputs=[hitl_draft], outputs=[draft_output])

    file_upload.change(
        fn=parse_uploaded_file,
        inputs=[file_upload],
        outputs=[
            inquiry_input, individual_texts_state,
            email_input_1, email_input_2, email_row_2,
            email_input_3, email_row_3,
        ],
    )

    _phase1_inputs = [
        inquiry_input, individual_texts_state,
        email_input_1, email_input_2, email_input_3,
    ]
    if user_id_state is not None:
        _phase1_inputs.append(user_id_state)

    submit_btn.click(
        fn=run_phase1,
        inputs=_phase1_inputs,
        outputs=[
            inquiry_output, readiness_output, costing_output, pricing_output, profit_output,
            draft_output, hitl_draft, summary_card, hitl_section, delivery_output,
            phase1_state, delivery_section, quotes_state, carousel_idx,
            best_idx_state, carousel_nav, carousel_indicator, quote_statuses,
        ],
    )

    _carousel_outputs = [
        carousel_idx, summary_card, hitl_draft, draft_output, carousel_indicator,
        inquiry_output, readiness_output, costing_output, pricing_output, profit_output,
    ]
    carousel_prev.click(
        fn=lambda idx, quotes, best, statuses: nav_carousel(-1, idx, quotes, best, statuses),
        inputs=[carousel_idx, quotes_state, best_idx_state, quote_statuses],
        outputs=_carousel_outputs,
    )
    carousel_next.click(
        fn=lambda idx, quotes, best, statuses: nav_carousel(1, idx, quotes, best, statuses),
        inputs=[carousel_idx, quotes_state, best_idx_state, quote_statuses],
        outputs=_carousel_outputs,
    )

    _hitl_outs = [
        delivery_output, hitl_section, summary_card, phase1_state, delivery_section,
        quote_statuses, carousel_idx, hitl_draft, draft_output, carousel_indicator,
        inquiry_output, readiness_output, costing_output, pricing_output, profit_output,
    ]
    approve_btn.click(
        fn=approve_quote,
        inputs=[hitl_draft, phase1_state, carousel_idx, quotes_state, best_idx_state, quote_statuses],
        outputs=_hitl_outs,
    )
    reject_btn.click(
        fn=reject_quote,
        inputs=[hitl_draft, phase1_state, carousel_idx, quotes_state, best_idx_state, quote_statuses],
        outputs=_hitl_outs,
    )

    return section, back_dash_btn, quote_title_html
