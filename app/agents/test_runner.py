import subprocess
import os
import tempfile
import sys
from typing import Any
from app.agents.base_agent import BaseAgent
from app.config import settings


class TestRunnerAgent(BaseAgent):
    """AI Tool 4: Executes generated test cases and reports results."""

    def __init__(self):
        super().__init__(
            name="Test Runner",
            description="Executes pytest test cases against generated code and produces a test report",
        )

    async def run(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        generated_code = input_data.get("generated_code", "")
        test_code = input_data.get("test_code", "")
        if not test_code:
            raise ValueError("No test code provided to Test Runner")

        # Create a temporary directory with the source and test files
        with tempfile.TemporaryDirectory(prefix="ainexus_") as tmpdir:
            src_path = os.path.join(tmpdir, "generated_model.py")
            test_path = os.path.join(tmpdir, "test_generated_model.py")

            with open(src_path, "w", encoding="utf-8") as f:
                f.write(generated_code)
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            # Run pytest using subprocess.run (Windows-compatible)
            python_exe = sys.executable
            result = subprocess.run(
                [python_exe, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout + result.stderr

            # Parse results
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            errors = output.count(" ERROR")
            total = passed + failed + errors

            # Save results to output dir
            os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

            with open(os.path.join(settings.OUTPUT_DIR, "generated_model.py"), "w", encoding="utf-8") as f:
                f.write(generated_code)
            with open(os.path.join(settings.OUTPUT_DIR, "test_generated_model.py"), "w", encoding="utf-8") as f:
                f.write(test_code)
            with open(os.path.join(settings.OUTPUT_DIR, "test_report.txt"), "w", encoding="utf-8") as f:
                f.write(output)

            report = {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
                "raw_output": output,
            }

            summary = f"Test Execution: {passed}/{total} passed ({report['pass_rate']}), {failed} failed, {errors} errors."
            return summary, {"test_report": report}
