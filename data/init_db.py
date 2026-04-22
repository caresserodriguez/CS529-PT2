"""
Initialize the ServiceFlow AI SQLite database.
Creates the full schema and seeds all tables from existing data files.

Run from the project root:
    python data/init_db.py
"""

import json
import re
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads" / "current_business"
CUSTOMERS_DIR = PROJECT_ROOT / "data" / "customers"
DB_PATH = PROJECT_ROOT / "data" / "serviceflow.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────

SCHEMA = """
-- COMPANY PROFILE
CREATE TABLE IF NOT EXISTS company_profile (
    id                      INTEGER PRIMARY KEY,
    business_name           TEXT NOT NULL,
    business_type           TEXT,
    standard_service_model  TEXT,
    minimum_charge          REAL,
    pricing_model           TEXT,
    pricing_unit            TEXT,
    minimum_booking_policy  TEXT
);
CREATE TABLE IF NOT EXISTS company_operating_hours (
    id          INTEGER PRIMARY KEY,
    day_range   TEXT,
    hours       TEXT
);
CREATE TABLE IF NOT EXISTS company_service_categories (
    id          INTEGER PRIMARY KEY,
    category    TEXT
);
CREATE TABLE IF NOT EXISTS company_size_tiers (
    id      INTEGER PRIMARY KEY,
    tier    TEXT
);
CREATE TABLE IF NOT EXISTS company_notes (
    id      INTEGER PRIMARY KEY,
    note    TEXT
);

-- SERVICES
CREATE TABLE IF NOT EXISTS services (
    id                  INTEGER PRIMARY KEY,
    service_name        TEXT UNIQUE NOT NULL,
    category            TEXT,
    description         TEXT,
    complexity_level    TEXT,
    notes               TEXT,
    pricing_unit        TEXT
);
CREATE TABLE IF NOT EXISTS service_includes (
    id          INTEGER PRIMARY KEY,
    service_id  INTEGER NOT NULL REFERENCES services(id),
    item        TEXT
);
CREATE TABLE IF NOT EXISTS service_excludes (
    id          INTEGER PRIMARY KEY,
    service_id  INTEGER NOT NULL REFERENCES services(id),
    item        TEXT
);
CREATE TABLE IF NOT EXISTS service_addons (
    id          INTEGER PRIMARY KEY,
    service_id  INTEGER NOT NULL REFERENCES services(id),
    addon       TEXT
);
CREATE TABLE IF NOT EXISTS service_duration_tiers (
    id          INTEGER PRIMARY KEY,
    service_id  INTEGER NOT NULL REFERENCES services(id),
    tier_name   TEXT,
    hours       REAL
);

-- PRICING
CREATE TABLE IF NOT EXISTS pricing_rules (
    id          INTEGER PRIMARY KEY,
    rule_name   TEXT UNIQUE,
    value       REAL,
    unit        TEXT
);
CREATE TABLE IF NOT EXISTS service_pricing (
    id              INTEGER PRIMARY KEY,
    service_name    TEXT,
    tier_name       TEXT,
    price           REAL
);
CREATE TABLE IF NOT EXISTS addon_pricing (
    id          INTEGER PRIMARY KEY,
    addon_name  TEXT UNIQUE,
    price       REAL
);
CREATE TABLE IF NOT EXISTS internal_cost_factors (
    id              INTEGER PRIMARY KEY,
    factor_name     TEXT UNIQUE,
    value           REAL,
    unit            TEXT
);
CREATE TABLE IF NOT EXISTS profit_thresholds (
    id              INTEGER PRIMARY KEY,
    threshold_name  TEXT UNIQUE,
    value           REAL
);
CREATE TABLE IF NOT EXISTS pricing_notes (
    id      INTEGER PRIMARY KEY,
    section TEXT,
    note    TEXT
);

-- BUSINESS POLICIES
CREATE TABLE IF NOT EXISTS business_policies (
    id      INTEGER PRIMARY KEY,
    section TEXT,
    content TEXT
);

-- JOB COMPLEXITY
CREATE TABLE IF NOT EXISTS job_complexity_levels (
    id          INTEGER PRIMARY KEY,
    level       TEXT UNIQUE,
    description TEXT
);
CREATE TABLE IF NOT EXISTS job_complexity_examples (
    id          INTEGER PRIMARY KEY,
    level_id    INTEGER NOT NULL REFERENCES job_complexity_levels(id),
    example     TEXT
);
CREATE TABLE IF NOT EXISTS job_complexity_indicators (
    id          INTEGER PRIMARY KEY,
    level_id    INTEGER NOT NULL REFERENCES job_complexity_levels(id),
    indicator   TEXT
);
CREATE TABLE IF NOT EXISTS job_complexity_notes (
    id      INTEGER PRIMARY KEY,
    note    TEXT
);

-- RISK FLAGS
CREATE TABLE IF NOT EXISTS risk_flags (
    id          INTEGER PRIMARY KEY,
    flag        TEXT UNIQUE,
    description TEXT,
    impact      TEXT
);
CREATE TABLE IF NOT EXISTS risk_flag_notes (
    id      INTEGER PRIMARY KEY,
    note    TEXT
);

-- STAFFING
CREATE TABLE IF NOT EXISTS staff_groups (
    id          INTEGER PRIMARY KEY,
    group_name  TEXT,
    count       INTEGER
);
CREATE TABLE IF NOT EXISTS staff_capabilities (
    id          INTEGER PRIMARY KEY,
    group_id    INTEGER NOT NULL REFERENCES staff_groups(id),
    capability  TEXT
);
CREATE TABLE IF NOT EXISTS staffing_meta (
    id      INTEGER PRIMARY KEY,
    key     TEXT UNIQUE,
    value   TEXT
);
CREATE TABLE IF NOT EXISTS crew_deployment_rules (
    id          INTEGER PRIMARY KEY,
    job_type    TEXT UNIQUE,
    rule        TEXT
);
CREATE TABLE IF NOT EXISTS staffing_notes (
    id      INTEGER PRIMARY KEY,
    note    TEXT
);

-- SCHEDULE
CREATE TABLE IF NOT EXISTS schedule_slots (
    id          INTEGER PRIMARY KEY,
    slot_name   TEXT UNIQUE,
    status      TEXT,
    notes       TEXT
);
CREATE TABLE IF NOT EXISTS booking_lead_times (
    id              INTEGER PRIMARY KEY,
    service_type    TEXT UNIQUE,
    lead_time       TEXT
);
CREATE TABLE IF NOT EXISTS high_demand_periods (
    id      INTEGER PRIMARY KEY,
    period  TEXT
);
CREATE TABLE IF NOT EXISTS schedule_meta (
    id      INTEGER PRIMARY KEY,
    key     TEXT UNIQUE,
    value   TEXT
);
CREATE TABLE IF NOT EXISTS schedule_notes (
    id      INTEGER PRIMARY KEY,
    note    TEXT
);

-- SERVICE AREA
CREATE TABLE IF NOT EXISTS service_zones (
    id          INTEGER PRIMARY KEY,
    zone_name   TEXT,
    zone_type   TEXT
);
CREATE TABLE IF NOT EXISTS travel_policy (
    id                      INTEGER PRIMARY KEY,
    zone_type               TEXT UNIQUE,
    surcharge_amount        REAL,
    surcharge_note          TEXT,
    typical_travel_minutes  INTEGER
);
CREATE TABLE IF NOT EXISTS service_area_notes (
    id      INTEGER PRIMARY KEY,
    note    TEXT
);

-- EQUIPMENT
CREATE TABLE IF NOT EXISTS equipment (
    id                  INTEGER PRIMARY KEY,
    equipment_name      TEXT UNIQUE,
    status              TEXT,
    condition_status    TEXT,
    units_available     INTEGER,
    notes               TEXT
);
CREATE TABLE IF NOT EXISTS equipment_notes (
    id      INTEGER PRIMARY KEY,
    note    TEXT
);

-- RESOURCES
CREATE TABLE IF NOT EXISTS resources (
    id              INTEGER PRIMARY KEY,
    resource_name   TEXT UNIQUE,
    status          TEXT,
    notes           TEXT
);
CREATE TABLE IF NOT EXISTS resource_meta (
    id      INTEGER PRIMARY KEY,
    key     TEXT UNIQUE,
    value   TEXT
);
CREATE TABLE IF NOT EXISTS resource_notes (
    id      INTEGER PRIMARY KEY,
    note    TEXT
);

-- CUSTOMERS
CREATE TABLE IF NOT EXISTS customers (
    id                      INTEGER PRIMARY KEY,
    email                   TEXT UNIQUE NOT NULL,
    repeat_customer         INTEGER DEFAULT 0,
    customer_since          TEXT,
    property_type           TEXT,
    property_size           TEXT,
    location_zone           TEXT,
    service_frequency       TEXT,
    preferred_schedule      TEXT,
    preferred_contact_style TEXT
);
CREATE TABLE IF NOT EXISTS customer_past_services (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    service_name TEXT
);
CREATE TABLE IF NOT EXISTS customer_common_requests (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    request     TEXT
);
CREATE TABLE IF NOT EXISTS customer_notes (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    note        TEXT
);
"""


# ─────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────

def seed_company_profile(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "company_profile.json").read_text())
    pricing = data["general_pricing_style"]
    conn.execute(
        """INSERT OR REPLACE INTO company_profile
           (id, business_name, business_type, standard_service_model,
            minimum_charge, pricing_model, pricing_unit, minimum_booking_policy)
           VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["business_name"],
            data["business_type"],
            data["standard_service_model"],
            pricing["minimum_charge"],
            pricing["model"],
            pricing.get("pricing_unit"),
            data["minimum_booking_policy"],
        ),
    )
    for day_range, hours in data["operating_hours"].items():
        conn.execute(
            "INSERT INTO company_operating_hours (day_range, hours) VALUES (?, ?)",
            (day_range, hours),
        )
    for cat in data["service_categories"]:
        conn.execute("INSERT INTO company_service_categories (category) VALUES (?)", (cat,))
    for tier in pricing.get("size_tiers", []):
        conn.execute("INSERT INTO company_size_tiers (tier) VALUES (?)", (tier,))
    for note in data.get("general_notes", []):
        conn.execute("INSERT INTO company_notes (note) VALUES (?)", (note,))


def seed_service_catalogue(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "service_catalogue.json").read_text())
    for svc in data["services"]:
        conn.execute(
            """INSERT OR REPLACE INTO services
               (service_name, category, description, complexity_level, notes, pricing_unit)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                svc["service_name"],
                svc.get("category"),
                svc.get("description"),
                svc.get("complexity_level"),
                svc.get("notes"),
                svc.get("pricing_unit"),
            ),
        )
        service_id = conn.execute(
            "SELECT id FROM services WHERE service_name = ?", (svc["service_name"],)
        ).fetchone()[0]
        for item in svc.get("includes", []):
            conn.execute(
                "INSERT INTO service_includes (service_id, item) VALUES (?, ?)", (service_id, item)
            )
        for item in svc.get("excludes", []):
            conn.execute(
                "INSERT INTO service_excludes (service_id, item) VALUES (?, ?)", (service_id, item)
            )
        for addon in svc.get("common_add_ons", []):
            conn.execute(
                "INSERT INTO service_addons (service_id, addon) VALUES (?, ?)", (service_id, addon)
            )
        for tier_name, hours in svc.get("typical_duration_hours", {}).items():
            conn.execute(
                "INSERT INTO service_duration_tiers (service_id, tier_name, hours) VALUES (?, ?, ?)",
                (service_id, tier_name, hours),
            )


def seed_pricing_data(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "pricing_data.json").read_text())

    rule_units = {
        "minimum_charge": "dollars",
        "base_markup_percent": "percent",
        "urgent_surcharge_percent": "percent",
        "condition_surcharge_percent": "percent",
        "after_hours_surcharge_percent": "percent",
        "extended_zone_surcharge_flat": "flat",
    }
    rules = data["pricing_rules"]
    for key, unit in rule_units.items():
        if key in rules:
            conn.execute(
                "INSERT OR REPLACE INTO pricing_rules (rule_name, value, unit) VALUES (?, ?, ?)",
                (key, rules[key], unit),
            )
    for note in rules.get("notes", []):
        conn.execute(
            "INSERT INTO pricing_notes (section, note) VALUES (?, ?)", ("pricing_rules", note)
        )

    cost_units = {
        "labor_rate_per_hour": "dollars_per_hour",
        "specialist_labor_rate_per_hour": "dollars_per_hour",
        "average_travel_cost_primary_zone": "dollars",
        "average_travel_cost_extended_zone": "dollars",
        "cleaning_supplies_cost_per_visit": "dollars",
        "steam_cleaner_operating_cost_per_hour": "dollars_per_hour",
    }
    costs = data["internal_cost_factors"]
    for key, unit in cost_units.items():
        if key in costs:
            conn.execute(
                "INSERT OR REPLACE INTO internal_cost_factors (factor_name, value, unit) VALUES (?, ?, ?)",
                (key, costs[key], unit),
            )
    for note in costs.get("notes", []):
        conn.execute(
            "INSERT INTO pricing_notes (section, note) VALUES (?, ?)",
            ("internal_cost_factors", note),
        )

    thresholds = data["profit_thresholds"]
    for key in ["minimum_acceptable_margin_percent", "target_margin_percent", "flag_below_margin_percent"]:
        if key in thresholds:
            conn.execute(
                "INSERT OR REPLACE INTO profit_thresholds (threshold_name, value) VALUES (?, ?)",
                (key, thresholds[key]),
            )
    for note in thresholds.get("notes", []):
        conn.execute(
            "INSERT INTO pricing_notes (section, note) VALUES (?, ?)",
            ("profit_thresholds", note),
        )

    for svc in data.get("services", []):
        name = svc["service_name"]
        if "price_tiers" in svc:
            for tier_name, price in svc["price_tiers"].items():
                conn.execute(
                    "INSERT INTO service_pricing (service_name, tier_name, price) VALUES (?, ?, ?)",
                    (name, tier_name, price),
                )
        elif "base_price_per_room" in svc:
            conn.execute(
                "INSERT INTO service_pricing (service_name, tier_name, price) VALUES (?, ?, ?)",
                (name, "per_room", svc["base_price_per_room"]),
            )
            for addon_name, addon_price in svc.get("add_ons", {}).items():
                conn.execute(
                    "INSERT OR REPLACE INTO addon_pricing (addon_name, price) VALUES (?, ?)",
                    (f"{name}_{addon_name}", addon_price),
                )
        elif "price_tiers" not in svc and "base_price_per_room" not in svc:
            for tier_name in ["small_property", "large_property", "small_office", "medium_office", "large_office"]:
                if tier_name in svc:
                    conn.execute(
                        "INSERT INTO service_pricing (service_name, tier_name, price) VALUES (?, ?, ?)",
                        (name, tier_name, svc[tier_name]),
                    )

    for addon_name, price in data.get("add_on_pricing", {}).items():
        conn.execute(
            "INSERT OR REPLACE INTO addon_pricing (addon_name, price) VALUES (?, ?)",
            (addon_name, price),
        )


def seed_business_policies(conn: sqlite3.Connection) -> None:
    text = (UPLOADS_DIR / "business_policies.txt").read_text()
    sections = re.split(r"\n(?=[A-Z][A-Z &/\-]+\n)", text.strip())
    for section in sections:
        lines = section.strip().split("\n")
        if not lines:
            continue
        section_name = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        conn.execute(
            "INSERT INTO business_policies (section, content) VALUES (?, ?)",
            (section_name, content),
        )


def seed_job_complexity(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "job_complexity.json").read_text())
    for level, details in data["complexity_framework"].items():
        conn.execute(
            "INSERT OR REPLACE INTO job_complexity_levels (level, description) VALUES (?, ?)",
            (level, details["description"]),
        )
        level_id = conn.execute(
            "SELECT id FROM job_complexity_levels WHERE level = ?", (level,)
        ).fetchone()[0]
        for ex in details.get("examples", []):
            conn.execute(
                "INSERT INTO job_complexity_examples (level_id, example) VALUES (?, ?)",
                (level_id, ex),
            )
        for ind in details.get("typical_indicators", []):
            conn.execute(
                "INSERT INTO job_complexity_indicators (level_id, indicator) VALUES (?, ?)",
                (level_id, ind),
            )
    for note in data.get("notes", []):
        conn.execute("INSERT INTO job_complexity_notes (note) VALUES (?)", (note,))


def seed_risk_flags(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "risk_flags.json").read_text())
    for flag in data["risk_flags"]:
        if isinstance(flag, dict):
            conn.execute(
                "INSERT OR REPLACE INTO risk_flags (flag, description, impact) VALUES (?, ?, ?)",
                (flag["flag"], flag.get("description"), flag.get("impact")),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO risk_flags (flag, description, impact) VALUES (?, ?, ?)",
                (flag, None, None),
            )
    for note in data.get("notes", []):
        conn.execute("INSERT INTO risk_flag_notes (note) VALUES (?)", (note,))


def seed_staffing(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "staffing_availability.json").read_text())
    status = data["staffing_status"]

    for group_name, group_data in status.get("crew_breakdown", {}).items():
        conn.execute(
            "INSERT INTO staff_groups (group_name, count) VALUES (?, ?)",
            (group_name, group_data["count"]),
        )
        group_id = conn.execute(
            "SELECT id FROM staff_groups WHERE group_name = ?", (group_name,)
        ).fetchone()[0]
        for cap in group_data.get("capabilities", []):
            conn.execute(
                "INSERT INTO staff_capabilities (group_id, capability) VALUES (?, ?)",
                (group_id, cap),
            )

    for key in [
        "total_staff_available",
        "carpet_steam_trained_staff",
        "high_access_trained_staff",
        "overtime_likelihood",
        "staffing_pressure",
    ]:
        if key in status:
            conn.execute(
                "INSERT OR REPLACE INTO staffing_meta (key, value) VALUES (?, ?)",
                (key, str(status[key])),
            )

    for note in status.get("notes", []):
        conn.execute("INSERT INTO staffing_notes (note) VALUES (?)", (note,))

    for job_type, rule in data.get("crew_deployment_rules", {}).items():
        conn.execute(
            "INSERT OR REPLACE INTO crew_deployment_rules (job_type, rule) VALUES (?, ?)",
            (job_type, rule),
        )
    for note in data.get("notes", []):
        conn.execute("INSERT INTO staffing_notes (note) VALUES (?)", (note,))


def seed_schedule_capacity(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "schedule_capacity.json").read_text())
    cap = data["schedule_capacity"]

    for key in ["current_capacity_status", "weekday_capacity", "same_day_capacity", "next_day_capacity"]:
        if key in cap:
            conn.execute(
                "INSERT OR REPLACE INTO schedule_meta (key, value) VALUES (?, ?)",
                (key, str(cap[key])),
            )

    weekend = cap.get("weekend_capacity", {})
    if isinstance(weekend, dict):
        for day, val in weekend.items():
            conn.execute(
                "INSERT OR REPLACE INTO schedule_meta (key, value) VALUES (?, ?)",
                (f"weekend_{day}", val),
            )

    recurring = cap.get("recurring_contract_slots", {})
    if recurring:
        conn.execute(
            "INSERT OR REPLACE INTO schedule_meta (key, value) VALUES (?, ?)",
            ("recurring_contract_status", recurring.get("status")),
        )

    for slot_name, slot_data in cap.get("daily_job_slots", {}).items():
        conn.execute(
            "INSERT OR REPLACE INTO schedule_slots (slot_name, status, notes) VALUES (?, ?, ?)",
            (slot_name, slot_data.get("status"), slot_data.get("notes")),
        )

    for period in cap.get("high_demand_periods", []):
        conn.execute("INSERT INTO high_demand_periods (period) VALUES (?)", (period,))

    for service_type, lead_time in data.get("booking_lead_time_guidelines", {}).items():
        conn.execute(
            "INSERT OR REPLACE INTO booking_lead_times (service_type, lead_time) VALUES (?, ?)",
            (service_type, lead_time),
        )

    for note in data.get("notes", []):
        conn.execute("INSERT INTO schedule_notes (note) VALUES (?)", (note,))


def seed_service_area(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "service_area.json").read_text())
    area = data["service_area"]

    for zone in area.get("primary_zones", []):
        conn.execute(
            "INSERT INTO service_zones (zone_name, zone_type) VALUES (?, ?)", (zone, "primary")
        )
    for zone in area.get("extended_zones", []):
        conn.execute(
            "INSERT INTO service_zones (zone_name, zone_type) VALUES (?, ?)", (zone, "extended")
        )
    for zone in area.get("out_of_area", []):
        conn.execute(
            "INSERT INTO service_zones (zone_name, zone_type) VALUES (?, ?)", (zone, "out_of_area")
        )

    policy = area.get("travel_policy", {})
    times = area.get("typical_travel_time_minutes", {})
    conn.execute(
        "INSERT OR REPLACE INTO travel_policy (zone_type, surcharge_amount, surcharge_note, typical_travel_minutes) VALUES (?, ?, ?, ?)",
        ("primary", policy.get("primary_zone_surcharge", 0), None, times.get("primary_zones")),
    )
    conn.execute(
        "INSERT OR REPLACE INTO travel_policy (zone_type, surcharge_amount, surcharge_note, typical_travel_minutes) VALUES (?, ?, ?, ?)",
        ("extended", policy.get("extended_zone_surcharge", 50), None, times.get("extended_zones")),
    )
    conn.execute(
        "INSERT OR REPLACE INTO travel_policy (zone_type, surcharge_amount, surcharge_note, typical_travel_minutes) VALUES (?, ?, ?, ?)",
        ("out_of_area", None, policy.get("out_of_area"), None),
    )

    for note in data.get("notes", []):
        conn.execute("INSERT INTO service_area_notes (note) VALUES (?)", (note,))
    for note in area.get("cleaning_specific_notes", []):
        conn.execute("INSERT INTO service_area_notes (note) VALUES (?)", (note,))


def seed_equipment(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "equipment_readiness.json").read_text())
    for eq_name, eq_data in data["equipment_readiness"].items():
        conn.execute(
            """INSERT OR REPLACE INTO equipment
               (equipment_name, status, condition_status, units_available, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (
                eq_name,
                eq_data.get("status"),
                eq_data.get("condition"),
                eq_data.get("units_available"),
                eq_data.get("notes"),
            ),
        )
    for note in data.get("notes", []):
        conn.execute("INSERT INTO equipment_notes (note) VALUES (?)", (note,))


def seed_resources(conn: sqlite3.Connection) -> None:
    data = json.loads((UPLOADS_DIR / "resource_availability.json").read_text())
    for res_name, res_data in data["resource_availability"].items():
        if res_name == "supply_risk":
            conn.execute(
                "INSERT OR REPLACE INTO resource_meta (key, value) VALUES (?, ?)",
                ("supply_risk", res_data),
            )
        elif isinstance(res_data, dict):
            conn.execute(
                "INSERT OR REPLACE INTO resources (resource_name, status, notes) VALUES (?, ?, ?)",
                (res_name, res_data.get("status"), res_data.get("notes")),
            )
    for note in data.get("notes", []):
        conn.execute("INSERT INTO resource_notes (note) VALUES (?)", (note,))


def seed_customers(conn: sqlite3.Connection) -> None:
    data = json.loads((CUSTOMERS_DIR / "customer_history.json").read_text())
    for email, record in data["customers"].items():
        conn.execute(
            """INSERT OR REPLACE INTO customers
               (email, repeat_customer, customer_since, property_type, property_size,
                location_zone, service_frequency, preferred_schedule, preferred_contact_style)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                email.lower(),
                1 if record.get("repeat_customer") else 0,
                record.get("customer_since"),
                record.get("property_type"),
                record.get("property_size"),
                record.get("location_zone"),
                record.get("service_frequency"),
                record.get("preferred_schedule"),
                record.get("preferred_contact_style"),
            ),
        )
        customer_id = conn.execute(
            "SELECT id FROM customers WHERE email = ?", (email.lower(),)
        ).fetchone()[0]
        for svc in record.get("past_services", []):
            conn.execute(
                "INSERT INTO customer_past_services (customer_id, service_name) VALUES (?, ?)",
                (customer_id, svc),
            )
        for req in record.get("common_requests", []):
            conn.execute(
                "INSERT INTO customer_common_requests (customer_id, request) VALUES (?, ?)",
                (customer_id, req),
            )
        for note in record.get("notes", []):
            conn.execute(
                "INSERT INTO customer_notes (customer_id, note) VALUES (?, ?)",
                (customer_id, note),
            )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database.")

    conn = get_connection()

    print("Creating schema...")
    conn.executescript(SCHEMA)
    conn.commit()

    steps = [
        ("Company profile", seed_company_profile),
        ("Service catalogue", seed_service_catalogue),
        ("Pricing data", seed_pricing_data),
        ("Business policies", seed_business_policies),
        ("Job complexity", seed_job_complexity),
        ("Risk flags", seed_risk_flags),
        ("Staffing", seed_staffing),
        ("Schedule capacity", seed_schedule_capacity),
        ("Service area", seed_service_area),
        ("Equipment", seed_equipment),
        ("Resources", seed_resources),
        ("Customers", seed_customers),
    ]

    for label, fn in steps:
        print(f"Seeding {label}...")
        fn(conn)
        conn.commit()

    conn.close()
    print(f"\nDatabase initialized at {DB_PATH}")
