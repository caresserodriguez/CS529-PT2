import json
import sqlite3
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from serviceflow_ai.guardrails import validate_email_input


DB_PATH = Path(__file__).resolve().parents[3] / "data" / "serviceflow.db"


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_customer_record(conn: sqlite3.Connection, customer_id: int) -> dict:
    past_services = [
        r["service_name"]
        for r in conn.execute(
            "SELECT service_name FROM customer_past_services WHERE customer_id = ?",
            (customer_id,),
        ).fetchall()
    ]
    common_requests = [
        r["request"]
        for r in conn.execute(
            "SELECT request FROM customer_common_requests WHERE customer_id = ?",
            (customer_id,),
        ).fetchall()
    ]
    notes = [
        r["note"]
        for r in conn.execute(
            "SELECT note FROM customer_notes WHERE customer_id = ?",
            (customer_id,),
        ).fetchall()
    ]
    return {
        "past_services": past_services,
        "common_requests": common_requests,
        "notes": notes,
    }


class CustomerHistoryToolInput(BaseModel):
    customer_email: str = Field(
        default="",
        description="Customer email used to look up prior customer history.",
    )


class CustomerHistoryTool(BaseTool):
    name: str = "Customer History Tool"
    description: str = (
        "Returns customer history and prior context for the current customer. "
        "Use this tool when you need background information such as past services, "
        "preferences, communication style, recurring requests, or other useful "
        "customer-specific notes."
    )
    args_schema: Type[BaseModel] = CustomerHistoryToolInput

    def _run(self, customer_email: str = "") -> str:
        try:
            conn = _get_db()

            if customer_email:
                email_lower = customer_email.strip().lower()
                row = conn.execute(
                    "SELECT * FROM customers WHERE email = ?", (email_lower,)
                ).fetchone()

                if row:
                    related = _fetch_customer_record(conn, row["id"])
                    conn.close()
                    return json.dumps(
                        {
                            "customer_email": customer_email,
                            "customer_found": True,
                            "customer_history": {
                                "repeat_customer": bool(row["repeat_customer"]),
                                "customer_since": row["customer_since"],
                                "property_type": row["property_type"],
                                "property_size": row["property_size"],
                                "location_zone": row["location_zone"],
                                "service_frequency": row["service_frequency"],
                                "preferred_schedule": row["preferred_schedule"],
                                "preferred_contact_style": row["preferred_contact_style"],
                                **related,
                            },
                        },
                        indent=2,
                    )

                conn.close()
                return json.dumps(
                    {
                        "customer_email": customer_email,
                        "customer_found": False,
                        "message": "No prior customer history found.",
                    },
                    indent=2,
                )

            # No email provided — return all customers
            customers = conn.execute("SELECT * FROM customers").fetchall()
            result = {}
            for customer in customers:
                related = _fetch_customer_record(conn, customer["id"])
                result[customer["email"]] = {
                    "repeat_customer": bool(customer["repeat_customer"]),
                    "customer_since": customer["customer_since"],
                    "property_type": customer["property_type"],
                    "property_size": customer["property_size"],
                    "location_zone": customer["location_zone"],
                    "service_frequency": customer["service_frequency"],
                    "preferred_schedule": customer["preferred_schedule"],
                    "preferred_contact_style": customer["preferred_contact_style"],
                    **related,
                }
            conn.close()
            return json.dumps({"customers": result}, indent=2)

        except Exception as e:
            return json.dumps(
                {"error": "failed_to_load_customer_history", "message": str(e)},
                indent=2,
            )
