# 🌌 Deep Research Agent 2.0

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg)](https://reactjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange.svg)](https://github.com/langchain-ai/langgraph)

**An Autonomous Multi-Agent Deep Research & Synthesis Engine**

[简体中文文档 (Chinese)](README-ZH.md) | [English Documentation](README.md)

</div>

---

## 📖 Introduction

**Deep Research Agent 2.0** is an enterprise-grade autonomous multi-agent deep research and report synthesis platform. Powered by **LangGraph StateGraph**, real-time multi-source web intelligence, **Hybrid Local Document RAG**, **Critic reflection recursion**, **Map-Reduce fact compression**, and **100% anti-hallucination citation verification**, it transforms ambiguous research topics into comprehensive, editorial-grade intelligence reports in minutes.

---

## ✨ Key Capabilities & System Architecture

### 1. Multi-Agent Collaborative StateGraph Pipeline
```
[User Query + Local Docs] 
        ↓
    [Planner] ──────→ (Dynamic 2~8 Chapters Outline)
        ↓
[Human-in-the-Loop] ─→ (User Reviews, Adds, Modifies Chapters)
        ↓
  [Researcher] ─────→ (Concurrent Web Search + Local Chunk RAG)
        ↓
 [Summarizer] ──────→ (Map-Reduce 500-token Fact Compression)
        ↓
   [Critic] ────────→ (Fact Verification & Deficiency Reflection Loop)
        ↓ (Needs more info? Iteration <= Max Limit)
    [Writer] ───────→ (Synthesizes Editorial-Grade Report & Tables)
        ↓
   [Verifier] ──────→ (1:1 Regex Citation Verification & Hallucination Elimination)
        ↓
[Final Publication & Interactive UI]
```

* 🎯 **Planner Agent**: Dynamically generates 2~8 structured chapters according to chosen depth mode (Quick, Standard, Exhaustive).
* 🔍 **Researcher Agent**: Concurrently retrieves live web sources (DuckDuckGo / Tavily) and local private document chunks.
* 🧠 **Summarizer Agent**: Compresses 10,000+ token raw webpages into 500-token high-density fact cards with unique `source_id`.
* 🔄 **Critic Agent**: Autonomously inspects fact completeness and contradictions; triggers secondary targeted deep searches with strict pruning.
* ✍️ **Writer Agent**: Synthesizes formal analytical reports featuring executive summaries, comparative tables, and strategic implications.
* 🛡️ **Verifier Agent**: Enforces 1:1 regex verification across all citations `[N]`, eliminating hallucinated sources.

---

### 2. Hybrid Local Document RAG
* Upload private proprietary documents (`.pdf`, `.docx`, `.txt`, `.md`).
* Automatically extracts and parses text into semantic chunks.
* Agent seamlessly blends private company knowledge with live open-web facts, generating hybrid references tagged as `[Local Document: filename]` and `[Web Source: domain]`.

---

### 3. Human-in-the-Loop (HITL) Outline Collaboration
* Research pauses after outline generation, allowing users to edit titles, adjust research focus, add custom chapters, or delete sections before resuming.

---

### 4. Editorial-Grade Web UI with 4 Curated Themes & Bilingual i18n
* 🌐 **Bilingual (English / 简体中文)**: Instant one-click switch across the entire interface.
* 🎨 **4 Visual Themes**:
  - 📜 **Vintage Antique (古色古香)**: Song Dynasty parchment (`#f4ecd8`), Chinese ink (`#2a1d0f`), and cinnabar red (`#b91c1c`).
  - ☀️ **Crisp Light (极简明亮)**: Minimalist pure snow white and royal blue.
  - 🌲 **Aurora Emerald (翡翠极光)**: Nordic forest green and mint emerald.
  - 🌌 **Deep Space Dark (深空暗夜)**: Cyberpunk dark blue and electric indigo.
* 📑 **True Sticky Scroll-Spy TOC**: Follows user scrolling with real-time active section highlighting and smooth scrolling.
* 🔍 **Citation Hover Cards (Hover to Peek, Click to Pin)**: Floating glassmorphism cards with domain, trust score, evidence snippets, and external links.
* ✨ **Highlight-to-Deep-Dive & Live Q&A**: Select any text to trigger targeted deep reasoning powered by DeepSeek LLM.

---

### 5. Multi-Format Export Engine & Mindmap
* 📑 **Microsoft Word (`.docx`)**: Clean office document layout with headings, bullet points, and citations.
* 📝 **Markdown (`.md`)**: Complete raw source with structured markdown tables.
* 🖨️ **Printable PDF**: Clean A4 print layout ready for one-click Save as PDF.
* 🧠 **Interactive Mindmap Canvas**: Full panoramic tree view with collapsible nodes.

---

## 📁 Repository Structure

```
demo5/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── state.py            # LangGraph core schema
│   │   │   ├── planner.py          # Dynamic outline planner
│   │   │   ├── researcher.py       # Hybrid RAG & web search agent
│   │   │   ├── summarizer.py       # Map-Reduce fact compressor
│   │   │   ├── critic.py           # Reflection & pruning node
│   │   │   ├── writer.py           # Report synthesis node
│   │   │   └── verifier.py         # 1:1 Citation verifier
│   │   ├── tools/
│   │   │   ├── search_tools.py     # DDGS & Tavily search tools
│   │   │   ├── scrape_tools.py     # Jina Reader web scraper
│   │   │   ├── doc_parser.py       # PDF/Word/TXT document chunker
│   │   │   └── memory_store.py     # Session vector memory store
│   │   ├── services/
│   │   │   └── task_manager.py     # Async lifecycle & SSE broadcast
│   │   ├── api/v1/
│   │   │   └── research.py         # RESTful & SSE endpoints
│   │   └── main.py                 # FastAPI app & static file mount
│   ├── tests/                      # 22 automated unit/integration tests
│   ├── run.py                      # Smart backend starter with port detection
│   └── cli.py                      # Terminal CLI entry point
├── frontend/
│   ├── src/
│   │   ├── components/             # React UI components
│   │   │   ├── CommandHero.tsx     # Hero command console & file upload
│   │   │   ├── OutlineCanvas.tsx   # HITL outline editor
│   │   │   ├── BentoRadarDashboard.tsx # 3-column live Bento grid
│   │   │   ├── ReportViewer.tsx    # Editorial report reader
│   │   │   ├── CitationPopover.tsx # Floating citation card
│   │   │   ├── FollowUpDrawer.tsx  # Live Q&A chat drawer
│   │   │   ├── MindmapModal.tsx    # Interactive mindmap modal
│   │   │   ├── ExportModal.tsx     # Multi-format export dialog
│   │   │   ├── ThemeSelector.tsx   # 4-Theme switcher
│   │   │   └── LanguageSelector.tsx# Bilingual language switcher
│   │   ├── locales/
│   │   │   └── translations.ts     # Bilingual translation dictionary
│   │   └── index.css               # CSS variables & typography
│   └── package.json
├── README.md                       # English documentation
└── README-ZH.md                    # 简体中文文档
```

---

## 🚀 Quickstart

### 1. Prerequisites
* Python 3.10+
* Node.js 18+

### 2. Configure & Start Backend
```bash
cd backend

# Configure your LLM API credentials (or create a .env file)
export TASK_LLM_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
export TASK_LLM_BASE_URL="https://api.deepseek.com"
export TASK_LLM_MODEL="deepseek-chat"

# Launch backend (Automatically detects ports and mounts frontend)
python3 run.py
```

### 3. Access in Browser
Navigate to **`http://localhost:8080`** (or the port displayed in your terminal).

---

## 🧪 Testing

```bash
cd backend
python3 -m pytest tests/ -v
```
All 22 automated tests covering tools, reflection pruning, citation verification, document parsing, and SSE streaming will execute and pass.

---

## 📄 License
This project is licensed under the MIT License.
