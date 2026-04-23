"""ServiceFlow AI — Gradio front-end
Run:  python app.py
"""
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from serviceflow_ai.auth import ensure_users_table, verify_user, get_user_id, get_user_profile
from serviceflow_ai.doc_manager import has_documents
from pages import auth as auth_page
from pages import dashboard as dash_page
from pages import quote as quote_page

ensure_users_table()

# ─── Theme — force light mode in both light and dark OS settings ──────────────

_LIGHT_BG   = "#ffffff"
_SUBTLE_BG  = "#f4f6f9"

_theme = gr.themes.Soft().set(
    body_background_fill=_LIGHT_BG,
    body_background_fill_dark=_LIGHT_BG,
    background_fill_primary=_LIGHT_BG,
    background_fill_primary_dark=_LIGHT_BG,
    background_fill_secondary=_SUBTLE_BG,
    background_fill_secondary_dark=_SUBTLE_BG,
    block_background_fill=_LIGHT_BG,
    block_background_fill_dark=_LIGHT_BG,
    panel_background_fill=_SUBTLE_BG,
    panel_background_fill_dark=_SUBTLE_BG,
    input_background_fill=_LIGHT_BG,
    input_background_fill_dark=_LIGHT_BG,
)

# ─── Styling ──────────────────────────────────────────────────────────────────

CSS = """
/* ── Base light-mode reset ── */
html, body {
    background: #ffffff !important;
    color-scheme: light !important;
}

/* Force white background — use `background` shorthand to beat Gradio's var()-based rules */
.gradio-container,
.gradio-container.dark,
.dark .gradio-container,
[data-theme="dark"] .gradio-container,
.gradio-container > .main,
.main, .wrap, .panel, .block,
[data-testid], .form, .gap, .padded, .compact,
.tabs, .tabitem, [role="tablist"], .tab-nav {
    background: #ffffff !important;
    color: #1e2d45 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}

/* Target the dark-mode root class Gradio 6 adds to <body> */
body.dark, html.dark, .dark {
    background: #ffffff !important;
    color-scheme: light !important;
}

/* ── Header ── */
#sf-header { background: linear-gradient(135deg, #0f1f3d 0%, #1a3a6e 100%) !important;
             padding: 24px 32px; border-radius: 12px; margin-bottom: 20px; }
#sf-header h1 { color: #ffffff !important; font-size: 1.75rem; font-weight: 700; margin: 0 0 4px 0; }
#sf-header p  { color: #94b4d9 !important; font-size: 0.9rem; margin: 0; }

/* ── Panels ── */
#form-panel, #results-panel {
    background: #ffffff !important; border-radius: 12px !important;
    padding: 24px !important; box-shadow: 0 1px 6px rgba(0,0,0,0.07) !important; }

/* ── Labels ── */
label, .label-wrap span { font-weight: 600 !important; color: #1e2d45 !important; }

/* ── Inputs ── */
input, textarea, .input-wrap { background: #ffffff !important; color: #1e2d45 !important;
    border-color: #d4dde8 !important; border-radius: 8px !important; }
input:focus, textarea:focus { border-color: #1a3a6e !important;
    box-shadow: 0 0 0 2px rgba(26,58,110,0.12) !important; }

/* ── Submit button ── */
#submit-btn { background: #1a3a6e !important; color: #ffffff !important; font-weight: 700 !important;
              border-radius: 8px !important; font-size: 1rem !important; border: none !important; }
#submit-btn:hover { background: #0f1f3d !important; }

/* ── Tabs ── */
.tab-nav button, button[role="tab"] {
    font-weight: 600 !important; color: #000000 !important; background: transparent !important;
    padding-top: 10px !important; padding-bottom: 10px !important; }
.tab-nav button.selected,
button[role="tab"][aria-selected="true"] {
    background: #1a3a6e !important; color: #ffffff !important;
    border-radius: 6px 6px 0 0 !important; border-bottom: none !important;
    padding-top: 10px !important; padding-bottom: 10px !important; }

/* ── Markdown tables ── */
.prose table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.prose th { background: #f0f4f8 !important; color: #1e2d45 !important;
            padding: 8px 12px; font-weight: 600; }
.prose td { padding: 8px 12px; border-bottom: 1px solid #e8ecf0; color: #374151; }

/* ── Draft email box ── */
#draft-box textarea { font-family: 'Georgia', serif !important; font-size: 0.92rem !important;
                      line-height: 1.65 !important; background: #fafcff !important;
                      border: 1px solid #d0dce8 !important; }

/* ── Divider ── */
.or-divider { display:flex; align-items:center; gap:10px; margin:8px 0;
              color:#94a3b8; font-size:0.78rem; font-weight:600;
              letter-spacing:0.8px; text-transform:uppercase; }
.or-divider::before, .or-divider::after { content:''; flex:1; height:1px; background:#e2e8f0; }

/* ── Upload box ── */
#upload-box { margin-top: 0 !important; }
#upload-box > .block { padding: 0 !important; }
#upload-box .upload-container,
#upload-box [data-testid="upload-container"] {
    min-height: 88px !important; max-height: 88px !important;
    border: 2px dashed #c7d8ee !important; border-radius: 10px !important;
    background: #f8fafd !important; transition: all 0.2s; }
#upload-box .upload-container:hover,
#upload-box [data-testid="upload-container"]:hover {
    border-color: #1a3a6e !important; background: #eef4ff !important; }
#upload-box svg { width: 20px !important; height: 20px !important; color: #1a3a6e !important; }
#upload-box .upload-container p,
#upload-box [data-testid="upload-container"] p {
    font-size: 0.82rem !important; color: #64748b !important; margin: 2px 0 !important; }

/* ── Loading spinner ── */
@keyframes sf-spin { to { transform: rotate(360deg); } }
.sf-spinner { width:26px; height:26px; border:3px solid rgba(148,180,217,0.25);
              border-top-color:#94b4d9; border-radius:50%;
              animation:sf-spin 0.75s linear infinite; flex-shrink:0; }

/* ── Auth section outer wrapper — no visual styling so it vanishes when hidden ── */
#auth-section { background: transparent !important; border: none !important;
                box-shadow: none !important; padding: 0 !important; margin: 0 !important; }

/* ── Auth field-error HTML components — zero height when hidden ── */
#err-login-email, #err-login-pw,
#err-reg-name, #err-reg-biz, #err-reg-email,
#err-reg-contact, #err-reg-pw, #err-reg-confirm {
    padding: 0 !important; margin: 0 !important;
    background: transparent !important; border: none !important; }
#auth-login-msg, #auth-reg-msg {
    padding: 0 !important; margin: 0 !important;
    background: transparent !important; border: none !important; }

/* ── Auth card — the actual visible card, hidden along with its content ── */
#auth-card { max-width: 460px; margin: 40px auto !important;
             background: #ffffff !important; border: 1px solid #dde3ec !important;
             border-radius: 14px !important; box-shadow: 0 4px 24px rgba(0,0,0,0.10) !important;
             padding: 28px 32px !important; }
#auth-card label, #auth-card .label-wrap span { color: #1e2d45 !important; font-weight: 600 !important; }
#auth-card > .block, #auth-card .block > div,
#auth-card .tabs, #auth-card [data-testid="tabs"] {
    background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 0 !important; }
#auth-login-btn { background: #1a3a6e !important; color: #fff !important; font-weight: 700 !important;
                  border-radius: 8px !important; border: none !important; }
#auth-login-btn:hover { background: #0f1f3d !important; }
#auth-reg-btn   { background: #059669 !important; color: #fff !important; font-weight: 700 !important;
                  border-radius: 8px !important; border: none !important; }
#auth-reg-btn:hover   { background: #047857 !important; }

/* ── Dashboard & quote section wrappers ── */
#dashboard-section, #dashboard-section > .block,
#quote-section,     #quote-section > .block {
    background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 0 !important; margin: 0 !important; }

/* ── Docs accordion & upload ── */
#docs-accordion { background: #ffffff !important; border-radius: 12px !important;
                  box-shadow: 0 1px 6px rgba(0,0,0,0.07) !important; margin-bottom: 16px !important; }
#add-doc-btn { background: #1a3a6e !important; color: #fff !important;
               font-weight: 700 !important; border-radius: 8px !important; border: none !important; }
#add-doc-btn:hover { background: #0f1f3d !important; }
#doc-upload-box .upload-container,
#doc-upload-box [data-testid="upload-container"] {
    min-height: 72px !important; border: 2px dashed #c7d8ee !important;
    border-radius: 8px !important; background: #f8fafd !important; }
#no-docs-warning { color: #b45309 !important; font-weight: 600 !important;
                   font-size: 0.9rem !important; min-height: 0 !important; }

/* ── Dashboard nav buttons ── */
#go-quote-btn { background: #1a3a6e !important; color: #fff !important; font-weight: 700 !important;
                border-radius: 10px !important; font-size: 1rem !important; border: none !important; }
#go-quote-btn:hover { background: #0f1f3d !important; }
#logout-btn   { background: transparent !important; border: 1px solid #dc2626 !important;
                color: #dc2626 !important; font-weight: 600 !important; border-radius: 8px !important; }
#logout-btn:hover   { background: #fee2e2 !important; }
#back-dash-btn { background: #1a3a6e !important; border: none !important;
                 color: #ffffff !important; font-weight: 600 !important; border-radius: 8px !important; }
#back-dash-btn:hover { background: #0f1f3d !important; }

/* ── Back button row — push button to extreme right ── */
#back-btn-row { justify-content: flex-end !important; padding: 4px 0 !important; }
#back-btn-row > .block { flex: 0 0 auto !important; min-width: 0 !important; width: auto !important; }

/* ── Carousel navigation ── */
#carousel-nav { margin: 6px 0 2px 0 !important; }
#carousel-prev, #carousel-next { background: #1a3a6e !important; color: #fff !important;
    font-weight: 700 !important; font-size: 1.2rem !important; border-radius: 8px !important;
    border: none !important; min-width: 44px !important; }
#carousel-prev:hover, #carousel-next:hover { background: #0f1f3d !important; }

/* ── Upload / table card columns inside accordion ── */
#doc-upload-col, #doc-table-col {
    background: #ffffff !important;
    border-radius: 10px !important;
    border: 1px solid #e8ecf2 !important;
    padding: 16px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important; }

/* Tighten the gap between the two columns */
#docs-accordion .gap { gap: 6px !important; }

/* ── Doc table pagination ── */
#doc-pagination-row { align-items: center !important; margin-top: 8px !important; }
#prev-page-btn, #next-page-btn {
    background: #1a3a6e !important; color: #fff !important;
    font-weight: 600 !important; border-radius: 6px !important;
    border: none !important; font-size: 0.85rem !important; }
#prev-page-btn:disabled, #next-page-btn:disabled {
    background: #e2e8f0 !important; color: #94a3b8 !important; }
#prev-page-btn:hover:not(:disabled), #next-page-btn:hover:not(:disabled) {
    background: #0f1f3d !important; }
#page-label-md, #page-label-md p { text-align: center !important;
    color: #64748b !important; font-size: 0.82rem !important; margin: 0 !important; }

/* ── HITL review panel ── */
#hitl-panel { border-left: 4px solid #f59e0b !important; border-radius: 0 12px 12px 0 !important;
              background: #fffbeb !important; margin: 12px 0 !important; padding: 4px 0 !important; }
#hitl-draft-box textarea { font-family: 'Georgia', serif !important; font-size: 0.92rem !important;
                           line-height: 1.65 !important; }
#approve-btn { background: #059669 !important; border-color: #059669 !important;
               color: #fff !important; font-weight: 700 !important; }
#approve-btn:hover { background: #047857 !important; }
#reject-btn  { background: #dc2626 !important; border-color: #dc2626 !important;
               color: #fff !important; font-weight: 700 !important; }
#reject-btn:hover  { background: #b91c1c !important; }
"""

_ERR_STYLE = (
    "color:#dc2626 !important;font-size:0.82rem !important;font-weight:600 !important;"
    "margin:3px 0 8px 2px !important;display:block !important;"
)
_LOGIN_ERR_BOX = (
    "background:#dc2626 !important;border:2px solid #b91c1c !important;"
    "border-radius:8px !important;padding:12px 16px !important;"
    "color:#ffffff !important;font-size:0.92rem !important;"
    "font-weight:700 !important;margin-top:10px !important;display:block !important;"
)


def _fe(msg: str = ""):
    if msg:
        return gr.update(visible=True, value=f'<span style="{_ERR_STYLE}">{msg}</span>')
    return gr.update(visible=False, value="")


def build_header_html(business_name: str = "") -> str:
    subtitle = (
        f"{business_name} &nbsp;·&nbsp; AI Quote Generation"
        if business_name else
        "AI-Powered Quote Generation Engine &nbsp;·&nbsp; 7-Agent Sequential Crew"
    )
    return f"""<div id="sf-header">
  <h1>&#9881;&#65039; Buckets &amp; Bucks AI</h1>
  <p>{subtitle}</p>
</div>"""


# ─── App ──────────────────────────────────────────────────────────────────────

with gr.Blocks(title="ServiceFlow AI — Quote Generator") as demo:

    header_html          = gr.HTML(build_header_html())
    current_user         = gr.State(None)   # email string
    current_user_id      = gr.State(None)   # integer DB user ID
    current_user_name    = gr.State(None)   # display name
    current_business     = gr.State(None)   # business name

    # Render each page (each adds its own gr.Group to this Blocks context)
    (auth_section,
     login_email, login_password, login_btn, login_msg,
     login_email_err, login_password_err)                                    = auth_page.render()
    (dashboard_section, dashboard_html, go_quote_btn,
     logout_btn, no_docs_msg,
     doc_table, doc_page, page_label,
     prev_page_btn, next_page_btn)                                           = dash_page.render(current_user_id)
    quote_section, back_dash_btn, quote_title_html                           = quote_page.render(current_user_id)

    # ── Login handler ────────────────────────────────────────────────────────

    def handle_login(email: str, password: str):
        e_email, e_pw = "", ""
        if not email.strip():
            e_email = "Email address is required."
        if not password:
            e_pw = "Password is required."

        if e_email or e_pw:
            return (
                gr.update(), gr.update(), gr.update(), gr.update(),
                None, None, None, None,
                gr.update(visible=False, value=""),
                _fe(e_email), _fe(e_pw),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(),
            )

        if verify_user(email, password):
            uid     = get_user_id(email)
            profile = get_user_profile(uid)
            name    = profile["name"] or email.split("@")[0]
            biz     = profile["business_name"]
            tbl_html, tbl_page, tbl_label, prev_upd, next_upd = dash_page.make_table_updates(uid, 0)
            return (
                gr.update(visible=False),                      # hide auth
                gr.update(visible=True),                       # show dashboard
                gr.update(visible=False),                      # hide quote
                dash_page.build_html(name, biz, uid),          # welcome card
                email.strip().lower(),                         # current_user
                uid,                                           # current_user_id
                name,                                          # current_user_name
                biz,                                           # current_business
                gr.update(visible=False, value=""),            # login_msg
                _fe(""), _fe(""),                              # field errors
                tbl_html, tbl_page, tbl_label, prev_upd, next_upd,
                build_header_html(biz),                        # update header
            )

        err_html = f'<div style="{_LOGIN_ERR_BOX}">Incorrect email or password. Please try again.</div>'
        return (
            gr.update(), gr.update(), gr.update(), gr.update(),
            None, None, None, None,
            gr.update(visible=True, value=err_html),
            _fe(""), _fe(""),
            gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(),
        )

    _login_outs = [
        auth_section, dashboard_section, quote_section,
        dashboard_html,
        current_user, current_user_id, current_user_name, current_business,
        login_msg, login_email_err, login_password_err,
        doc_table, doc_page, page_label, prev_page_btn, next_page_btn,
        header_html,
    ]
    login_btn.click(fn=handle_login, inputs=[login_email, login_password], outputs=_login_outs)
    login_email.submit(fn=handle_login, inputs=[login_email, login_password], outputs=_login_outs)
    login_password.submit(fn=handle_login, inputs=[login_email, login_password], outputs=_login_outs)

    # ── Go to quote ──────────────────────────────────────────────────────────

    def handle_go_quote(user_id, biz):
        if not user_id or not has_documents(user_id):
            return (
                gr.update(), gr.update(),
                gr.update(value="Please upload at least one business document before generating a quote."),
                gr.update(),
            )
        title_html = (
            f'<div style="background:#eef4ff !important;border:1px solid #c7d8ee !important;'
            f'border-radius:10px !important;padding:14px 22px !important;margin-bottom:6px !important;">'
            f'<p style="color:#64748b !important;font-size:0.72rem !important;font-weight:700 !important;'
            f'text-transform:uppercase !important;letter-spacing:1.2px !important;margin:0 0 3px 0 !important;">'
            f'Quote Generation</p>'
            f'<h2 style="color:#1a3a6e !important;margin:0 !important;font-size:1.2rem !important;'
            f'font-weight:700 !important;">{biz or "Your Business"} &mdash; Quotation Prediction</h2>'
            f'</div>'
        )
        return gr.update(visible=False), gr.update(visible=True), gr.update(value=""), gr.update(value=title_html)

    go_quote_btn.click(
        fn=handle_go_quote,
        inputs=[current_user_id, current_business],
        outputs=[dashboard_section, quote_section, no_docs_msg, quote_title_html],
    )

    # ── Back to dashboard ────────────────────────────────────────────────────

    def handle_back(name, biz, user_id):
        return (
            gr.update(visible=True),
            gr.update(visible=False),
            dash_page.build_html(name or "", biz or "", user_id) if user_id else gr.update(),
        )

    back_dash_btn.click(
        fn=handle_back,
        inputs=[current_user_name, current_business, current_user_id],
        outputs=[dashboard_section, quote_section, dashboard_html],
    )

    # ── Logout ───────────────────────────────────────────────────────────────

    logout_btn.click(
        fn=lambda: (
            gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
            None, None, None, None,
            build_header_html(),
        ),
        outputs=[
            auth_section, dashboard_section, quote_section,
            current_user, current_user_id, current_user_name, current_business,
            header_html,
        ],
    )


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        css=CSS,
        theme=_theme,
        share=True
    )
