# AI Nexus Orchestrator

> **GOH-UC-037** — Agentic AI Pipeline for End-to-End Software Development

An intelligent orchestrator that chains multiple AI tools into a seamless, automated pipeline:  
**Specification → Code Generation → Test Specification → Test Cases → Test Execution & Reporting**

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-orange)

---

## Problem Statement

LTTS has multiple discrete AI tools within AI Nexus for software development — model generation from specifications, test specification creation, and test case generation. These are **point solutions** that operate independently. There is no unified agentic environment that can orchestrate these tools to drive **end-to-end software development** autonomously.

## Solution

An **Agentic AI Orchestrator** that:

1. Accepts a software specification as input
2. Automatically chains 4 specialized AI agents in sequence
3. Passes artifacts between agents (output of one becomes input to the next)
4. Provides real-time streaming progress via Server-Sent Events
5. Delivers a complete package: working code, test spec, test cases, and test results

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI NEXUS ORCHESTRATOR                       │
│                                                                 │
│  ┌──────────┐    ┌───────────┐    ┌───────────┐    ┌─────────┐ │
│  │  Agent 1  │───▶│  Agent 2  │───▶│  Agent 3  │───▶│ Agent 4 │ │
│  │  Model    │    │ Test Spec │    │ Test Case │    │  Test   │ │
│  │ Generator │    │ Generator │    │ Generator │    │ Runner  │ │
│  └──────────┘    └───────────┘    └───────────┘    └─────────┘ │
│       │                │                │               │       │
│       ▼                ▼                ▼               ▼       │
│  Python Code    Test Spec (MD)    Pytest Code     Test Report   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Pipeline Orchestrator (async)                 │ │
│  │  • Chains agents sequentially                              │ │
│  │  • Passes artifacts via shared context                     │ │
│  │  • Streams real-time events (SSE)                          │ │
│  │  • Handles errors gracefully per stage                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              FastAPI Backend + Web UI                       │ │
│  │  • REST API for pipeline control                           │ │
│  │  • SSE streaming for live updates                          │ │
│  │  • Modern glass-morphism dashboard                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Details

| Component | File | Purpose |
|-----------|------|---------|
| **Base Agent** | `app/agents/base_agent.py` | Abstract base class for all agents with execute/run pattern, timing, error handling |
| **Model Generator** | `app/agents/model_generator.py` | LLM-powered agent that converts specification → Python code |
| **Test Spec Generator** | `app/agents/test_spec_generator.py` | Analyzes code + spec → structured test specification document |
| **Test Case Generator** | `app/agents/test_case_generator.py` | Converts test spec + code → executable pytest test file |
| **Test Runner** | `app/agents/test_runner.py` | Writes files to temp dir, runs pytest, parses results |
| **Orchestrator** | `app/orchestrator.py` | Pipeline engine that chains agents, manages context flow, streams events |
| **LLM Client** | `app/llm_client.py` | Async OpenAI client wrapper |
| **API Server** | `app/main.py` | FastAPI endpoints for pipeline control and artifact retrieval |
| **Web UI** | `app/static/index.html` | Real-time dashboard with stage tracking, live logs, artifact viewer |

---

## Approach

### Design Principles

1. **Agent Abstraction** — Each AI tool is wrapped in a `BaseAgent` with a uniform `execute()` interface, making it easy to add/remove/reorder agents.

2. **Context Flow** — A shared `context` dictionary flows through the pipeline. Each agent reads what it needs and writes its artifacts back. This is the "glue" that makes the agents work together.

3. **Streaming Architecture** — The pipeline uses async generators + SSE to stream real-time progress to the frontend, giving users immediate feedback.

4. **Fail-Fast with Isolation** — If any stage fails, the pipeline stops immediately with a clear error. Each agent runs in isolation so failures don't corrupt other stages.

5. **Real Execution** — The Test Runner actually writes code to disk and runs `pytest`, providing genuine pass/fail results — not simulated.

### Pipeline Flow

```
Input: Software Specification (plain text)
          │
          ▼
    ┌─────────────┐
    │   Agent 1    │  System prompt: "You are an expert software engineer..."
    │   Model Gen  │  Input: specification
    │              │  Output: Python source code
    └──────┬──────┘
           │ context += {generated_code}
           ▼
    ┌─────────────┐
    │   Agent 2    │  System prompt: "You are an expert QA architect..."
    │  Test Spec   │  Input: specification + generated_code
    │   Generator  │  Output: Markdown test specification
    └──────┬──────┘
           │ context += {test_specification}
           ▼
    ┌─────────────┐
    │   Agent 3    │  System prompt: "You are an expert test engineer..."
    │  Test Case   │  Input: generated_code + test_specification
    │   Generator  │  Output: Executable pytest code
    └──────┬──────┘
           │ context += {test_code}
           ▼
    ┌─────────────┐
    │   Agent 4    │  No LLM needed — runs subprocess
    │  Test Runner │  Input: generated_code + test_code
    │              │  Output: pytest results + report
    └─────────────┘
           │
           ▼
    Output: {generated_code, test_spec, test_cases, test_report}
            All saved to outputs/ directory
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- One of the following LLM providers:
  - **HuggingFace** (free token, cloud-hosted open-source models) — recommended for quick start
  - **Ollama** (free, runs models locally) — recommended for offline/privacy
  - **OpenAI** (paid API key)
  - **LM Studio** (free, local GUI)

### Setup (Windows PowerShell)

```powershell
# 1. Navigate to project
cd ai-nexus-orchestrator

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install dependencies
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 5. Create .env config from template
Copy-Item .env.example .env

# 6. Edit .env — choose your provider (see provider setup below)

# 7. Run the server
.\venv\Scripts\python.exe run.py
```

### Setup (Linux / macOS)

```bash
cd ai-nexus-orchestrator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — choose your provider (see provider setup below)
python run.py
```

### Provider Setup

#### Option A: HuggingFace (recommended — free, no install)

1. Go to https://huggingface.co/settings/tokens
2. Sign up (free) → Create a token with **Read** access
3. Edit `.env`:
   ```
   LLM_PROVIDER=huggingface
   LLM_API_KEY=hf_your-token-here
   LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3
   ```

#### Option B: Ollama (free, runs locally)

1. Install Ollama from https://ollama.com
2. Pull a model: `ollama pull llama3.1:8b`
3. Edit `.env`:
   ```
   LLM_PROVIDER=ollama
   LLM_MODEL=llama3.1:8b
   ```
   No API key needed.

#### Option C: OpenAI (paid)

1. Get an API key from https://platform.openai.com/api-keys
2. Edit `.env`:
   ```
   LLM_PROVIDER=openai
   LLM_API_KEY=sk-your-key-here
   LLM_MODEL=gpt-4o-mini
   ```

### Usage

1. Open browser at **http://localhost:8000**
2. Verify the top-right badge shows your provider (e.g., `HUGGINGFACE · mistralai/Mistral-7B-Instruct-v0.3`)
3. Paste a software specification (or click **"Load Example"**)
4. Click **Run Pipeline**
5. Watch the 4 agents execute in real-time
6. View generated code, test spec, test cases, and test results in the artifact tabs

> **Note:** If you change `.env`, you must restart the server for changes to take effect.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/api/health` | Health check + config status |
| `POST` | `/api/pipeline/start` | Start pipeline (SSE stream) |
| `GET` | `/api/pipeline/{run_id}` | Get pipeline run status |
| `GET` | `/api/pipeline/{run_id}/artifacts` | Get full artifacts |

---

## Output Artifacts

After a successful run, the `outputs/` directory contains:

| File | Description |
|------|-------------|
| `generated_model.py` | The AI-generated Python source code |
| `test_generated_model.py` | The AI-generated pytest test file |
| `test_report.txt` | Raw pytest execution output |

---

## Extensibility

The architecture is designed for easy extension:

### Adding a New Agent

```python
from app.agents.base_agent import BaseAgent

class MyNewAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="My Agent", description="Does something")

    async def run(self, input_data):
        # Use input_data from context
        # Return (summary_string, artifacts_dict)
        return "Done", {"my_output": result}
```

Then add it to the pipeline in `app/orchestrator.py`:

```python
self.agents = [
    ModelGeneratorAgent(),
    MyNewAgent(),           # ← insert anywhere in the chain
    TestSpecGeneratorAgent(),
    ...
]
```

### Potential Extensions

- **Code Review Agent** — Reviews generated code for quality/security
- **Documentation Agent** — Generates API docs from code
- **Deployment Agent** — Packages and deploys the code
- **Feedback Loop** — Re-runs code generation if tests fail
- **Multi-Language** — Support C, Java, etc. via agent config
- **MCP Integration** — Expose agents as MCP tools for IDE integration

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| AI/LLM | OpenAI API (GPT-4o / GPT-4o-mini) |
| Frontend | HTML5, TailwindCSS, Lucide Icons |
| Streaming | Server-Sent Events (SSE) |
| Testing | pytest (executed by Test Runner agent) |
| Config | python-dotenv, Pydantic |

---

## Hackathon Demo Script

1. **Show the problem**: "We have separate AI tools — they don't talk to each other"
2. **Show the architecture**: Walk through the 4-agent pipeline diagram
3. **Live demo**: Paste a spec → watch all 4 stages run in real-time
4. **Show artifacts**: Generated code, test spec, test cases, test results — all from one click
5. **Show extensibility**: "Adding a new agent is just one class and one line of config"
6. **Key value**: "Reduced manual handoff between tools from hours to seconds"
