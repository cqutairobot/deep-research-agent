# 🌌 Deep Research Agent 2.0 (AI 深度知识调研系统)

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg)](https://reactjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange.svg)](https://github.com/langchain-ai/langgraph)

**基于多智能体自主协同的深度知识调研与研报生成系统**

[简体中文文档 (Chinese)](README-ZH.md) | [English Documentation](README.md)

</div>

---

## 📖 项目简介

**Deep Research Agent 2.0** 是一套面向复杂开放性命题的工业级多智能体深度知识调研系统。系统基于 **LangGraph 状态机**、**全网多源实时检索**、**本地私有文档混合 RAG**、**Critic 反思递归纠错**、**Map-Reduce 事实压缩**与 **100% 引用防幻觉核验机制**，能够在数分钟内自主完成从大纲规划、事实搜集、交叉验证到生成带精准溯源引用的出版级深度行业研报。

---

## ✨ 核心特性与架构亮点

### 1. 多智能体状态图协同流水线 (Multi-Agent StateGraph Pipeline)
```
[用户课题 + 本地文档] 
        ↓
    [Planner] ──────→ (自主规划 2~8 个章节大纲)
        ↓
[人机协同确认] ─→ (人工编辑、增删章节与侧重点)
        ↓
  [Researcher] ─────→ (并发调度全网检索 + 本地私有文档切片)
        ↓
 [Summarizer] ──────→ (Map-Reduce 压缩 500 字高密度事实卡片)
        ↓
   [Critic] ────────→ (事实充实度评估与缺失矛盾反思循环)
        ↓ (事实不足？触发下一轮精准深搜，受最大轮次剪枝保护)
    [Writer] ───────→ (撰写出版级研报、数据对比表格与战略洞察)
        ↓
   [Verifier] ──────→ (1:1 严格正则核验 [N] 引用，消灭虚构文献)
        ↓
[最终出版交付与交互界面]
```

* 🎯 **Planner 战略规划节点**：根据快速/标准/穷尽深度模式，自主动态拆解 2~8 个逻辑递进的章节大纲；
* 🔍 **Researcher 知识搜集节点**：并发执行 DuckDuckGo / Tavily 实时搜索与本地文档切片检索；
* 🧠 **Summarizer 事实压缩节点**：将万字长网页压缩为 500 字高密度事实卡片并分配唯一 `source_id`；
* 🔄 **Critic 反思评估节点**：自主评估事实充实度与矛盾，自动生成二阶检索词触发循环，带最大迭代轮数安全剪枝；
* ✍️ **Writer 研报合成节点**：结构化撰写宏观执行摘要、定量对比表格、微观机理与战略建议；
* 🛡️ **Verifier 引用核验节点**：1:1 严格正则匹配核验正文所有 `[N]` 引用，消灭张冠李戴与伪造信源。

---

### 2. 本地私有知识库混合检索 (Hybrid Local RAG)
* 支持上传本地专有研报、财报、论文或专利（支持 `.pdf`, `.docx`, `.txt`, `.md` 格式）；
* 自动进行文本清洗与语义切片（每段约 500 字符）；
* Agent 自动将私有知识与全网实时检索动态交织，在报告中生成 `[本地专有文档: 文件名]` 与 `[网络信源: 域名]` 复合引证。

---

### 3. 人机协同大纲确认 (Human-in-the-Loop)
* 大纲生成后自动挂起，支持用户在界面上任意编辑章节标题、调整侧重点、新增或删除章节，一键确认后恢复 Agent 自主执行。

---

### 4. 出版级多主题与中英文双语界面
* 🌐 **中英文一键无缝切换 (CN / EN)**：导航栏一键切换全站语言；
* 🎨 **4 套精选主题**：
  - 📜 **古色古香 (Vintage Antique)**：宋代古籍宣纸米黄 (`#f4ecd8`)、徽墨浓黑 (`#2a1d0f`)、御制朱砂红 (`#b91c1c`)；
  - ☀️ **极简明亮 (Crisp Light)**：纯净雪白与皇家蓝；
  - 🌲 **翡翠极光 (Aurora Emerald)**：北欧苍翠墨绿与薄荷青绿；
  - 🌌 **深空暗夜 (Deep Space Dark)**：极客深蓝与霓虹电光；
* 📑 **真吸顶目录 (Sticky Scroll-Spy TOC)**：目录常驻左侧，随阅读位置实时高亮当前章节，支持平滑滚动直达；
* 🔍 **悬浮引证毛玻璃卡片 (Hover & Pin)**：鼠标悬停预览引证段落与置信度，点击锁定常驻，一键直达原始网页；
* ✨ **划词深挖与即时追问 (Deep-Dive & Live Q&A)**：划选任意段落唤醒 DeepSeek 大模型进行针对性深度推理。

---

### 5. 多格式导出引擎与可视化思维导图
* 📑 **Microsoft Word (`.docx`)**：标准办公排版格式输出，保留分级标题、列表与引用标记；
* 📝 **Markdown 源码 (`.md`)**：完整结构化源码与数据表格；
* 🖨️ **出版级 PDF**：洁净 A4 打印预览版面，一键另存为 PDF；
* 🧠 **交互式思维导图画布**：全景层级树状浏览，支持节点展开与折叠。

---

## 📁 项目目录结构

```
demo5/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── state.py            # LangGraph 核心状态 Schema
│   │   │   ├── planner.py          # 动态章节大纲规划节点
│   │   │   ├── researcher.py       # 混合 RAG 与网络检索节点
│   │   │   ├── summarizer.py       # Map-Reduce 网页长文压缩器
│   │   │   ├── critic.py           # 反思递归与评估剪枝节点
│   │   │   ├── writer.py           # 研报合成撰写节点
│   │   │   └── verifier.py         # 引用防幻觉 1:1 核验节点
│   │   ├── tools/
│   │   │   ├── search_tools.py     # DDGS 与 Tavily 搜索工具
│   │   │   ├── scrape_tools.py     # Jina Reader 网页清洗工具
│   │   │   ├── doc_parser.py       # 本地 PDF/Word/TXT 切片解析器
│   │   │   └── memory_store.py     # 临时会话向量与 BM25 索引库
│   │   ├── services/
│   │   │   └── task_manager.py     # 异步任务生命周期与 SSE 广播
│   │   ├── api/v1/
│   │   │   └── research.py         # RESTful 与 SSE 路由接口
│   │   └── main.py                 # FastAPI 应用入口与静态前端托管
│   ├── tests/                      # 22 项自动化单元与集成测试
│   ├── run.py                      # 智能端口防碰撞后端启动脚本
│   └── cli.py                      # 终端 CLI 交互入口
├── frontend/
│   ├── src/
│   │   ├── components/             # React 现代化组件库
│   │   │   ├── CommandHero.tsx     # 课题输入与本地文档上传中心
│   │   │   ├── OutlineCanvas.tsx   # 大纲协同编辑画布
│   │   │   ├── BentoRadarDashboard.tsx # 调研进度三栏雷达
│   │   │   ├── ReportViewer.tsx    # 出版级研报阅读器
│   │   │   ├── CitationPopover.tsx # 悬浮引证毛玻璃卡片
│   │   │   ├── FollowUpDrawer.tsx  # 真实大模型即时追问抽屉
│   │   │   ├── MindmapModal.tsx    # 交互式思维导图
│   │   │   ├── ExportModal.tsx     # 多格式导出弹窗
│   │   │   ├── ThemeSelector.tsx   # 4 套色彩主题切换器
│   │   │   └── LanguageSelector.tsx# 中英文语言切换器
│   │   ├── locales/
│   │   │   └── translations.ts     # 中英文双语语言包
│   │   └── index.css               # 主题 CSS 变量与出版级排版规则
│   └── package.json
├── README.md                       # 英文说明文档
└── README-ZH.md                    # 简体中文说明文档
```

---

## 🚀 快速启动指南

### 1. 环境准备
* Python 3.10+
* Node.js 18+

### 2. 配置与启动后端
```bash
cd backend

# 配置大模型 API 凭证 (或在 backend/.env 中配置)
export TASK_LLM_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
export TASK_LLM_BASE_URL="https://api.deepseek.com"
export TASK_LLM_MODEL="deepseek-chat"

# 启动后端服务 (自动检测可用端口并自动托管前端)
python3 run.py
```

### 3. 打开浏览器访问
在浏览器中打开 **`http://localhost:8080`**（或控制台打印的端口号）即可开始深度调研！

---

## 🧪 自动化测试套件

```bash
cd backend
python3 -m pytest tests/ -v
```
所有 22 项测试均可稳定通过：
* API 端点与 SSE 流式生成 (`test_api.py`)
* 本地文档切片与解析器 (`test_doc_parser.py`)
* 引用防幻觉与 1:1 溯源 (`test_verifier.py` & `test_citation_accuracy.py`)
* Critic 反思与迭代剪枝 (`test_critic.py`)
* 多智能体状态图全流程 (`test_graph.py`)
* 工具层与 Map-Reduce 压缩 (`test_tools.py` & `test_summarizer.py`)

---

## 📄 开源许可证
本项目基于 MIT License 开源。
