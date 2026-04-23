"""Auth page — login and registration with field-level validation."""
import re
import gradio as gr
from serviceflow_ai.auth import register_user

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Use solid vivid colors + !important so the global `background:#fff !important` reset
# can't override them.
_ERR_STYLE = (
    "color:#dc2626 !important;font-size:0.82rem !important;font-weight:600 !important;"
    "margin:3px 0 8px 2px !important;display:block !important;"
)
_SUCCESS_BOX = (
    "background:#16a34a !important;border:2px solid #15803d !important;"
    "border-radius:8px !important;padding:12px 16px !important;"
    "color:#ffffff !important;font-size:0.92rem !important;"
    "font-weight:700 !important;margin-top:10px !important;display:block !important;"
)
_ERROR_BOX = (
    "background:#dc2626 !important;border:2px solid #b91c1c !important;"
    "border-radius:8px !important;padding:12px 16px !important;"
    "color:#ffffff !important;font-size:0.92rem !important;"
    "font-weight:700 !important;margin-top:10px !important;display:block !important;"
)


def _field_err(msg: str = ""):
    if msg:
        return gr.update(visible=True, value=f'<span style="{_ERR_STYLE}">{msg}</span>')
    return gr.update(visible=False, value="")


def render():
    """Render the auth section.

    Returns
    -------
    section, login_email, login_password, login_btn, login_msg,
    login_email_err, login_password_err
    """
    with gr.Group(elem_id="auth-section", visible=True) as section:
        with gr.Column(elem_id="auth-card"):
            gr.HTML(
                "<h2 style='text-align:center;color:#1e2d45 !important;margin:0 0 4px 0;"
                "font-size:1.4rem;font-weight:700;'>ServiceFlow AI</h2>"
                "<p style='text-align:center;color:#64748b;font-size:0.88rem;"
                "margin:0 0 20px 0;'>Log in or create a free account to get started</p>"
            )
            with gr.Tabs(elem_id="auth-tabs") as auth_tabs:

                # ── Log In tab ────────────────────────────────────────────────
                with gr.Tab("Log In"):
                    login_email = gr.Textbox(
                        label="Email Address",
                        placeholder="you@example.com",
                        elem_id="login-email-input",
                    )
                    login_email_err = gr.HTML("", visible=False, elem_id="err-login-email")

                    login_password = gr.Textbox(
                        label="Password",
                        placeholder="••••••••",
                        type="password",
                        elem_id="login-pw-input",
                    )
                    login_password_err = gr.HTML("", visible=False, elem_id="err-login-pw")

                    login_btn = gr.Button(
                        "Log In", variant="primary", elem_id="auth-login-btn"
                    )
                    login_msg = gr.HTML("", visible=False, elem_id="auth-login-msg")

                # ── Create Account tab ────────────────────────────────────────
                with gr.Tab("Create Account"):
                    with gr.Row():
                        with gr.Column(scale=1, min_width=0):
                            reg_name = gr.Textbox(
                                label="Full Name",
                                placeholder="Jane Smith",
                                elem_id="reg-name-input",
                            )
                            reg_name_err = gr.HTML("", visible=False, elem_id="err-reg-name")
                        with gr.Column(scale=1, min_width=0):
                            reg_business = gr.Textbox(
                                label="Business Name",
                                placeholder="Sparkle & Shine Cleaning",
                                elem_id="reg-biz-input",
                            )
                            reg_business_err = gr.HTML("", visible=False, elem_id="err-reg-biz")

                    with gr.Row():
                        with gr.Column(scale=1, min_width=0):
                            reg_email = gr.Textbox(
                                label="Email Address",
                                placeholder="you@example.com",
                                elem_id="reg-email-input",
                            )
                            reg_email_err = gr.HTML("", visible=False, elem_id="err-reg-email")
                        with gr.Column(scale=1, min_width=0):
                            reg_contact = gr.Textbox(
                                label="Contact Number",
                                placeholder="+1 555 000 0000",
                                elem_id="reg-contact-input",
                            )
                            reg_contact_err = gr.HTML("", visible=False, elem_id="err-reg-contact")

                    reg_password = gr.Textbox(
                        label="Password",
                        placeholder="Minimum 8 characters",
                        type="password",
                        elem_id="reg-pw-input",
                    )
                    reg_password_err = gr.HTML("", visible=False, elem_id="err-reg-pw")

                    reg_confirm = gr.Textbox(
                        label="Confirm Password",
                        placeholder="Repeat your password",
                        type="password",
                        elem_id="reg-confirm-input",
                    )
                    reg_confirm_err = gr.HTML("", visible=False, elem_id="err-reg-confirm")

                    reg_btn = gr.Button(
                        "Create Account", variant="primary", elem_id="auth-reg-btn"
                    )
                    reg_msg = gr.HTML("", visible=False, elem_id="auth-reg-msg")

    # ── Registration handler ─────────────────────────────────────────────────
    def _handle_register(name, business, email, contact, password, confirm):
        e: dict[str, str] = {}

        if not name.strip():
            e["name"] = "Full name is required."
        if not business.strip():
            e["business"] = "Business name is required."
        if not email.strip():
            e["email"] = "Email address is required."
        elif not _EMAIL_RE.match(email.strip()):
            e["email"] = "Please enter a valid email address (e.g. you@example.com)."
        if not contact.strip():
            e["contact"] = "Contact number is required."
        if not password:
            e["password"] = "Password is required."
        elif len(password) < 8:
            e["password"] = "Password must be at least 8 characters long."
        if not confirm:
            e["confirm"] = "Please confirm your password."
        elif password and password != confirm:
            e["confirm"] = "Passwords do not match. Please re-enter."

        # Validation failed — show field errors, no tab switch
        if e:
            return (
                _field_err(e.get("name", "")),
                _field_err(e.get("business", "")),
                _field_err(e.get("email", "")),
                _field_err(e.get("contact", "")),
                _field_err(e.get("password", "")),
                _field_err(e.get("confirm", "")),
                gr.update(visible=False, value=""),
                gr.update(),                          # auth_tabs — no change
                gr.update(),                          # login_email — no change
            )

        ok, msg = register_user(
            name.strip(), business.strip(), email.strip().lower(), contact.strip(), password
        )

        if ok:
            return (
                _field_err(""), _field_err(""), _field_err(""),
                _field_err(""), _field_err(""), _field_err(""),
                gr.update(visible=False, value=""),
                gr.update(selected="Log In"),                   # switch to Log In tab
                gr.update(value=email.strip().lower()),         # pre-fill email field
            )

        # Server-side error (duplicate email, etc.)
        email_field_err = _field_err(msg) if "email" in msg.lower() else _field_err("")
        return (
            _field_err(""), _field_err(""), email_field_err,
            _field_err(""), _field_err(""), _field_err(""),
            gr.update(
                visible=True,
                value=f'<div style="{_ERROR_BOX}">{msg}</div>',
            ),
            gr.update(),   # auth_tabs — no change
            gr.update(),   # login_email — no change
        )

    _reg_outputs = [
        reg_name_err, reg_business_err, reg_email_err, reg_contact_err,
        reg_password_err, reg_confirm_err, reg_msg,
        auth_tabs,    # enables programmatic tab switching
        login_email,  # pre-fills email on success
    ]
    reg_btn.click(
        fn=_handle_register,
        inputs=[reg_name, reg_business, reg_email, reg_contact, reg_password, reg_confirm],
        outputs=_reg_outputs,
    )

    return (
        section,
        login_email,
        login_password,
        login_btn,
        login_msg,
        login_email_err,
        login_password_err,
    )
