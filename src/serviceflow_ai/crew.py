from crewai import Agent, Crew, Process, Task, Memory
from crewai.project import CrewBase, agent, crew, task
from crewai.mcp import MCPServerStdio

from serviceflow_ai.tools.customer_tools import CustomerHistoryTool
from serviceflow_ai.tools.business_context_tools import ServiceCatalogueTool
from serviceflow_ai.tools.operations_tools import (
    TravelServiceAreaTool,
    RiskFlaggingTool,
    JobComplexityTool,
    EquipmentReadinessTool,
    ResourceAvailabilityTool,
)
from serviceflow_ai.tools.pricing_tools import (
    InternalCostFactorsTool,
    PricingPolicyTool,
    QuotePolicyTool,
    ProfitThresholdTool,
)
from serviceflow_ai.models import (
    InquiryAnalysisOutput,
    ReadinessCheckOutput,
    CostingOutput,
    PricingOutput,
    ProfitRecommendationOutput,
    EmailDeliveryOutput,
)
from serviceflow_ai.tools.email_tools import SendQuoteEmailTool

crew_memory = Memory(
    semantic_weight=0.4,
    recency_weight=0.4,
    importance_weight=0.2,
    recency_half_life_days=14,
)

business_mcp_server = MCPServerStdio(
    command="python",
    args=["mcp_business_server.py"],
)


@CrewBase
class ServiceflowAi:

    @agent
    def inquiry_analyst_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["inquiry_analyst_agent"],
            tools=[
                CustomerHistoryTool(),
                ServiceCatalogueTool(),
            ],
            mcps=[business_mcp_server],
            verbose=True,
        )

    @agent
    def readiness_check_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["readiness_check_agent"],
            tools=[
                TravelServiceAreaTool(),
                RiskFlaggingTool(),
                JobComplexityTool(),
                EquipmentReadinessTool(),
                ResourceAvailabilityTool(),
            ],
            mcps=[business_mcp_server],
            verbose=True,
        )

    @agent
    def costing_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["costing_agent"],
            tools=[
                InternalCostFactorsTool(),
                JobComplexityTool(),
                RiskFlaggingTool(),
                EquipmentReadinessTool(),
                ResourceAvailabilityTool(),
            ],
            mcps=[business_mcp_server],
            verbose=True,
        )

    @agent
    def pricing_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["pricing_agent"],
            tools=[
                PricingPolicyTool(),
                QuotePolicyTool(),
            ],
            mcps=[business_mcp_server],
            verbose=True,
        )

    @agent
    def profit_optimization_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["profit_optimization_agent"],
            tools=[
                ProfitThresholdTool(),
                RiskFlaggingTool(),
            ],
            mcps=[business_mcp_server],
            verbose=True,
        )

    @agent
    def client_response_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["client_response_agent"],
            tools=[
                QuotePolicyTool(),
                CustomerHistoryTool(),
            ],
            mcps=[business_mcp_server],
            verbose=True,
        )

    @agent
    def email_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["email_agent"],
            tools=[],
            verbose=True,
        )

    @task
    def analyze_inquiry_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_inquiry_task"],
            output_pydantic=InquiryAnalysisOutput,
        )

    @task
    def readiness_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["readiness_check_task"],
            output_pydantic=ReadinessCheckOutput,
        )

    @task
    def costing_task(self) -> Task:
        return Task(
            config=self.tasks_config["costing_task"],
            output_pydantic=CostingOutput,
        )

    @task
    def pricing_task(self) -> Task:
        return Task(
            config=self.tasks_config["pricing_task"],
            output_pydantic=PricingOutput,
        )

    @task
    def profit_optimization_task(self) -> Task:
        return Task(
            config=self.tasks_config["profit_optimization_task"],
            output_pydantic=ProfitRecommendationOutput,
        )

    @task
    def draft_client_response_task(self) -> Task:
        return Task(config=self.tasks_config["draft_client_response_task"])

    @task
    def send_quote_email_task(self) -> Task:
        return Task(
            config=self.tasks_config["send_quote_email_task"],
            output_pydantic=EmailDeliveryOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=crew_memory,
            verbose=True,
        )

    def phase1_crew(self) -> Crew:
        """Agents 1–6: analysis through draft generation. Pauses for human review."""
        return Crew(
            agents=[
                self.inquiry_analyst_agent(),
                self.readiness_check_agent(),
                self.costing_agent(),
                self.pricing_agent(),
                self.profit_optimization_agent(),
                self.client_response_agent(),
            ],
            tasks=[
                self.analyze_inquiry_task(),
                self.readiness_check_task(),
                self.costing_task(),
                self.pricing_task(),
                self.profit_optimization_task(),
                self.draft_client_response_task(),
            ],
            process=Process.sequential,
            verbose=True,
        )

    def phase2_crew(self) -> Crew:
        """Agent 7 only: delivers the human-approved (or rejected) quote email."""
        return Crew(
            agents=[self.email_agent()],
            tasks=[self.send_quote_email_task()],
            process=Process.sequential,
            verbose=True,
        )