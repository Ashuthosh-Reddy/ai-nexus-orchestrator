"""Data Analytics Agent - Generates analysis code and statistical insights."""
from typing import Any
from app.agents.base_agent import BaseAgent
from app.llm_client import call_llm

SYSTEM_PROMPT = """You are an expert Data Analytics AI tool.
Your job is to take a data description or dataset specification and generate:
1. Complete Python analysis code using pandas, matplotlib, numpy
2. Statistical summaries and insights
3. Visualization scripts that produce charts and dashboards

Rules:
- Generate clean, runnable Python code
- Include data loading, cleaning, analysis, and visualization steps
- Use pandas for data manipulation
- Use matplotlib/seaborn for visualizations
- Add print statements for key statistics
- Save charts to files
- Output ONLY the Python code, no explanations
"""

USER_PROMPT_TEMPLATE = """Generate a complete Python data analysis script based on this description:

--- DATA DESCRIPTION ---
{specification}
--- END DESCRIPTION ---

Generate complete, runnable Python analysis code with visualizations."""


class DataAnalyticsAgent(BaseAgent):
    """AI Model 4: Generates data analysis code and insights."""

    def __init__(self):
        super().__init__(
            name="Data Analytics",
            description="Generates data analysis code, statistical insights, and visualization scripts",
        )

    async def run(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        specification = input_data.get("specification", "")
        if not specification:
            raise ValueError("No data description provided to Data Analytics agent")

        user_prompt = USER_PROMPT_TEMPLATE.format(specification=specification)
        analysis_code = await call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.2, domain="data_analytics")

        code = analysis_code.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        summary = f"Generated {len(code.splitlines())} lines of data analysis code with visualizations."
        return summary, {"analysis_code": code, "language": "python"}
