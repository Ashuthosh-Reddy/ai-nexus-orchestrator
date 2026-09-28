import asyncio
import re
import time
from openai import AsyncOpenAI
from app.config import settings, DOMAIN_MAX_TOKENS

# Response cache: (system_prompt_hash, user_prompt_hash) -> (response, timestamp)
_response_cache: dict[tuple[int, int], tuple[str, float]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _make_client(config: dict) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=60.0,
    )


def get_llm_client() -> AsyncOpenAI:
    config = settings.get_provider_config()
    return _make_client(config)


async def _call_provider(config: dict, messages: list, temperature: float,
                         max_tokens: int) -> str:
    """Make an LLM call to a specific provider config. Raises on failure."""
    client = _make_client(config)
    kwargs = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


async def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3,
                   max_tokens: int | None = None, domain: str = "") -> str:
    """Provider-agnostic LLM call with fallback chain and caching."""
    if settings.DEMO_MODE:
        return await _demo_response(system_prompt, user_prompt)

    # Check cache
    cache_key = (hash(system_prompt), hash(user_prompt))
    if cache_key in _response_cache:
        cached_resp, cached_time = _response_cache[cache_key]
        if time.time() - cached_time < CACHE_TTL_SECONDS:
            print(f"[LLM CACHE HIT] Returning cached response")
            return cached_resp

    # Determine max_tokens from domain config if not explicitly set
    if max_tokens is None:
        max_tokens = DOMAIN_MAX_TOKENS.get(domain, 2048)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Build provider chain: primary -> fallbacks -> demo
    providers_to_try = []

    # Primary provider
    primary_config = settings.get_provider_config()
    providers_to_try.append((settings.LLM_PROVIDER, primary_config))

    # Fallback providers from env
    for fb_provider in settings.FALLBACK_PROVIDERS:
        if fb_provider != settings.LLM_PROVIDER:
            fb_config = settings.get_provider_config_for(fb_provider)
            if fb_config["api_key"]:
                providers_to_try.append((fb_provider, fb_config))

    # Try each provider in order
    last_error = None
    for provider_name, config in providers_to_try:
        try:
            print(f"[LLM] Calling {provider_name} ({config['model']}) max_tokens={max_tokens}")
            result = await _call_provider(config, messages, temperature, max_tokens)
            # Cache successful response
            _response_cache[cache_key] = (result, time.time())
            return result
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            is_connection_error = any(k in error_msg for k in
                                     ["connection", "refused", "getaddrinfo", "timeout", "unreachable"])
            print(f"[LLM FALLBACK] {provider_name} failed: {e}")
            if not is_connection_error:
                # Non-connection errors (auth, rate limit) — still try fallbacks
                continue

    # All providers failed — fall back to demo mode
    print(f"[LLM FALLBACK] All providers failed, using demo mode. Last error: {last_error}")
    return await _demo_response(system_prompt, user_prompt)


def _extract_topic(user_prompt: str) -> dict:
    """Extract the main topic/entity from the user's query for contextual demo responses."""
    # Clean the prompt
    text = user_prompt.strip()
    for prefix in ["Generate a complete implementation based on this specification:",
                   "--- SPECIFICATION ---", "--- END SPECIFICATION ---",
                   "Generate the complete code implementation. Output only valid code.",
                   "Analyze the following source code", "--- ORIGINAL SPECIFICATION ---",
                   "--- END SPECIFICATION ---", "--- GENERATED SOURCE CODE ---",
                   "--- END SOURCE CODE ---", "Generate complete, executable pytest test cases",
                   "--- SOURCE CODE", "--- TEST SPECIFICATION ---", "--- END TEST SPECIFICATION ---",
                   "--- DOCUMENT ---", "--- END DOCUMENT ---", "--- DATA DESCRIPTION ---",
                   "--- END DESCRIPTION ---"]:
        text = text.replace(prefix, "")
    text = text.strip()

    # Extract a class name from the topic
    words = [w for w in re.split(r'[\s,.\-:;]+', text) if len(w) > 2 and w[0].isalpha()]
    # Build a meaningful class name from first few significant words
    stop_words = {"the", "and", "for", "with", "that", "this", "from", "build", "create",
                  "implement", "generate", "make", "write", "develop", "following", "features",
                  "based", "using", "should", "have", "has", "are", "can", "will", "class",
                  "system", "module", "also", "each", "all", "any", "add", "use", "include"}
    key_words = [w for w in words[:20] if w.lower() not in stop_words and len(w) > 2][:4]

    if not key_words:
        key_words = ["Service"]

    class_name = "".join(w.capitalize() for w in key_words[:2])
    manager_name = class_name + "Manager"
    module_desc = " ".join(key_words[:4]).lower()

    return {
        "class_name": class_name,
        "manager_name": manager_name,
        "module_desc": module_desc,
        "key_words": key_words,
        "raw_topic": text[:300],
    }


def _demo_code(topic: dict) -> str:
    cn = topic["class_name"]
    mn = topic["manager_name"]
    desc = topic["module_desc"]
    spec = topic["raw_topic"]
    return f'''"""Auto-generated module: {desc}

Based on specification:
{spec[:200]}{'...' if len(spec) > 200 else ''}
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class {cn}:
    """Represents a {desc} entity."""
    id: int
    name: str
    description: str = ""
    status: str = "active"
    category: str = "default"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def update(self, **kwargs) -> None:
        """Update entity fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

    def deactivate(self) -> None:
        """Mark entity as inactive."""
        self.status = "inactive"
        self.updated_at = datetime.now()

    def is_active(self) -> bool:
        """Check if entity is active."""
        return self.status == "active"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {{
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }}


class {mn}:
    """Manages a collection of {desc} entities with full CRUD operations."""

    def __init__(self):
        self._items: dict[int, {cn}] = {{}}
        self._next_id: int = 1

    def create(self, name: str, description: str = "", category: str = "default") -> {cn}:
        """Create a new {desc} entity."""
        if not name.strip():
            raise ValueError("Name cannot be empty")
        item = {cn}(id=self._next_id, name=name, description=description, category=category)
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def get(self, item_id: int) -> Optional[{cn}]:
        """Get an entity by ID."""
        return self._items.get(item_id)

    def list_all(self, status: Optional[str] = None, category: Optional[str] = None) -> list[{cn}]:
        """List entities with optional filters."""
        items = list(self._items.values())
        if status:
            items = [i for i in items if i.status == status]
        if category:
            items = [i for i in items if i.category == category]
        return sorted(items, key=lambda i: i.created_at, reverse=True)

    def update(self, item_id: int, **kwargs) -> bool:
        """Update an entity. Returns True if successful."""
        item = self._items.get(item_id)
        if item:
            item.update(**kwargs)
            return True
        return False

    def delete(self, item_id: int) -> bool:
        """Delete an entity by ID."""
        return self._items.pop(item_id, None) is not None

    def search(self, query: str) -> list[{cn}]:
        """Search entities by name or description."""
        query_lower = query.lower()
        return [i for i in self._items.values()
                if query_lower in i.name.lower() or query_lower in i.description.lower()]

    def get_stats(self) -> dict:
        """Get statistics."""
        items = list(self._items.values())
        categories = {{}}
        for i in items:
            categories[i.category] = categories.get(i.category, 0) + 1
        return {{
            "total": len(items),
            "active": sum(1 for i in items if i.status == "active"),
            "inactive": sum(1 for i in items if i.status == "inactive"),
            "categories": categories,
        }}
'''


def _demo_test_spec(topic: dict) -> str:
    cn = topic["class_name"]
    mn = topic["manager_name"]
    desc = topic["module_desc"]
    return f'''# Test Specification Document — {desc}

## 1. Unit Tests — {cn} Class
### 1.1 Entity Creation
- **Objective**: Verify {cn} initializes with correct defaults
- **Preconditions**: None
- **Expected**: id, name set; status="active"; created_at auto-set; updated_at=None

### 1.2 Update Method
- **Objective**: Verify update() modifies fields and sets updated_at
- **Expected**: Fields updated; updated_at is set to current time

### 1.3 Deactivate
- **Objective**: Verify deactivate() sets status and timestamp
- **Expected**: status="inactive"; updated_at is set

### 1.4 to_dict Serialization
- **Objective**: Verify to_dict() returns correct dictionary
- **Expected**: All fields present with correct values

## 2. Unit Tests — {mn} Class
### 2.1 Create Entity
- **Objective**: Verify entity creation with auto-incrementing ID
- **Expected**: Entity returned with correct name, description, category

### 2.2 Create Validation
- **Objective**: Verify empty name raises ValueError
- **Expected**: ValueError raised

### 2.3 Get Entity
- **Objective**: Verify retrieval by valid and invalid ID
- **Expected**: Returns {cn} for valid ID, None for invalid

### 2.4 List Entities with Filters
- **Objective**: Verify listing with status and category filters
- **Expected**: Correct filtered results, sorted by creation date desc

### 2.5 Update Entity
- **Objective**: Verify entity update by ID
- **Expected**: Returns True and fields change; False for invalid ID

### 2.6 Delete Entity
- **Objective**: Verify entity deletion
- **Expected**: Returns True and entity removed; False for invalid ID

### 2.7 Search
- **Objective**: Verify search by name and description
- **Expected**: Returns matching entities

### 2.8 Get Stats
- **Objective**: Verify statistics calculation
- **Expected**: Correct counts for total, active, inactive, categories

## 3. Edge Cases
- Empty manager operations
- Updating a non-existent entity
- Deleting a non-existent entity
- Search with no matches
- Large number of entities
'''


def _demo_test_cases(topic: dict) -> str:
    cn = topic["class_name"]
    mn = topic["manager_name"]
    return f'''import pytest
from datetime import datetime, timedelta


class {cn}:
    """Minimal {cn} for testing."""
    def __init__(self, id, name, description="", category="default"):
        self.id = id
        self.name = name
        self.description = description
        self.status = "active"
        self.category = category
        self.created_at = datetime.now()
        self.updated_at = None

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

    def deactivate(self):
        self.status = "inactive"
        self.updated_at = datetime.now()

    def is_active(self):
        return self.status == "active"


class {mn}:
    """Minimal {mn} for testing."""
    def __init__(self):
        self._items = {{}}
        self._next_id = 1

    def create(self, name, description="", category="default"):
        if not name.strip():
            raise ValueError("Name cannot be empty")
        item = {cn}(self._next_id, name, description, category)
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def get(self, item_id):
        return self._items.get(item_id)

    def list_all(self, status=None, category=None):
        items = list(self._items.values())
        if status:
            items = [i for i in items if i.status == status]
        if category:
            items = [i for i in items if i.category == category]
        return sorted(items, key=lambda i: i.created_at, reverse=True)

    def update(self, item_id, **kwargs):
        item = self._items.get(item_id)
        if item:
            item.update(**kwargs)
            return True
        return False

    def delete(self, item_id):
        return self._items.pop(item_id, None) is not None

    def search(self, query):
        q = query.lower()
        return [i for i in self._items.values() if q in i.name.lower() or q in i.description.lower()]

    def get_stats(self):
        items = list(self._items.values())
        categories = {{}}
        for i in items:
            categories[i.category] = categories.get(i.category, 0) + 1
        return {{"total": len(items), "active": sum(1 for i in items if i.status == "active"),
                "inactive": sum(1 for i in items if i.status == "inactive"), "categories": categories}}


class Test{cn}Creation:
    def test_defaults(self):
        item = {cn}(1, "Test Item")
        assert item.id == 1
        assert item.name == "Test Item"
        assert item.status == "active"
        assert item.updated_at is None

    def test_update(self):
        item = {cn}(1, "Test")
        item.update(name="Updated")
        assert item.name == "Updated"
        assert item.updated_at is not None

    def test_deactivate(self):
        item = {cn}(1, "Test")
        item.deactivate()
        assert item.status == "inactive"
        assert item.is_active() is False

    def test_is_active(self):
        item = {cn}(1, "Test")
        assert item.is_active() is True
        item.deactivate()
        assert item.is_active() is False


class Test{mn}:
    def test_create(self):
        mgr = {mn}()
        item = mgr.create("Item1", category="cat1")
        assert item.name == "Item1"
        assert item.category == "cat1"

    def test_create_empty_name_raises(self):
        mgr = {mn}()
        with pytest.raises(ValueError):
            mgr.create("  ")

    def test_get(self):
        mgr = {mn}()
        item = mgr.create("Item1")
        assert mgr.get(item.id) == item
        assert mgr.get(999) is None

    def test_list_filtered(self):
        mgr = {mn}()
        mgr.create("A", category="x")
        mgr.create("B", category="y")
        result = mgr.list_all(category="x")
        assert len(result) == 1

    def test_update(self):
        mgr = {mn}()
        item = mgr.create("Item1")
        assert mgr.update(item.id, name="Updated") is True
        assert mgr.update(999, name="Nope") is False

    def test_delete(self):
        mgr = {mn}()
        item = mgr.create("Item1")
        assert mgr.delete(item.id) is True
        assert mgr.delete(item.id) is False

    def test_search(self):
        mgr = {mn}()
        mgr.create("Alpha", description="first item")
        mgr.create("Beta", description="second item")
        assert len(mgr.search("alpha")) == 1
        assert len(mgr.search("item")) == 2
        assert len(mgr.search("zzz")) == 0

    def test_get_stats(self):
        mgr = {mn}()
        mgr.create("A", category="x")
        mgr.create("B", category="y")
        i3 = mgr.create("C", category="x")
        mgr.get(i3.id).deactivate()
        stats = mgr.get_stats()
        assert stats["total"] == 3
        assert stats["active"] == 2
        assert stats["inactive"] == 1
        assert stats["categories"]["x"] == 2
'''


def _demo_doc_analysis(topic: dict) -> str:
    desc = topic["module_desc"]
    spec = topic["raw_topic"]
    return f'''# Document Analysis Report — {desc}

## Executive Summary
The analyzed document describes a specification for **{desc}**. Below is a comprehensive
analysis of the requirements, architecture, risks, and recommendations.

## Original Content Summary
{spec[:500]}{'...' if len(spec) > 500 else ''}

## Key Findings

### 1. Functional Requirements
- **Core Operations**: CRUD operations with full lifecycle management
- **Data Validation**: Input sanitization and constraint enforcement
- **Search & Filter**: Query-based retrieval with multi-field filtering
- **Status Tracking**: Entity state management with timestamp auditing

### 2. Technical Architecture
- **Data Model**: Dataclass-based entities with type hints
- **Storage Pattern**: In-memory dictionary with auto-incrementing keys
- **API Design**: Method-based interface suitable for REST adaptation
- **Serialization**: Built-in to_dict() for JSON compatibility

### 3. Identified Gaps & Risks
- No persistent storage — data loss on process restart
- No authentication or authorization layer
- No input length/format validation beyond empty checks
- Missing pagination for list operations at scale
- No concurrent access protection (thread safety)

### 4. Recommendations
1. Add SQLite/PostgreSQL persistence layer with ORM (SQLAlchemy)
2. Implement JWT-based authentication middleware
3. Add comprehensive input validation (pydantic models)
4. Implement pagination with cursor-based approach
5. Add logging and monitoring (structured JSON logs)
6. Add rate limiting for API endpoints
7. Write integration tests with test database

## Complexity Assessment
- **Estimated Effort**: 3-5 developer-days for production-ready implementation
- **Risk Level**: Medium — well-scoped but needs infrastructure additions
- **Priority**: Persistence and auth should be addressed first
'''


def _demo_data_analysis(topic: dict) -> str:
    desc = topic["module_desc"]
    spec = topic["raw_topic"]
    return f'''"""Auto-generated data analysis script for: {desc}

Based on: {spec[:150]}{'...' if len(spec) > 150 else ''}
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

# --- Data Generation (simulating {desc} data) ---
np.random.seed(42)
n_records = 500

dates = [datetime(2024, 1, 1) + timedelta(days=int(d)) for d in np.random.uniform(0, 365, n_records)]
categories = np.random.choice(["Category_A", "Category_B", "Category_C", "Category_D"], n_records, p=[0.3, 0.25, 0.25, 0.2])
statuses = np.random.choice(["active", "completed", "pending", "archived"], n_records, p=[0.35, 0.30, 0.20, 0.15])
scores = np.random.normal(75, 15, n_records).clip(0, 100).round(1)
durations = np.random.exponential(5, n_records).round(1)

df = pd.DataFrame({{
    "record_id": range(1, n_records + 1),
    "date": dates,
    "category": categories,
    "status": statuses,
    "score": scores,
    "duration": durations,
}})

# --- Analysis ---
print("=" * 60)
print("DATA ANALYSIS REPORT: {desc.upper()}")
print("=" * 60)

# 1. Status Distribution
print("\\n--- Status Distribution ---")
status_counts = df["status"].value_counts()
print(status_counts)
print(f"Active Rate: {{(status_counts.get('active', 0) / len(df) * 100):.1f}}%")
print(f"Completion Rate: {{(status_counts.get('completed', 0) / len(df) * 100):.1f}}%")

# 2. Category Distribution
print("\\n--- Category Distribution ---")
print(df["category"].value_counts())

# 3. Score Statistics by Category
print("\\n--- Score Stats by Category ---")
print(df.groupby("category")["score"].agg(["mean", "std", "min", "max"]).round(2))

# 4. Duration Analysis
print("\\n--- Duration Stats by Status ---")
print(df.groupby("status")["duration"].agg(["mean", "median"]).round(2))

# 5. Monthly Trend
df["month"] = pd.to_datetime(df["date"]).dt.month
monthly = df.groupby("month").size()
print("\\n--- Monthly Record Trend ---")
print(monthly)

# 6. Correlation Analysis
print("\\n--- Score vs Duration Correlation ---")
corr = df[["score", "duration"]].corr().iloc[0, 1]
print(f"Pearson Correlation: {{corr:.3f}}")

# --- Visualization Dashboard ---
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("{desc} — Analytics Dashboard", fontsize=16, fontweight="bold")

# Chart 1: Status pie
status_counts.plot.pie(ax=axes[0, 0], autopct="%1.1f%%", startangle=90,
                       colors=["#4CAF50", "#2196F3", "#FF9800", "#9E9E9E"])
axes[0, 0].set_title("Status Distribution")
axes[0, 0].set_ylabel("")

# Chart 2: Score distribution by category
for cat in df["category"].unique():
    axes[0, 1].hist(df[df["category"] == cat]["score"], bins=20, alpha=0.6, label=cat)
axes[0, 1].set_title("Score Distribution by Category")
axes[0, 1].legend(fontsize=8)

# Chart 3: Monthly trend
monthly.plot(ax=axes[1, 0], marker="o", color="steelblue", linewidth=2)
axes[1, 0].set_title("Monthly Record Trend")
axes[1, 0].set_xlabel("Month")
axes[1, 0].grid(True, alpha=0.3)

# Chart 4: Score vs Duration scatter
axes[1, 1].scatter(df["duration"], df["score"], alpha=0.3, c="mediumpurple", s=10)
axes[1, 1].set_title(f"Score vs Duration (r={{corr:.2f}})")
axes[1, 1].set_xlabel("Duration")
axes[1, 1].set_ylabel("Score")

plt.tight_layout()
plt.savefig("analytics_dashboard.png", dpi=150, bbox_inches="tight")
print("\\nDashboard saved to analytics_dashboard.png")
'''


def _demo_general_qa(topic: dict) -> str:
    desc = topic["module_desc"]
    spec = topic["raw_topic"]
    return f"""Based on your question about **{desc}**, here is what I can tell you:

{spec[:300]}

**Key Points:**
- This is a broad topic that covers several important aspects
- The answer depends on the specific context and requirements
- For the most up-to-date information, I recommend checking authoritative sources

**Summary:**
The topic of {desc} is well-documented and widely discussed. The key takeaway is that understanding the fundamentals helps in making informed decisions. If you need more specific details, feel free to ask a follow-up question.

*Note: This is a demo response. Connect to Ollama, Groq, or Gemini for real AI-generated answers.*"""


async def _demo_response(system_prompt: str, user_prompt: str) -> str:
    """Generate contextual demo responses based on the user's actual query."""
    await asyncio.sleep(0.3)  # Brief pause to simulate LLM latency
    topic = _extract_topic(user_prompt)
    prompt_lower = system_prompt.lower()

    if "model generator" in prompt_lower or "code generator" in prompt_lower:
        return _demo_code(topic)
    elif "test specification" in prompt_lower or "qa architect" in prompt_lower:
        return _demo_test_spec(topic)
    elif "test case" in prompt_lower or "test engineer" in prompt_lower:
        return _demo_test_cases(topic)
    elif "document" in prompt_lower or "analyzer" in prompt_lower:
        return _demo_doc_analysis(topic)
    elif "data" in prompt_lower or "analytics" in prompt_lower:
        return _demo_data_analysis(topic)
    elif "helpful ai assistant" in prompt_lower or "general" in prompt_lower:
        return _demo_general_qa(topic)
    elif "router" in prompt_lower or "classify" in prompt_lower:
        return "code_generator"
    return _demo_general_qa(topic)
