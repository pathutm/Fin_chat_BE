# Finance AI Chatbot - Backend (FastAPI)

FastAPI-powered Multi-Agent backend for CFO Conversational Analytics & Working Capital Intelligence.

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.10+ (Recommended: Python 3.12)
- Node.js 18+ (for Frontend)

---

### 2. Setup Virtual Environment
From the `Fin_chat_BE` directory:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows (Command Prompt):
# venv\Scripts\activate.bat
# On Windows (PowerShell):
# venv\Scripts\Activate.ps1
```

---

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_ENVIRONMENT_ID=your_anthropic_environment_id
SUPABASE_PROJECT_REF=your_supabase_project_ref
SUPABASE_ACCESS_TOKEN=your_supabase_access_token
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
NVIDIA_API_KEY=your_nvidia_api_key
GROQ_API_KEY=your_groq_api_key
```

---

### 5. Run the Server
```bash
python3 -m uvicorn app:app --reload
```
The backend API will run at **`http://127.0.0.1:8000`**.

---

## 🧪 Architecture & Guardrails
- **Multi-Agent Coordination:** Orchestrates Coordination Agent, Finance Agent, and General Agent with Claude Tool Calling.
- **MCP Database Connection:** Executes live Supabase SQL queries securely through Model Context Protocol (MCP).
- **Input/Output Guardrails:** Uses NVIDIA Nemotron 3.5 Content Safety and Groq for input classification and PII scrubbing.
