from serviceflow_ai.crew import ServiceflowAi

def run():
    inputs = {
        "customer_inquiry": """
        Hello, I need a quote for a service job next week.
        The work may require two team members, some specialized equipment,
        and completion before Friday afternoon.
        Please email me at client@example.com.
        """.strip(),
        "human_approved": "false",
        "customer_email": "client@example.com",
    }

    result = ServiceflowAi().crew().kickoff(inputs=inputs)
    print("\n=== FINAL CREW OUTPUT ===\n")
    print(result)


if __name__ == "__main__":
    run()