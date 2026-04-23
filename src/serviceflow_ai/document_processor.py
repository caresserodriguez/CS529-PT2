"""
Business document processor for the ServiceFlow AI admin panel.
Accepts an uploaded file and a document type, uses Claude to extract
structured data, and writes the result into the SQLite database.
"""

import json
import sqlite3
from pathlib import Path

from openai import OpenAI
import docx
import pdfplumber

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "serviceflow.db"

_client = OpenAI()

# ─── Extraction prompts ───────────────────────────────────────────────────────

_PROMPTS = {
    "Pricing & Cost Factors": """
You are extracting pricing data from a business document for a small cleaning company.
Extract ALL pricing information present and return it as JSON using this exact structure.
Only include fields explicitly stated in the document — use null for anything not mentioned.

{
  "pricing_rules": {
    "minimum_charge": <number or null>,
    "base_markup_percent": <number or null>,
    "urgent_surcharge_percent": <number or null>,
    "condition_surcharge_percent": <number or null>,
    "after_hours_surcharge_percent": <number or null>,
    "extended_zone_surcharge_flat": <number or null>
  },
  "service_pricing": [
    { "service_name": "...", "tier_name": "...", "price": <number> }
  ],
  "addon_pricing": { "<addon_name>": <price> },
  "internal_cost_factors": { "<factor_name>": <value> },
  "profit_thresholds": {
    "minimum_acceptable_margin_percent": <number or null>,
    "target_margin_percent": <number or null>,
    "flag_below_margin_percent": <number or null>
  }
}

Return ONLY valid JSON. No explanation or markdown fences.
""",

    "Service Catalogue": """
You are extracting service definitions from a business document for a small cleaning company.
Extract ALL services described and return them as JSON.
Only include services explicitly defined in the document.

{
  "services": [
    {
      "service_name": "...",
      "category": "...",
      "description": "...",
      "includes": ["..."],
      "excludes": ["..."],
      "common_add_ons": ["..."],
      "complexity_level": "simple|moderate|complex",
      "notes": "...",
      "typical_duration_hours": { "<tier_name>": <hours> }
    }
  ]
}

Return ONLY valid JSON. No explanation or markdown fences.
""",

    "Business Policies": """
You are extracting business policy information from a document for a small cleaning company.
Organise all policies by section and return as JSON.
Preserve the full text of each section. Infer sensible section names if headings are unclear.

{
  "policies": [
    { "section": "SECTION HEADING IN CAPS", "content": "full policy text for this section" }
  ]
}

Return ONLY valid JSON. No explanation or markdown fences.
""",

    "Equipment & Resources": """
You are extracting equipment and supply availability from a document for a small cleaning company.
Return as JSON. Only include items explicitly mentioned.

{
  "equipment": [
    {
      "equipment_name": "...",
      "status": "available|limited|unavailable",
      "condition_status": "good|fair|under_maintenance",
      "units_available": <number or null>,
      "notes": "..."
    }
  ],
  "resources": [
    { "resource_name": "...", "status": "adequate|limited|unavailable", "notes": "..." }
  ],
  "supply_risk": "low|low_to_moderate|moderate|high|null"
}

Return ONLY valid JSON. No explanation or markdown fences.
""",

    "Staffing": """
You are extracting staffing information from a document for a small cleaning company.
Return as JSON. Only include information explicitly present in the document.

{
  "staff_groups": [
    { "group_name": "...", "count": <number>, "capabilities": ["..."] }
  ],
  "meta": {
    "total_staff_available": <number or null>,
    "carpet_steam_trained_staff": <number or null>,
    "high_access_trained_staff": <number or null>,
    "overtime_likelihood": "low|moderate|high|null",
    "staffing_pressure": "low|moderate|high|null"
  },
  "crew_deployment_rules": { "<job_type>": "<rule>" }
}

Return ONLY valid JSON. No explanation or markdown fences.
""",
}

DOCUMENT_TYPES = list(_PROMPTS.keys())


# ─── File reader ──────────────────────────────────────────────────────────────

def _read_file(file) -> str:
    if file is None:
        return ""
    path = file.name if hasattr(file, "name") else str(file)
    ext = path.rsplit(".", 1)[-1].lower()
    try:
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
    except Exception as exc:
        return f"[Could not read file: {exc}]"
    return ""


# ─── OpenAI extraction ───────────────────────────────────────────────────────

def _extract(document_text: str, document_type: str) -> dict:
    prompt = _PROMPTS[document_type]
    response = _client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"{prompt}\n\nDOCUMENT:\n{document_text}",
            }
        ],
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ─── DB update handlers ───────────────────────────────────────────────────────

def _update_pricing(conn: sqlite3.Connection, data: dict) -> list[str]:
    log = []
    for key, value in data.get("pricing_rules", {}).items():
        if value is not None:
            conn.execute(
                """INSERT OR REPLACE INTO pricing_rules (rule_name, value, unit)
                   VALUES (?, ?, COALESCE((SELECT unit FROM pricing_rules WHERE rule_name = ?), 'unknown'))""",
                (key, value, key),
            )
            log.append(f"Pricing rule: **{key}** = {value}")

    for row in data.get("service_pricing", []):
        conn.execute(
            "INSERT OR REPLACE INTO service_pricing (service_name, tier_name, price) VALUES (?, ?, ?)",
            (row["service_name"], row["tier_name"], row["price"]),
        )
        log.append(f"Service price: **{row['service_name']}** / {row['tier_name']} = ${row['price']}")

    for name, price in data.get("addon_pricing", {}).items():
        conn.execute(
            "INSERT OR REPLACE INTO addon_pricing (addon_name, price) VALUES (?, ?)",
            (name, price),
        )
        log.append(f"Add-on price: **{name}** = ${price}")

    for key, value in data.get("internal_cost_factors", {}).items():
        conn.execute(
            """INSERT OR REPLACE INTO internal_cost_factors (factor_name, value, unit)
               VALUES (?, ?, COALESCE((SELECT unit FROM internal_cost_factors WHERE factor_name = ?), 'unknown'))""",
            (key, value, key),
        )
        log.append(f"Cost factor: **{key}** = {value}")

    for key, value in data.get("profit_thresholds", {}).items():
        if value is not None:
            conn.execute(
                "INSERT OR REPLACE INTO profit_thresholds (threshold_name, value) VALUES (?, ?)",
                (key, value),
            )
            log.append(f"Profit threshold: **{key}** = {value}%")

    return log


def _update_services(conn: sqlite3.Connection, data: dict) -> list[str]:
    log = []
    for svc in data.get("services", []):
        name = svc["service_name"]
        conn.execute(
            """INSERT INTO services (service_name, category, description, complexity_level, notes, pricing_unit)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(service_name) DO UPDATE SET
                 category = excluded.category,
                 description = excluded.description,
                 complexity_level = excluded.complexity_level,
                 notes = excluded.notes""",
            (
                name,
                svc.get("category"),
                svc.get("description"),
                svc.get("complexity_level"),
                svc.get("notes"),
                svc.get("pricing_unit"),
            ),
        )
        svc_id = conn.execute(
            "SELECT id FROM services WHERE service_name = ?", (name,)
        ).fetchone()[0]
        for table in ("service_includes", "service_excludes", "service_addons", "service_duration_tiers"):
            conn.execute(f"DELETE FROM {table} WHERE service_id = ?", (svc_id,))
        for item in svc.get("includes", []):
            conn.execute("INSERT INTO service_includes (service_id, item) VALUES (?, ?)", (svc_id, item))
        for item in svc.get("excludes", []):
            conn.execute("INSERT INTO service_excludes (service_id, item) VALUES (?, ?)", (svc_id, item))
        for addon in svc.get("common_add_ons", []):
            conn.execute("INSERT INTO service_addons (service_id, addon) VALUES (?, ?)", (svc_id, addon))
        for tier_name, hours in svc.get("typical_duration_hours", {}).items():
            conn.execute(
                "INSERT INTO service_duration_tiers (service_id, tier_name, hours) VALUES (?, ?, ?)",
                (svc_id, tier_name, hours),
            )
        log.append(f"Service upserted: **{name}**")
    return log


def _update_policies(conn: sqlite3.Connection, data: dict) -> list[str]:
    conn.execute("DELETE FROM business_policies")
    log = []
    for policy in data.get("policies", []):
        conn.execute(
            "INSERT INTO business_policies (section, content) VALUES (?, ?)",
            (policy["section"], policy["content"]),
        )
        log.append(f"Policy section: **{policy['section']}**")
    return log


def _update_equipment_resources(conn: sqlite3.Connection, data: dict) -> list[str]:
    log = []
    for eq in data.get("equipment", []):
        conn.execute(
            """INSERT OR REPLACE INTO equipment
               (equipment_name, status, condition_status, units_available, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (
                eq["equipment_name"],
                eq.get("status"),
                eq.get("condition_status"),
                eq.get("units_available"),
                eq.get("notes"),
            ),
        )
        log.append(f"Equipment: **{eq['equipment_name']}** — {eq.get('status')}")
    for res in data.get("resources", []):
        conn.execute(
            "INSERT OR REPLACE INTO resources (resource_name, status, notes) VALUES (?, ?, ?)",
            (res["resource_name"], res.get("status"), res.get("notes")),
        )
        log.append(f"Resource: **{res['resource_name']}** — {res.get('status')}")
    if data.get("supply_risk"):
        conn.execute(
            "INSERT OR REPLACE INTO resource_meta (key, value) VALUES (?, ?)",
            ("supply_risk", data["supply_risk"]),
        )
        log.append(f"Supply risk: **{data['supply_risk']}**")
    return log


def _update_staffing(conn: sqlite3.Connection, data: dict) -> list[str]:
    log = []
    if data.get("staff_groups"):
        conn.execute(
            "DELETE FROM staff_capabilities WHERE group_id IN (SELECT id FROM staff_groups)"
        )
        conn.execute("DELETE FROM staff_groups")
        for group in data["staff_groups"]:
            conn.execute(
                "INSERT INTO staff_groups (group_name, count) VALUES (?, ?)",
                (group["group_name"], group["count"]),
            )
            group_id = conn.execute(
                "SELECT id FROM staff_groups WHERE group_name = ?", (group["group_name"],)
            ).fetchone()[0]
            for cap in group.get("capabilities", []):
                conn.execute(
                    "INSERT INTO staff_capabilities (group_id, capability) VALUES (?, ?)",
                    (group_id, cap),
                )
            log.append(f"Staff group: **{group['group_name']}** ({group['count']} staff)")
    for key, value in data.get("meta", {}).items():
        if value is not None:
            conn.execute(
                "INSERT OR REPLACE INTO staffing_meta (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
            log.append(f"Staffing meta: **{key}** = {value}")
    for job_type, rule in data.get("crew_deployment_rules", {}).items():
        conn.execute(
            "INSERT OR REPLACE INTO crew_deployment_rules (job_type, rule) VALUES (?, ?)",
            (job_type, rule),
        )
        log.append(f"Crew rule updated: **{job_type}**")
    return log


_HANDLERS = {
    "Pricing & Cost Factors": _update_pricing,
    "Service Catalogue": _update_services,
    "Business Policies": _update_policies,
    "Equipment & Resources": _update_equipment_resources,
    "Staffing": _update_staffing,
}


# ─── Public entry point ───────────────────────────────────────────────────────

def process_business_document(file, document_type: str) -> str:
    if file is None:
        return "No file uploaded."
    if document_type not in _PROMPTS:
        return f"Unknown document type: {document_type}"

    document_text = _read_file(file)
    if not document_text:
        return "The uploaded file appears to be empty."
    if document_text.startswith("[Could not read"):
        return document_text

    try:
        extracted = _extract(document_text, document_type)
    except json.JSONDecodeError as e:
        return f"Could not parse the extracted data as JSON. Try uploading a cleaner document. Detail: {e}"
    except Exception as e:
        return f"Extraction failed: {e}"

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        log = _HANDLERS[document_type](conn, extracted)
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return f"Database update failed: {e}"
    conn.close()

    if not log:
        return (
            "Document processed but no matching data was found. "
            "Check that the document type selection matches the document content."
        )

    lines = [f"### {document_type} — Updated Successfully\n", f"**{len(log)} record(s) updated:**\n"]
    lines += [f"- {entry}" for entry in log]
    return "\n".join(lines)
