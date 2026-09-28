import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator

from app.agents.base_agent import AgentResult, AgentStatus
from app.agents.model_generator import ModelGeneratorAgent
from app.agents.test_spec_generator import TestSpecGeneratorAgent
from app.agents.test_case_generator import TestCaseGeneratorAgent
from app.agents.test_runner import TestRunnerAgent
from app.agents.doc_analyzer import DocAnalyzerAgent
from app.agents.data_analytics import DataAnalyticsAgent
from app.agents.general_qa import GeneralQAAgent
from app.agents.router_agent import route_query


# Domain-specific pipeline definitions
DOMAIN_PIPELINES = {
    "code_generator": {
        "stages": [
            {"name": "Code Generator", "desc": "Generate code from specification"},
        ],
    },
    "test_engineer": {
        "stages": [
            {"name": "Test Spec Generator", "desc": "Analyze spec and create test plan"},
            {"name": "Test Case Generator", "desc": "Generate executable test cases"},
            {"name": "Test Runner", "desc": "Execute tests and report results"},
        ],
    },
    "doc_analyzer": {
        "stages": [
            {"name": "Document Analyzer", "desc": "Analyze document and extract insights"},
        ],
    },
    "data_analytics": {
        "stages": [
            {"name": "Data Analytics", "desc": "Generate analysis code and visualizations"},
        ],
    },
    "general_qa": {
        "stages": [
            {"name": "General Q&A", "desc": "Answer question and provide information"},
        ],
    },
}

# Agent registry — maps stage names to agent instances
AGENT_REGISTRY = {
    "Code Generator": ModelGeneratorAgent(),
    "Test Spec Generator": TestSpecGeneratorAgent(),
    "Test Case Generator": TestCaseGeneratorAgent(),
    "Test Runner": TestRunnerAgent(),
    "Document Analyzer": DocAnalyzerAgent(),
    "Data Analytics": DataAnalyticsAgent(),
    "General Q&A": GeneralQAAgent(),
}


@dataclass
class PipelineStage:
    stage_number: int
    agent_name: str
    description: str
    status: AgentStatus = AgentStatus.PENDING
    result: AgentResult | None = None


@dataclass
class PipelineRun:
    run_id: str
    query: str
    routed_model: str = ""
    routed_model_name: str = ""
    routing_confidence: float = 0.0
    routing_method: str = ""
    stages: list[PipelineStage] = field(default_factory=list)
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "query": self.query[:200] + "..." if len(self.query) > 200 else self.query,
            "routed_model": self.routed_model,
            "routed_model_name": self.routed_model_name,
            "routing_confidence": self.routing_confidence,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "stages": [
                {
                    "stage_number": s.stage_number,
                    "agent_name": s.agent_name,
                    "description": s.description,
                    "status": s.status.value,
                    "result": {
                        "agent_name": s.result.agent_name,
                        "status": s.result.status.value,
                        "output": s.result.output,
                        "artifacts": {
                            k: (v[:500] + "..." if isinstance(v, str) and len(v) > 500 else v)
                            for k, v in s.result.artifacts.items()
                        },
                        "error": s.result.error,
                        "duration_seconds": s.result.duration_seconds,
                    } if s.result else None,
                }
                for s in self.stages
            ],
        }


class PipelineOrchestrator:
    """
    Intelligent AI Orchestrator that:
    1. Receives a user query
    2. Routes it to the best domain-specific AI model via the Router Agent
    3. Executes the appropriate pipeline stages
    4. Returns results with full artifacts
    """

    def __init__(self):
        self.runs: dict[str, PipelineRun] = {}

    def _create_pipeline(self, run_id: str, query: str, model_id: str,
                         routing_info: dict) -> PipelineRun:
        pipeline_def = DOMAIN_PIPELINES.get(model_id, DOMAIN_PIPELINES["code_generator"])
        stages = [
            PipelineStage(i + 1, s["name"], s["desc"])
            for i, s in enumerate(pipeline_def["stages"])
        ]
        pipeline = PipelineRun(
            run_id=run_id,
            query=query,
            routed_model=model_id,
            routed_model_name=routing_info.get("model_name", model_id),
            routing_confidence=routing_info.get("confidence", 0),
            routing_method=routing_info.get("method", ""),
            stages=stages,
        )
        self.runs[run_id] = pipeline
        return pipeline

    async def run_pipeline(self, run_id: str, query: str) -> AsyncGenerator[dict, None]:
        """Route query, build pipeline, execute stages, yield SSE events."""
        start = datetime.now()

        # Step 1: Route the query
        yield self._event("routing_started", {"query": query[:200]})
        routing_info = await route_query(query)
        model_id = routing_info["selected_model"]

        yield self._event("routing_completed", {
            "selected_model": model_id,
            "model_name": routing_info["model_name"],
            "model_description": routing_info["model_description"],
            "confidence": routing_info["confidence"],
            "method": routing_info["method"],
        })

        # Step 2: Build the pipeline for the selected model
        pipeline = self._create_pipeline(run_id, query, model_id, routing_info)
        pipeline.status = "running"
        pipeline.started_at = start.isoformat()

        context: dict[str, Any] = {"specification": query}

        yield self._event("pipeline_started", {
            "run_id": run_id,
            "total_stages": len(pipeline.stages),
            "model_id": model_id,
            "model_name": routing_info["model_name"],
        })

        # Step 3: Execute each stage
        for stage in pipeline.stages:
            agent = AGENT_REGISTRY.get(stage.agent_name)
            if not agent:
                pipeline.status = "failed"
                yield self._event("stage_failed", {
                    "stage_number": stage.stage_number,
                    "agent_name": stage.agent_name,
                    "error": f"Agent '{stage.agent_name}' not found in registry",
                })
                return

            stage.status = AgentStatus.RUNNING
            yield self._event("stage_started", {
                "stage_number": stage.stage_number,
                "agent_name": stage.agent_name,
                "description": stage.description,
            })

            result = await agent.execute(context)
            stage.result = result
            stage.status = result.status

            if result.status == AgentStatus.FAILED:
                pipeline.status = "failed"
                pipeline.completed_at = datetime.now().isoformat()
                yield self._event("stage_failed", {
                    "stage_number": stage.stage_number,
                    "agent_name": stage.agent_name,
                    "error": result.error,
                })
                yield self._event("pipeline_failed", {
                    "run_id": run_id,
                    "failed_at_stage": stage.stage_number,
                    "error": result.error,
                })
                return

            context.update(result.artifacts)
            pipeline.context = {
                k: (v[:300] + "..." if isinstance(v, str) and len(v) > 300 else v)
                for k, v in context.items()
            }

            yield self._event("stage_completed", {
                "stage_number": stage.stage_number,
                "agent_name": stage.agent_name,
                "summary": result.output,
                "duration_seconds": result.duration_seconds,
                "artifacts_keys": list(result.artifacts.keys()),
            })

        # Step 4: Pipeline complete
        pipeline.status = "completed"
        pipeline.completed_at = datetime.now().isoformat()

        total_duration = sum(s.result.duration_seconds for s in pipeline.stages if s.result)
        test_report = context.get("test_report", {})

        yield self._event("pipeline_completed", {
            "run_id": run_id,
            "routed_model": model_id,
            "model_name": routing_info["model_name"],
            "total_duration_seconds": round(total_duration, 2),
            "test_summary": {
                "total": test_report.get("total_tests", 0),
                "passed": test_report.get("passed", 0),
                "failed": test_report.get("failed", 0),
                "pass_rate": test_report.get("pass_rate", "N/A"),
            },
            "stages_summary": [
                {
                    "stage": s.stage_number,
                    "agent": s.agent_name,
                    "status": s.status.value,
                    "duration": s.result.duration_seconds if s.result else 0,
                    "summary": s.result.output if s.result else "",
                }
                for s in pipeline.stages
            ],
        })

    def get_run(self, run_id: str) -> PipelineRun | None:
        return self.runs.get(run_id)

    def get_full_artifacts(self, run_id: str) -> dict[str, Any] | None:
        pipeline = self.runs.get(run_id)
        if not pipeline:
            return None
        artifacts = {}
        for stage in pipeline.stages:
            if stage.result and stage.result.artifacts:
                artifacts[stage.agent_name] = stage.result.artifacts
        return artifacts

    @staticmethod
    def _event(event_type: str, data: dict) -> dict:
        return {"event": event_type, "data": data}


# Singleton
orchestrator = PipelineOrchestrator()
