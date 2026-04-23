"""Dashboard page — welcome card, document management, navigation."""
import gradio as gr
from serviceflow_ai.doc_manager import (
    DOCUMENT_TYPES,
    LABEL_TO_KEY,
    build_docs_table_html,
    get_decision_counts,
    get_user_documents,
    upload_document,
)

PER_PAGE = 5


def build_html(name: str, business_name: str = "", user_id: int | None = None) -> str:
    stats_html = ""
    if user_id is not None:
        counts = get_decision_counts(user_id)
        approved = counts["approved"]
        rejected = counts["rejected"]
        stats_html = f"""
<div style="display:flex;gap:16px;margin:16px 0 4px 0;">
  <div style="flex:1;background:linear-gradient(135deg,#d1fae5,#a7f3d0);
              border:1px solid #6ee7b7;border-radius:12px;
              padding:18px 20px;text-align:center;">
    <p style="color:#065f46;font-size:0.75rem;font-weight:700;text-transform:uppercase;
              letter-spacing:1.2px;margin:0 0 6px 0;">Approved Quotes</p>
    <p style="color:#065f46;font-size:2.4rem;font-weight:800;margin:0;line-height:1;">{approved}</p>
  </div>
  <div style="flex:1;background:linear-gradient(135deg,#fee2e2,#fecaca);
              border:1px solid #fca5a5;border-radius:12px;
              padding:18px 20px;text-align:center;">
    <p style="color:#991b1b;font-size:0.75rem;font-weight:700;text-transform:uppercase;
              letter-spacing:1.2px;margin:0 0 6px 0;">Rejected Quotes</p>
    <p style="color:#991b1b;font-size:2.4rem;font-weight:800;margin:0;line-height:1;">{rejected}</p>
  </div>
</div>"""
    biz_line = (
        f'<span style="display:inline-block;background:#eef4ff;color:#1a3a6e;'
        f'font-size:0.78rem;font-weight:600;border-radius:20px;padding:2px 10px;'
        f'border:1px solid #c7d8ee;margin-top:4px;">{business_name}</span>'
        if business_name else ""
    )
    return f"""
<div style="padding:8px 0 8px 0;">
  <h2 style="color:#1e2d45;margin:0 0 2px 0;font-size:1.5rem;">
    Welcome back, <strong style="color:#1a3a6e;">{name}</strong>
  </h2>
  {biz_line}
  <p style="color:#64748b;margin:8px 0 4px 0;font-size:0.88rem;">
    Manage your business documents below or generate a new quote.
  </p>
  {stats_html}
</div>"""


def make_table_updates(user_id: int, page: int = 0):
    """Return (html, page, label_md, prev_update, next_update).

    Called from app.py login handler so all 5 table components stay in sync.
    """
    docs = get_user_documents(user_id)
    total = len(docs)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    html = build_docs_table_html(user_id, page, PER_PAGE)
    label = (
        f"<p style='text-align:center;color:#64748b;font-size:0.82rem;margin:0;'>"
        f"Page {page + 1} of {total_pages}</p>"
        if total_pages > 1 else ""
    )
    return (
        html,
        page,
        label,
        gr.update(interactive=page > 0),
        gr.update(interactive=page < total_pages - 1),
    )


def render(user_id_state: gr.State):
    """Render the dashboard section inside the active gr.Blocks context.

    Returns
    -------
    section, dashboard_html, go_quote_btn, logout_btn, no_docs_msg,
    doc_table, doc_page, page_label, prev_page_btn, next_page_btn
    """
    with gr.Group(elem_id="dashboard-section", visible=False) as section:

        dashboard_html = gr.HTML("")

        # ── Business Documents ───────────────────────────────────────────────
        with gr.Accordion("📁  Business Documents", open=True, elem_id="docs-accordion"):

            gr.Markdown(
                "<p style='color:#64748b;font-size:0.85rem;margin:0 0 14px 0;'>"
                "Step 1 — choose a document type &nbsp;·&nbsp; "
                "Step 2 — attach your file &nbsp;·&nbsp; "
                "click <strong>Add Document</strong>.</p>"
            )

            with gr.Row(equal_height=False):

                # ── Left: upload form ────────────────────────────────────────
                with gr.Column(scale=9, min_width=300, elem_id="doc-upload-col"):
                    doc_type_dd = gr.Dropdown(
                        label="Step 1 · Document Type",
                        choices=["— Please Select A Category —"] + list(DOCUMENT_TYPES.values()),
                        value="— Please Select A Category —",
                        elem_id="doc-type-dd",
                    )
                    doc_file = gr.File(
                        label="Step 2 · Upload file  (.pdf · .docx · .xlsx · .xls · .json · .txt)",
                        file_types=[".pdf", ".docx", ".doc", ".xlsx", ".xls", ".json", ".txt"],
                        elem_id="doc-upload-box",
                    )
                    upload_doc_btn = gr.Button(
                        "Add Document", variant="primary", elem_id="add-doc-btn"
                    )
                    upload_msg = gr.Markdown("")

                # ── Vertical divider ─────────────────────────────────────────
                gr.HTML(
                    '<div style="width:1px;background:#e2e8f0;'
                    'margin:4px 6px;align-self:stretch;min-height:180px;'
                    'flex-shrink:0;"></div>'
                )

                # ── Right: table + pagination ────────────────────────────────
                with gr.Column(scale=11, min_width=320, elem_id="doc-table-col"):
                    doc_table = gr.HTML("")
                    with gr.Row(elem_id="doc-pagination-row"):
                        prev_page_btn = gr.Button(
                            "← Prev", scale=1, interactive=False, elem_id="prev-page-btn"
                        )
                        with gr.Column(scale=2, min_width=0):
                            page_label = gr.Markdown("", elem_id="page-label-md")
                        next_page_btn = gr.Button(
                            "Next →", scale=1, interactive=False, elem_id="next-page-btn"
                        )

        doc_page = gr.State(0)

        # ── Action row ──────────────────────────────────────────────────────
        no_docs_msg = gr.Markdown("", elem_id="no-docs-warning")
        with gr.Row():
            go_quote_btn = gr.Button(
                "⚡  Generate New Quote",
                variant="primary",
                scale=3,
                elem_id="go-quote-btn",
            )
            logout_btn = gr.Button("Log Out", scale=1, elem_id="logout-btn")

    _table_comps = [doc_table, doc_page, page_label, prev_page_btn, next_page_btn]

    # ── Upload handler ───────────────────────────────────────────────────────
    _PLACEHOLDER = "— Please Select A Category —"

    def handle_upload(doc_type_label, file, user_id):
        if not doc_type_label or doc_type_label == _PLACEHOLDER:
            return ("⚠️ Please select a document type first (Step 1).",
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
        if file is None:
            return ("⚠️ Please attach a file (Step 2).",
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
        if user_id is None:
            return ("❌ Session expired — please log in again.",
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update())

        canonical_key = LABEL_TO_KEY.get(doc_type_label, doc_type_label)
        path = file.name if hasattr(file, "name") else str(file)
        ok, msg = upload_document(user_id, canonical_key, path)
        status = f"✅ {msg}" if ok else f"❌ {msg}"
        return (status,) + make_table_updates(user_id, 0)

    upload_doc_btn.click(
        fn=handle_upload,
        inputs=[doc_type_dd, doc_file, user_id_state],
        outputs=[upload_msg] + _table_comps,
    )

    prev_page_btn.click(
        fn=lambda uid, p: make_table_updates(uid, p - 1),
        inputs=[user_id_state, doc_page],
        outputs=_table_comps,
    )

    next_page_btn.click(
        fn=lambda uid, p: make_table_updates(uid, p + 1),
        inputs=[user_id_state, doc_page],
        outputs=_table_comps,
    )

    return (
        section, dashboard_html, go_quote_btn, logout_btn, no_docs_msg,
        doc_table, doc_page, page_label, prev_page_btn, next_page_btn,
    )
