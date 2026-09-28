# AI Nexus Orchestrator - Setup Guide

## Quick Start (5 Minutes)

### Step 1: Get Free Groq API Key (Recommended)
1. Visit https://console.groq.com/keys
2. Sign up (free, no credit card required)
3. Click "Create API Key"
4. Copy your key (starts with `gsk_`)

### Step 2: Configure Environment
Open `.env` file and paste your API key:
```bash
LLM_PROVIDER=groq
LLM_API_KEY=gsk_your_key_here  # Paste your key here
LLM_MODEL=llama-3.1-8b-instant
DEMO_MODE=false
```

### Step 3: Install Dependencies
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install packages (if not already installed)
pip install -r requirements.txt
```

### Step 4: Start Server
```bash
python run.py
```

Server starts at: **http://localhost:8080**

### Step 5: Test It
Open http://localhost:8080 in your browser and try:
- **Q&A**: "Who is the current Prime Minister of India?"
- **Code**: "Generate a Python function to calculate factorial"
- **Analysis**: Upload a document and ask "Analyze this"

Expected response time: **2-3 seconds** ⚡

---

## Alternative Providers

### Option 1: Gemini (Google - Free)
```bash
# Get key from https://aistudio.google.com/apikey
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_key_here
LLM_MODEL=gemini-2.0-flash-lite
```

### Option 2: Ollama (Local - Private)
```bash
# Install Ollama from https://ollama.com
ollama pull llama3.1:8b

# Configure .env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
LLM_BASE_URL=http://localhost:11434/v1
```

### Option 3: Fallback Chain (Best Reliability)
```bash
LLM_PROVIDER=groq
LLM_API_KEY=gsk_your_groq_key
LLM_FALLBACK_PROVIDERS=ollama  # Falls back to Ollama if Groq fails
```

---

## Troubleshooting

### Issue: "Connection refused" or slow responses
**Solution**: Check if you're using Groq (fast) vs Ollama (slow on CPU)
```bash
# Verify in .env:
LLM_PROVIDER=groq  # Should be groq, not ollama
```

### Issue: "API key required"
**Solution**: Make sure your API key is in `.env`:
```bash
LLM_API_KEY=gsk_your_actual_key_here  # Don't use placeholder
```

### Issue: Port 8000 already in use
**Solution**: Server now uses port 8080 by default
```bash
# Access at: http://localhost:8080
```

### Issue: Zombie processes on port 8000
**Solution**: Kill all Python processes and restart
```powershell
Get-Process -Name python | Stop-Process -Force
python run.py
```

---

## Testing the POC

### Test 1: Speed Test
```
Query: "What is Python?"
Expected: 2-3 second response
If slower: Check LLM_PROVIDER is set to "groq" not "ollama"
```

### Test 2: Code Generation
```
Query: "Generate a C++ hello world program"
Expected: Clean code in 3 seconds, single stage execution
```

### Test 3: File Upload
```
1. Click "Upload Document"
2. Drag/drop any PDF or text file
3. Ask: "Summarize this document"
Expected: Analysis in 3-5 seconds
```

### Test 4: Cache Test
```
1. Ask any question
2. Ask the same question again
Expected: Second response is instant (cached)
```

---

## API Endpoints

### Health Check
```bash
curl http://localhost:8080/api/health
```

### Get Available Models
```bash
curl http://localhost:8080/api/models
```

### Route Query (Test Routing)
```bash
curl -X POST http://localhost:8080/api/route \
  -H "Content-Type: application/json" \
  -d '{"query": "Generate Python code"}'
```

### Execute Pipeline
```bash
curl -X POST http://localhost:8080/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AI?"}'
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_PROVIDER` | Primary LLM provider | `groq`, `gemini`, `ollama` |
| `LLM_API_KEY` | API key for provider | `gsk_...` |
| `LLM_MODEL` | Model to use | `llama-3.1-8b-instant` |
| `LLM_BASE_URL` | Custom endpoint (optional) | `http://localhost:11434/v1` |
| `LLM_FALLBACK_PROVIDERS` | Comma-separated fallbacks | `ollama,gemini` |
| `DEMO_MODE` | Use simulated responses | `true` or `false` |

### Domain Max Tokens

Configured in `app/config.py`:
```python
DOMAIN_MAX_TOKENS = {
    "code_generator": 2048,   # Code generation
    "test_engineer": 2048,    # Test creation
    "doc_analyzer": 1024,     # Document analysis
    "data_analytics": 2048,   # Data analysis
    "general_qa": 512,        # Q&A (faster)
    "router": 32,             # Routing (instant)
}
```

---

## Performance Benchmarks

### Response Times (with Groq)
- General Q&A: **2s**
- Code Generation: **3s** (1 stage)
- Document Analysis: **3s**
- Data Analytics: **4s**
- Cached Queries: **<0.1s**

### Comparison vs Ollama (Local)
- General Q&A: 120s → **2s** (60x faster)
- Code Generation: 300s → **3s** (100x faster)

---

## Next Steps

1. ✅ **Get Groq API key** and configure `.env`
2. ✅ **Start server** with `python run.py`
3. ✅ **Test all 5 models** (Code, Test, Doc, Data, Q&A)
4. ✅ **Try file upload** with documents/images
5. ✅ **Verify caching** by repeating queries
6. 📋 **Share feedback** for production roadmap

---

## Support

**Project Location**: `c:\Users\40043862\workspace\ai-nexus-orchestrator`

**Key Files**:
- `.env` - Configuration
- `run.py` - Server entry point
- `app/main.py` - FastAPI application
- `app/llm_client.py` - LLM interface
- `PROJECT_DOCUMENTATION.md` - Full documentation

**Common Issues**:
- Slow responses → Use Groq, not Ollama
- Connection errors → Check API key in `.env`
- Port conflicts → Server uses 8080, not 8000
- Cache not working → Check `reload_settings()` in startup

---

## Demo Mode (No API Key Needed)

For testing without an API key:
```bash
DEMO_MODE=true
LLM_PROVIDER=ollama  # Ignored in demo mode
```

Demo mode returns simulated responses instantly (0.3s delay).
