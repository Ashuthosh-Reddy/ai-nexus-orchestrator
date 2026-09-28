from typing import Any
from app.agents.base_agent import BaseAgent
from app.llm_client import call_llm

SYSTEM_PROMPT = """You are an expert QA architect AI tool called "Test Specification Generator".
Your job is to analyze source code and its original specification to produce a comprehensive test specification document.

Rules:
- Identify all testable units (functions, classes, methods, edge cases)
- Categorize tests: Unit Tests, Integration Tests, Edge Cases, Negative Tests
- For each test area, describe: objective, preconditions, expected behavior
- Use a structured format with clear sections
- Be thorough — cover happy paths, error paths, boundary conditions
- Output in clean Markdown format
"""

USER_PROMPT_TEMPLATE = """Analyze the following source code and specification, then generate a comprehensive test specification document.

--- ORIGINAL SPECIFICATION ---
{specification}
--- END SPECIFICATION ---

--- GENERATED SOURCE CODE ---
{generated_code}
--- END SOURCE CODE ---

Generate a complete test specification document in Markdown format."""


class TestSpecGeneratorAgent(BaseAgent):
    """AI Tool 2: Generates test specifications from code and its specification."""

    def __init__(self):
        super().__init__(
            name="Test Specification Generator",
            description="Analyzes code and spec to produce a structured test specification document",
        )

    async def run(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        specification = input_data.get("specification", "")
        generated_code = input_data.get("generated_code", "")
        if not generated_code:
            raise ValueError("No generated code provided to Test Spec Generator")

        user_prompt = USER_PROMPT_TEMPLATE.format(
            specification=specification,
            generated_code=generated_code,
        )
        test_spec = await call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.2, domain="test_engineer")

        sections = [line for line in test_spec.splitlines() if line.strip().startswith("##")]
        summary = f"Generated test specification with {len(sections)} test sections covering the codebase."
        return summary, {"test_specification": test_spec}
