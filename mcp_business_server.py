import json
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Business Resource MCP Server")

DB_PATH = Path("data/serviceflow.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_error(operation: str, e: Exception) -> str:
    return json.dumps({"error": f"db_error_{operation}", "message": str(e)}, indent=2)


@mcp.tool()
def get_company_profile() -> str:
    try:
        conn = get_db()
        profile = dict(conn.execute("SELECT * FROM company_profile WHERE id = 1").fetchone())
        hours = {
            r["day_range"]: r["hours"]
            for r in conn.execute("SELECT day_range, hours FROM company_operating_hours").fetchall()
        }
        categories = [
            r["category"]
            for r in conn.execute("SELECT category FROM company_service_categories").fetchall()
        ]
        size_tiers = [
            r["tier"] for r in conn.execute("SELECT tier FROM company_size_tiers").fetchall()
        ]
        notes = [r["note"] for r in conn.execute("SELECT note FROM company_notes").fetchall()]
        conn.close()
        return json.dumps(
            {
                "business_name": profile["business_name"],
                "business_type": profile["business_type"],
                "service_categories": categories,
                "standard_service_model": profile["standard_service_model"],
                "operating_hours": hours,
                "general_pricing_style": {
                    "model": profile["pricing_model"],
                    "minimum_charge": profile["minimum_charge"],
                    "pricing_unit": profile["pricing_unit"],
                    "size_tiers": size_tiers,
                },
                "minimum_booking_policy": profile["minimum_booking_policy"],
                "general_notes": notes,
            },
            indent=2,
        )
    except Exception as e:
        return db_error("get_company_profile", e)


@mcp.tool()
def get_service_catalogue() -> str:
    try:
        conn = get_db()
        services_rows = conn.execute("SELECT * FROM services").fetchall()
        services = []
        for svc in services_rows:
            svc_id = svc["id"]
            includes = [
                r["item"]
                for r in conn.execute(
                    "SELECT item FROM service_includes WHERE service_id = ?", (svc_id,)
                ).fetchall()
            ]
            excludes = [
                r["item"]
                for r in conn.execute(
                    "SELECT item FROM service_excludes WHERE service_id = ?", (svc_id,)
                ).fetchall()
            ]
            addons = [
                r["addon"]
                for r in conn.execute(
                    "SELECT addon FROM service_addons WHERE service_id = ?", (svc_id,)
                ).fetchall()
            ]
            duration = {
                r["tier_name"]: r["hours"]
                for r in conn.execute(
                    "SELECT tier_name, hours FROM service_duration_tiers WHERE service_id = ?",
                    (svc_id,),
                ).fetchall()
            }
            services.append(
                {
                    "service_name": svc["service_name"],
                    "category": svc["category"],
                    "description": svc["description"],
                    "includes": includes,
                    "excludes": excludes,
                    "common_add_ons": addons,
                    "complexity_level": svc["complexity_level"],
                    "typical_duration_hours": duration,
                    "notes": svc["notes"],
                }
            )
        conn.close()
        return json.dumps({"services": services}, indent=2)
    except Exception as e:
        return db_error("get_service_catalogue", e)


@mcp.tool()
def get_pricing_data() -> str:
    try:
        conn = get_db()
        rules = {
            r["rule_name"]: r["value"]
            for r in conn.execute("SELECT rule_name, value FROM pricing_rules").fetchall()
        }
        rule_notes = [
            r["note"]
            for r in conn.execute(
                "SELECT note FROM pricing_notes WHERE section = 'pricing_rules'"
            ).fetchall()
        ]
        cost_factors = {
            r["factor_name"]: r["value"]
            for r in conn.execute("SELECT factor_name, value FROM internal_cost_factors").fetchall()
        }
        cost_notes = [
            r["note"]
            for r in conn.execute(
                "SELECT note FROM pricing_notes WHERE section = 'internal_cost_factors'"
            ).fetchall()
        ]
        thresholds = {
            r["threshold_name"]: r["value"]
            for r in conn.execute("SELECT threshold_name, value FROM profit_thresholds").fetchall()
        }
        threshold_notes = [
            r["note"]
            for r in conn.execute(
                "SELECT note FROM pricing_notes WHERE section = 'profit_thresholds'"
            ).fetchall()
        ]
        svc_pricing: dict = {}
        for row in conn.execute(
            "SELECT service_name, tier_name, price FROM service_pricing"
        ).fetchall():
            svc_pricing.setdefault(row["service_name"], {})[row["tier_name"]] = row["price"]
        addon_pricing = {
            r["addon_name"]: r["price"]
            for r in conn.execute("SELECT addon_name, price FROM addon_pricing").fetchall()
        }
        conn.close()
        return json.dumps(
            {
                "pricing_rules": {**rules, "notes": rule_notes},
                "internal_cost_factors": {**cost_factors, "notes": cost_notes},
                "profit_thresholds": {**thresholds, "notes": threshold_notes},
                "services": [
                    {"service_name": name, "price_tiers": tiers}
                    for name, tiers in svc_pricing.items()
                ],
                "add_on_pricing": addon_pricing,
            },
            indent=2,
        )
    except Exception as e:
        return db_error("get_pricing_data", e)


@mcp.tool()
def get_business_policies() -> str:
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT section, content FROM business_policies ORDER BY id"
        ).fetchall()
        conn.close()
        return "\n\n".join(f"{row['section']}\n{row['content']}" for row in rows)
    except Exception as e:
        return db_error("get_business_policies", e)


@mcp.tool()
def get_job_complexity() -> str:
    try:
        conn = get_db()
        levels = conn.execute("SELECT * FROM job_complexity_levels").fetchall()
        framework = {}
        for level in levels:
            level_id = level["id"]
            examples = [
                r["example"]
                for r in conn.execute(
                    "SELECT example FROM job_complexity_examples WHERE level_id = ?", (level_id,)
                ).fetchall()
            ]
            indicators = [
                r["indicator"]
                for r in conn.execute(
                    "SELECT indicator FROM job_complexity_indicators WHERE level_id = ?", (level_id,)
                ).fetchall()
            ]
            framework[level["level"]] = {
                "description": level["description"],
                "examples": examples,
                "typical_indicators": indicators,
            }
        notes = [r["note"] for r in conn.execute("SELECT note FROM job_complexity_notes").fetchall()]
        conn.close()
        return json.dumps({"complexity_framework": framework, "notes": notes}, indent=2)
    except Exception as e:
        return db_error("get_job_complexity", e)


@mcp.tool()
def get_risk_flags() -> str:
    try:
        conn = get_db()
        flags = [
            dict(r)
            for r in conn.execute("SELECT flag, description, impact FROM risk_flags").fetchall()
        ]
        notes = [r["note"] for r in conn.execute("SELECT note FROM risk_flag_notes").fetchall()]
        conn.close()
        return json.dumps({"risk_flags": flags, "notes": notes}, indent=2)
    except Exception as e:
        return db_error("get_risk_flags", e)


@mcp.tool()
def get_staffing_availability() -> str:
    try:
        conn = get_db()
        meta = {
            r["key"]: r["value"]
            for r in conn.execute("SELECT key, value FROM staffing_meta").fetchall()
        }
        groups = conn.execute("SELECT * FROM staff_groups").fetchall()
        crew_breakdown = {}
        for g in groups:
            caps = [
                r["capability"]
                for r in conn.execute(
                    "SELECT capability FROM staff_capabilities WHERE group_id = ?", (g["id"],)
                ).fetchall()
            ]
            crew_breakdown[g["group_name"]] = {"count": g["count"], "capabilities": caps}
        rules = {
            r["job_type"]: r["rule"]
            for r in conn.execute("SELECT job_type, rule FROM crew_deployment_rules").fetchall()
        }
        notes = [r["note"] for r in conn.execute("SELECT note FROM staffing_notes").fetchall()]
        conn.close()
        return json.dumps(
            {
                "staffing_status": {
                    "total_staff_available": int(meta.get("total_staff_available", 0)),
                    "crew_breakdown": crew_breakdown,
                    "carpet_steam_trained_staff": int(meta.get("carpet_steam_trained_staff", 0)),
                    "high_access_trained_staff": int(meta.get("high_access_trained_staff", 0)),
                    "overtime_likelihood": meta.get("overtime_likelihood"),
                    "staffing_pressure": meta.get("staffing_pressure"),
                },
                "crew_deployment_rules": rules,
                "notes": notes,
            },
            indent=2,
        )
    except Exception as e:
        return db_error("get_staffing_availability", e)


@mcp.tool()
def get_schedule_capacity() -> str:
    try:
        conn = get_db()
        meta = {
            r["key"]: r["value"]
            for r in conn.execute("SELECT key, value FROM schedule_meta").fetchall()
        }
        slots = {
            r["slot_name"]: {"status": r["status"], "notes": r["notes"]}
            for r in conn.execute("SELECT slot_name, status, notes FROM schedule_slots").fetchall()
        }
        lead_times = {
            r["service_type"]: r["lead_time"]
            for r in conn.execute("SELECT service_type, lead_time FROM booking_lead_times").fetchall()
        }
        periods = [
            r["period"] for r in conn.execute("SELECT period FROM high_demand_periods").fetchall()
        ]
        notes = [r["note"] for r in conn.execute("SELECT note FROM schedule_notes").fetchall()]
        conn.close()
        return json.dumps(
            {
                "schedule_capacity": {
                    "current_capacity_status": meta.get("current_capacity_status"),
                    "daily_job_slots": slots,
                    "weekday_capacity": meta.get("weekday_capacity"),
                    "weekend_capacity": {
                        "saturday": meta.get("weekend_saturday"),
                        "sunday": meta.get("weekend_sunday"),
                    },
                    "same_day_capacity": meta.get("same_day_capacity"),
                    "high_demand_periods": periods,
                },
                "booking_lead_time_guidelines": lead_times,
                "notes": notes,
            },
            indent=2,
        )
    except Exception as e:
        return db_error("get_schedule_capacity", e)


@mcp.tool()
def get_service_area() -> str:
    try:
        conn = get_db()
        zones = conn.execute("SELECT zone_name, zone_type FROM service_zones").fetchall()
        primary = [r["zone_name"] for r in zones if r["zone_type"] == "primary"]
        extended = [r["zone_name"] for r in zones if r["zone_type"] == "extended"]
        out_of_area = [r["zone_name"] for r in zones if r["zone_type"] == "out_of_area"]
        travel_rows = conn.execute("SELECT * FROM travel_policy").fetchall()
        travel_policy: dict = {}
        travel_times: dict = {}
        for row in travel_rows:
            if row["zone_type"] == "primary":
                travel_policy["primary_zone_surcharge"] = row["surcharge_amount"]
                if row["typical_travel_minutes"]:
                    travel_times["primary_zones"] = row["typical_travel_minutes"]
            elif row["zone_type"] == "extended":
                travel_policy["extended_zone_surcharge"] = row["surcharge_amount"]
                if row["typical_travel_minutes"]:
                    travel_times["extended_zones"] = row["typical_travel_minutes"]
            elif row["zone_type"] == "out_of_area":
                travel_policy["out_of_area"] = row["surcharge_note"]
        notes = [
            r["note"] for r in conn.execute("SELECT note FROM service_area_notes").fetchall()
        ]
        conn.close()
        return json.dumps(
            {
                "service_area": {
                    "primary_zones": primary,
                    "extended_zones": extended,
                    "out_of_area": out_of_area,
                    "travel_policy": travel_policy,
                    "typical_travel_time_minutes": travel_times,
                },
                "notes": notes,
            },
            indent=2,
        )
    except Exception as e:
        return db_error("get_service_area", e)


@mcp.tool()
def get_equipment_readiness() -> str:
    try:
        conn = get_db()
        equipment = conn.execute("SELECT * FROM equipment").fetchall()
        eq_dict = {}
        for eq in equipment:
            entry = {
                "status": eq["status"],
                "condition": eq["condition_status"],
                "notes": eq["notes"],
            }
            if eq["units_available"] is not None:
                entry["units_available"] = eq["units_available"]
            eq_dict[eq["equipment_name"]] = entry
        notes = [r["note"] for r in conn.execute("SELECT note FROM equipment_notes").fetchall()]
        conn.close()
        return json.dumps({"equipment_readiness": eq_dict, "notes": notes}, indent=2)
    except Exception as e:
        return db_error("get_equipment_readiness", e)


@mcp.tool()
def get_resource_availability() -> str:
    try:
        conn = get_db()
        resources = conn.execute("SELECT resource_name, status, notes FROM resources").fetchall()
        res_dict = {
            r["resource_name"]: {"status": r["status"], "notes": r["notes"]} for r in resources
        }
        meta = {
            r["key"]: r["value"]
            for r in conn.execute("SELECT key, value FROM resource_meta").fetchall()
        }
        notes = [r["note"] for r in conn.execute("SELECT note FROM resource_notes").fetchall()]
        conn.close()
        return json.dumps(
            {
                "resource_availability": {**res_dict, "supply_risk": meta.get("supply_risk")},
                "notes": notes,
            },
            indent=2,
        )
    except Exception as e:
        return db_error("get_resource_availability", e)


if __name__ == "__main__":
    mcp.run()
