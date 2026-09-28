"""General Q&A Agent - Answers general questions and provides information."""
from typing import Any
from app.agents.base_agent import BaseAgent
from app.llm_client import call_llm

SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions clearly and accurately.

Your job is to:
- Answer factual questions with accurate, up-to-date information
- Provide clear explanations for concepts
- Give helpful responses to general inquiries
- Be conversational and friendly while remaining professional

Rules:
- Keep answers concise but complete (2-4 paragraphs max)
- Use bullet points for lists
- Cite sources or indicate uncertainty when appropriate
- If you don't know something, say so honestly
"""

USER_PROMPT_TEMPLATE = """{question}"""


class GeneralQAAgent(BaseAgent):
    """AI Model 5: Answers general questions and provides information."""

    def __init__(self):
        super().__init__(
            name="General Q&A",
            description="Answers general questions, provides information and explanations",
        )

    async def run(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        question = input_data.get("specification", input_data.get("question", ""))
        if not question:
            raise ValueError("No question provided to General Q&A agent")

        user_prompt = USER_PROMPT_TEMPLATE.format(question=question)
        answer = await call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.7, domain="general_qa")

        word_count = len(answer.split())
        summary = f"Generated answer with {word_count} words."
        return summary, {"answer": answer, "format": "text"}
