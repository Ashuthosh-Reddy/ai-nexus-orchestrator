"""Document Analyzer Agent - Analyzes documents, extracts insights and summaries."""
from typing import Any
from app.agents.base_agent import BaseAgent
from app.llm_client import call_llm

SYSTEM_PROMPT = """You are an expert Document Analyzer AI tool.
Your job is to analyze technical documents, specifications, or text and produce:
1. An executive summary
2. Key findings and insights
3. Identified gaps or risks
4. Actionable recommendations
5. Complexity/effort assessment

Rules:
- Be thorough and structured
- Use clear Markdown formatting with sections
- Highlight critical items
- Provide quantitative assessments where possible
- Output in clean Markdown format
"""

USER_PROMPT_TEMPLATE = """Analyze the following document/text and produce a comprehensive analysis report:

--- DOCUMENT ---
{document}
--- END DOCUMENT ---

Generate a complete analysis report in Markdown format."""


class DocAnalyzerAgent(BaseAgent):
    """AI Model 3: Analyzes documents and extracts insights."""

    def __init__(self):
        super().__init__(
            name="Document Analyzer",
            description="Analyzes technical documents, extracts insights, and generates comprehensive reports",
        )

    async def run(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        document = input_data.get("specification", input_data.get("document", ""))
        if not document:
            raise ValueError("No document/text provided to Document Analyzer")

        user_prompt = USER_PROMPT_TEMPLATE.format(document=document)
        analysis = await call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.3, domain="doc_analyzer")

        sections = [line for line in analysis.splitlines() if line.strip().startswith("##")]
        summary = f"Generated analysis report with {len(sections)} sections covering the document."
        return summary, {"analysis_report": analysis, "format": "markdown"}
