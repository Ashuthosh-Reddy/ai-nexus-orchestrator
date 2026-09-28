from typing import Any
from app.agents.base_agent import BaseAgent
from app.llm_client import call_llm

SYSTEM_PROMPT = """You are an expert test engineer AI tool called "Test Case Generator".
Your job is to generate executable Python test cases (using pytest) from a test specification and source code.

Rules:
- Generate complete, runnable pytest test code
- Import the source module properly (assume the generated code is saved as 'generated_model.py' in the same directory)
- Cover all scenarios from the test specification
- Use descriptive test function names following test_<feature>_<scenario> pattern
- Include assertions with clear failure messages
- Use pytest fixtures where appropriate
- Include parametrize decorators for data-driven tests where applicable
- Add a brief docstring to each test function
- Output ONLY valid Python test code, no explanations
"""

USER_PROMPT_TEMPLATE = """Generate complete, executable pytest test cases based on the following:

--- SOURCE CODE (saved as generated_model.py) ---
{generated_code}
--- END SOURCE CODE ---

--- TEST SPECIFICATION ---
{test_specification}
--- END TEST SPECIFICATION ---

Generate the complete pytest test file. Output only valid Python code."""


class TestCaseGeneratorAgent(BaseAgent):
    """AI Tool 3: Generates executable pytest test cases from test specs and code."""

    def __init__(self):
        super().__init__(
            name="Test Case Generator",
            description="Generates executable pytest test cases from test specification and source code",
        )

    async def run(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        generated_code = input_data.get("generated_code", "")
        test_specification = input_data.get("test_specification", "")
        if not test_specification:
            raise ValueError("No test specification provided to Test Case Generator")

        user_prompt = USER_PROMPT_TEMPLATE.format(
            generated_code=generated_code,
            test_specification=test_specification,
        )
        test_code = await call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.2, domain="test_engineer")

        # Clean up code fences if present
        code = test_code.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        test_count = len([line for line in code.splitlines() if "def test_" in line])
        summary = f"Generated {test_count} executable pytest test cases."
        return summary, {"test_code": code, "test_count": test_count}
