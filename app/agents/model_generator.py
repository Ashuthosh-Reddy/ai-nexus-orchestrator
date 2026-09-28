from typing import Any
from app.agents.base_agent import BaseAgent
from app.llm_client import call_llm

SYSTEM_PROMPT = """You are an expert software engineer AI tool called "Model Generator".
Your job is to take a software specification and generate a complete, working implementation.

Rules:
- Generate clean, production-quality code
- Include proper class/function structure with type hints
- Include docstrings for all classes and public methods
- Handle edge cases and input validation
- Output ONLY the code, no explanations before or after
- The code must be self-contained and immediately runnable
- Use dataclasses or Pydantic models where appropriate
"""

USER_PROMPT_TEMPLATE = """Generate a complete implementation based on this specification:

--- SPECIFICATION ---
{specification}
--- END SPECIFICATION ---

Generate the complete code implementation. Output only valid code."""


class ModelGeneratorAgent(BaseAgent):
    """AI Tool 1: Generates code/model from a software specification."""

    def __init__(self):
        super().__init__(
            name="Model Generator",
            description="Generates code/model from a software specification document",
        )

    async def run(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        specification = input_data.get("specification", "")
        if not specification:
            raise ValueError("No specification provided to Model Generator")

        user_prompt = USER_PROMPT_TEMPLATE.format(specification=specification)
        generated_code = await call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.2, domain="code_generator")

        # Clean up code fences if present
        code = generated_code.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        # Detect language from code fence or default
        lang = "python"
        if generated_code.strip().startswith("```"):
            first_line = generated_code.strip().split("\n")[0].replace("```", "").strip().lower()
            if first_line:
                lang = first_line

        summary = f"Generated {len(code.splitlines())} lines of {lang} code from specification."
        return summary, {"generated_code": code, "language": lang}
