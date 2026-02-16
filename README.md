<p align="center">
  <a href="https://ewala.es/#elias">
    <img src="librechat/client/public/assets/logo-lucia.png" height="128">
  </a>
</p>
<p align="center"><strong>Learning Urban Cognitive Intelligence for Autonomous Buildings</strong></p>
<p align="center">
  <a href="https://ewala.es/">
    <img src="librechat/client/public/assets/EWALA.png" height="40">
  </a>
</p>


---

## 🧠 What is LUCIA?

**LUCIA** is an open-source, local-first, multi-agent AI platform designed for **autonomous decision-making, energy optimization, and intelligent environment control**.

It combines:
- Conversational AI (LibreChat)
- Agentic reasoning (LangChain)
- Vision-based contextual understanding (Vision LLMs)
- Real-world actuation (Home Assistant)
- Governance, evaluation, and rule generation (Setup Wizard)

LUCIA is built to run **fully on-premise**, using **local LLMs via Ollama**, and is designed for **edge, industrial, and privacy-sensitive environments**.

---

## 🧭 Design Principles

- Local-first and privacy-preserving by default
- Explainability over black-box automation
- Human-in-the-loop governance
- Modular, replaceable components
- Edge-ready, cloud-optional

---

## 🎯 Target Use Cases

- Smart buildings & energy optimization
- Industrial automation
- Research & experimentation
- Edge AI deployments (Edge ≠ “Raspberry Pi”)
- Privacy-first AI systems
- Human-in-the-loop autonomous systems

---

## ✨ Core Features

### 🤖 Multi-Agent Architecture
- Autonomous AI agents powered by **LangChain**
- Clear separation of responsibilities:
  - Decision-making agents
  - Evaluation agents
  - Rule-generation agents
  - Chat-driven command agents
- Agents can:
  - Analyze structured data
  - Consume sensor history
  - Use vision-based context
  - Generate explainable decisions
  - Propose and manage automation rules

---

### 💬 Conversational Interface (LibreChat)
- LibreChat as the **main UI**
- Native support for:
  - MCP (Model Context Protocol)
  - Tool calling
  - Streaming responses
- Agents are exposed to the chat via MCP servers
- Users can **interact directly with agents** as first-class chat participants

---

### 🔌 MCP-Driven Integration
LUCIA makes extensive use of **Model Context Protocol (MCP)**:

- **LangChain Agent MCP**
  - Exposes the agent system to LibreChat
  - Enables chat-driven actions and reasoning

- **Home Assistant MCP**
  - Allows agents to read sensor data
  - Enables agents to trigger real-world actions

This architecture keeps LUCIA modular, extensible, and future-proof.

---

### 👁️ Vision-Aware Intelligence
- Vision LLM integration via **Home Assistant HAC (VisionLLM)**
- Vision agents can:
  - Analyze images
  - Generate semantic scene descriptions or JSON Response.
  - Persist contextual knowledge as HA entities
- Enables reasoning like:
  > “The room is empty, lights are on, and sunlight is sufficient.”

---

### 🧩 Setup Wizard (Governance)
The Setup Wizard is a dedicated UI and backend for **governing AI behavior**:

- Select entities of interest (sensors, zones, devices)
- Review AI-generated decisions
- Score and evaluate agent behavior
- Automatically generate rules based on evaluations
- Manage rules created by:
  - Human users
  - Evaluation agents
  - Chat-command agents

This provides **human-in-the-loop control** over autonomous systems.

---

## 🏗️ High-Level Architecture

```
User
 ↓
LibreChat
 ↓
MCP Servers
 ├─ LangChain MCP
 └─ Home Assistant MCP
 ↓
LangChain Backend
 ↓
Ollama (Local LLMs)
 ↓
Decisions / Rules
 ↓
Home Assistant (Execution)
```
All components are orchestrated using **Docker Compose**.

---

## 🧪 Model Strategy

LUCIA supports two deployment modes for Ollama:

### 🔹 Single-Model Mode (Not Recommended)
- One model handles:
  - Reasoning
  - Tool calling
  - Vision
- Useful for demos or constrained hardware

Example:
```
aliafshar/gemma3-it-qat-tools:12b
```


### 🔹 Dual-Model Mode (Recommended)

| Purpose | Model | VRAM |
|------|------|------|
| Reasoning & tools | gemma3-it-qat-tools:12b | ~12–13 GB |
| Vision | qwen2.5vl:7b | ~8–9 GB |

Minimum recommended VRAM: **24 GB**.

---

## 🧰 Technology Stack

### Frontend
- LibreChat Client (Vite + React + TypeScript)
- Setup Wizard Frontend (Vite + React)

### Backend
- LibreChat API (Next.js)
- LangChain Backend (FastAPI)
- LangChain MCP (FastMCP)
- Setup Wizard Backend (Flask + Gunicorn)

### Infrastructure
- Docker & Docker Compose
- MongoDB (LibreChat)
- PostgreSQL + pgvector (RAG)
- SQLite (decisions, rules, governance)
- MeiliSearch (search & indexing)

### Core Components and Licenses

| Component | Description | Technology | License |
|--------|------------|-----------|---------|
| LibreChat Client | Conversational web interface | React, Vite | MIT |
| LibreChat API | Backend for chat, auth, models, MCP | Node.js / Next.js | MIT |
| LangChain Backend | Agentic reasoning and decision engine | Python, FastAPI, LangChain | MIT |
| LangChain MCP | MCP server exposing agents to LibreChat | FastMCP | MIT |
| Setup Wizard Frontend | Governance & evaluation UI | React, Vite | MIT |
| Setup Wizard Backend | Rules, decisions & governance API | Python, Flask | MIT |
| Ollama | Local LLM and Vision inference engine | Go | Apache 2.0 |
| VisionLLM HAC | Vision integration for Home Assistant | Python | Apache 2.0 |
| Home Assistant | Building automation platform | Python | Apache 2.0 |
| MongoDB | LibreChat persistence | MongoDB | SSPL / MongoDB License |
| PostgreSQL | Relational & vector DB | PostgreSQL + pgvector | PostgreSQL License |
| MeiliSearch | Search & indexing engine | Rust | MIT |
| Docker & Docker Compose | Container orchestration | Docker | Apache 2.0 |

> ⚠️ Note on licensing  
> While LUCIA itself is released under the MIT License, it integrates
> third-party components that are distributed under their own licenses.
> Users are responsible for ensuring compliance with all applicable licenses,
> especially when deploying in commercial or production environments.

---

## 📂 Project Structure (Simplified)
```
.
├── docker-compose.yml
├── env/
│ ├── lucia.env
│ └── librechat.env
├── librechat/
├── services/
│ ├── lang_chain_backend/
│ └── setup-wizard-microservice/
├── db/
├── docker/
└── README.md
```

---

## 🚀 Deployment (Summary)

1. Install Docker & Docker Compose
2. Install and run Ollama on the host or a GPU node
3. Configure environment files:
   - `.env`
   - `env/lucia.env`
   - `env/librechat.env`
   - `librechat/librechat.yaml`
4. Build and start:
   ```bash
   docker compose build
   docker compose up -d
   ```

---

## 🔐 Security
- Default deployment uses HTTP (local/dev)

- Production deployments should include:
    - Reverse proxy (Nginx or Traefik)
    - TLS certificates (Let’s Encrypt)
    - Firewall rules
    - Secure Home Assistant tokens
    - Regular backups of volumes

---

## 📜 License

This project is licensed under the **MIT License**.  
See the [LICENSE](LICENSE) file for details.

---

> ⚠️ This repository focuses on orchestration and integration.  
> Hardware provisioning, GPU drivers, and Home Assistant setup are assumed to be managed externally.