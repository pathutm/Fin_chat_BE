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

Open `.env` and fill in your credentials. `.env.example` lists every variable with a short note.

---

### 5. Create the agents (once, and after every prompt or skill change)
The three agents are files: `agents/coordinator.md` (Coordination Agent, with the other two in its multiagent roster), `agents/finance.md` (Finance Agent, with the skills in `agents/skills/`) and `agents/general.md` (General Agent). Sync them with the [`ant` CLI](https://github.com/anthropics/anthropic-cli/releases) (1.30.0 or later); applying the coordinator also applies the files it references:

```bash
ant apply --dry-run -v agents/coordinator.md   # review the plan
ant apply agents/coordinator.md                # create/update all three agents and upload the skills
```

This writes `claude-lock.json` (commit it). The server reads the agent IDs from there, or from `COORDINATION_AGENT_ID` / `FINANCE_AGENT_ID` / `GENERAL_AGENT_ID` in `.env`. Each later `ant apply` creates a new agent version instead of a new agent.

---

### 6. Database setup (once)
Conversation sessions are stored in Supabase:

```sql
create table if not exists conversation_sessions (
  conversation_id text primary key,
  session_id text,
  last_dataset text,
  created_at timestamptz default now(),
  updated_at timestamptz
);
```

---

### 7. Run the Server
```bash
python3 -m uvicorn app:app --reload
```
The backend API will run at **`http://127.0.0.1:8000`**.

---

## 🧪 Architecture & Guardrails
- **Multi-Agent Coordination:** Orchestrates Coordination Agent, Finance Agent, and General Agent with Claude Tool Calling.
- **MCP Database Connection:** Executes live Supabase SQL queries securely through Model Context Protocol (MCP).
- **Input/Output Guardrails:** Uses NVIDIA Nemotron 3.5 Content Safety and Groq for input classification and PII scrubbing.

### Token usage optimizations
- **Agents created once:** The three agents are defined in `agents/*.md` and synced with `ant apply`, which versions them instead of creating new agents on every server start.
- **Coordinator relay:** When a sub-agent's report already answers the question, the Coordination Agent relays it instead of rewriting it, so the answer is generated once.
- **Skills on demand:** The 10 finance playbooks in `agents/skills/` are attached to the Finance Agent as Skills and loaded only when a question needs one.
- **One session per conversation:** The platform keeps history with prompt caching and compaction; after 5 idle minutes a fresh session starts with the last 3 messages. Each session has a spend cap (`SESSION_BUDGET_CENTS`).
- **Small SQL results:** At most 100 rows and 3 queries per question; only the rows are sent to the model, in a compact format, with amounts converted to USD. MCP itself runs on the backend and uses no Claude tokens.
- **No model call** for greetings and chart follow-ups.
