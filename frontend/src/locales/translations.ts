export type Language = 'zh' | 'en';

export const translations = {
  zh: {
    // Navbar
    nav: {
      title: 'Deep Research',
      version: 'Agent 2.0',
      subtitle: '多智能体自主深度知识调研系统',
      step1: '需求配置',
      step2: '大纲协同',
      step3: '实时调研',
      step4: '深度研报',
      liveSse: 'LIVE SSE',
      newResearch: '新建调研',
      theme: '主题配色',
      lang: '语言 / Language'
    },
    // CommandHero
    hero: {
      badge: '自主多智能体全网深度调研 + 本地混合 RAG',
      title: '你想深度调研什么课题？',
      subtitle: 'Agent 将自主规划多层级大纲、融合本地私有文档与全网实时检索、交叉验证事实并生成带精准溯源引用的深度研报。',
      placeholder: '输入任意开放式课题，例如：全球全固态电池商业化量产时间表、主流路线对比及主要厂商竞争壁垒...',
      launchHint: '启动',
      localDocsTitle: '本地专有文档混合 RAG (可选)：',
      localDocsHint: '支持上传 .pdf / .docx / .txt / .md',
      uploadBtn: '+ 上传本地文档',
      uploading: '正在解析...',
      chunks: '段切片',
      presetsTitle: '精选推荐课题：',
      presets: [
        { title: '⚡ 固态电池产业对比', text: '全球全固态电池商业化进展、主流技术路线（硫化物 vs 氧化物）及主要厂商量产壁垒对比' },
        { title: '🤖 具身智能与灵巧手', text: '2026年具身智能机器人灵巧手微电机驱动与腱绳传动技术对比及主要厂商量产落地进展' },
        { title: '✈️ 低空经济 eVTOL 适航', text: '全球 eVTOL 飞行汽车适航认证取证进展、三电系统供应链及主要中美厂商商业化时间表' },
        { title: '🧠 脑机接口临床进展', text: '侵入式与半侵入式脑机接口临床试验最新突破、信号解码算法与伦理监管框架' }
      ],
      depthLabel: '调研深度 (Search Depth)',
      depthQuick: '快速',
      depthStandard: '标准',
      depthDeep: '穷尽',
      styleLabel: '报告风格 (Report Style)',
      styleConsulting: '商业咨询',
      styleAcademic: '学术严谨',
      styleExecutive: '决策简报',
      footerInfo: '实时全网检索 + 深度推理',
      footerInfoHybrid: '实时全网检索 + {count} 份本地文档混合 RAG',
      submitBtn: '开始规划大纲',
      submittingBtn: '正在发起...'
    },
    // Outline
    outline: {
      statusBadge: 'AGENT 规划已就绪',
      title: '🎯 调研大纲已生成',
      hitlBadge: '等待人工协同确认 (Human-in-the-Loop)',
      addChapter: '添加章节',
      approveBtn: '确认大纲并启动调研',
      approvingBtn: '正在启动...',
      clarificationTitle: 'Agent 意图澄清与拆解：',
      focusLabel: '重点关注：',
      focusPlaceholder: '该章节核心要搜集的数据与指标...',
      queriesLabel: '规划检索词：',
      newChapterTitle: '新增调研章节：行业政策环境与市场渗透率预测',
      newChapterFocus: '梳理国家补贴标准、行业准入门槛与 2026~2030 年渗透率',
      newChapterQuery: '新增章节 政策 补贴 渗透率预测',
      minChapterAlert: '至少需要保留一个调研章节！'
    },
    // Radar Dashboard
    radar: {
      title: '深度调研雷达控制台',
      subtitle: '多智能体实时协作流水线',
      round: '第 {current}/{max} 轮反思迭代',
      tabThought: 'Agent 思考流',
      tabScrape: '网页抓取矩阵',
      tabFacts: '事实瀑布 & Critic 评估',
      emptyThought: '正在等待 Agent 输出思考流日志...',
      emptyScrape: '正在执行多源实时检索与动态抓取...',
      emptyFacts: '正在通过 Map-Reduce 压缩长文事实...',
      criticHeader: 'Critic 反思评估反馈',
      passBadge: '评估通过',
      needsMoreBadge: '需二阶深搜',
      sourceCitations: '累计收录可信信源：{count} 处'
    },
    // Report Viewer
    report: {
      badgeTitle: '出版级可信研报已生成',
      badgeSubtitle: '100% 来源真实可溯源 · 包含 {count} 处权威信源',
      copyFull: '复制全文',
      copied: '已复制全文',
      exportReport: '导出报告',
      mindmapBtn: '思维导图',
      liveQABtn: '即时追问会话',
      tocTitle: '研报导航目录',
      deepDiveTooltip: '针对此处深挖追问',
      citationVerified: '已核验证据',
      citationRelevance: '置信度',
      viewSource: '查看原始网页',
      pinHint: '悬浮查看信源，点击锁定'
    },
    // Follow up Drawer
    chat: {
      title: '研报即时追问对话',
      subtitle: '基于真实 DeepSeek 大模型 + 研报事实库深度解答',
      welcome: '你好！我已经完整掌握了本次调研的所有事实与研报内容。你可以随时针对细节、数据指标、研究结论或划词选段向我提问，我将通过真实 DeepSeek 大模型为你实时深度解答。',
      quickPrompt1: '📌 核心结论与建议',
      prompt1Text: '请总结这份研报的核心结论与三条关键建议。',
      quickPrompt2: '📊 定量数据梳理',
      prompt2Text: '研报中提到哪些关键数据指标和定量结论？',
      inputPlaceholder: '输入针对报告的追问或选段深挖...',
      thinking: 'DeepSeek 正在研读报告与事实库组织针对性回答...'
    },
    // Export Modal
    export: {
      title: '导出与分享深度研报',
      docxTitle: '下载 Microsoft Word 文档 (.docx)',
      docxDesc: '包含完整分级标题、原生数据表格与标准办公排版',
      docxGenerating: '正在生成 Word 文档...',
      mdTitle: '下载 Markdown 源码 (.md)',
      mdDesc: '保留原始 Markdown 结构、表格与文献溯源锚点',
      pdfTitle: '导出为出版级 PDF / 打印',
      pdfDesc: '生成纯净 A4 打印预览版面并一键另存为 PDF',
      mindmapJsonTitle: '下载思维导图数据结构 (.json)',
      mindmapJsonDesc: '可直接导入 XMind、ProcessOn 等脑图软件进行二次编辑',
      close: '关闭'
    },
    // Mindmap
    mindmap: {
      title: '交互式研报思维导图',
      subtitle: '全景树状知识层级 · 支持节点展开与折叠',
      exportJsonBtn: '导出脑图 JSON',
      tip: '提示：点击节点左侧箭头可折叠/展开任意分支',
      close: '关闭导图'
    },
    // Themes
    themes: {
      dark: '深空暗夜 🌌',
      vintage: '古色古香 📜',
      light: '极简明亮 ☀️',
      emerald: '翡翠极光 🌲'
    }
  },
  en: {
    // Navbar
    nav: {
      title: 'Deep Research',
      version: 'Agent 2.0',
      subtitle: 'Autonomous Multi-Agent Deep Knowledge Research System',
      step1: 'Configure',
      step2: 'Outline',
      step3: 'Live Research',
      step4: 'Report',
      liveSse: 'LIVE SSE',
      newResearch: 'New Research',
      theme: 'Color Theme',
      lang: 'Language / 语言'
    },
    // CommandHero
    hero: {
      badge: 'Multi-Agent Autonomous Research + Hybrid Local RAG',
      title: 'What topic would you like to explore deeply?',
      subtitle: 'The agent will autonomously plan outlines, blend local private files with live web searches, cross-validate facts, and produce fully cited editorial-grade reports.',
      placeholder: 'Enter any research query, e.g., Global solid-state battery commercialization timeline, sulfide vs oxide routes and OEM barriers...',
      launchHint: 'to start',
      localDocsTitle: 'Hybrid Local RAG (Optional):',
      localDocsHint: 'Supports .pdf / .docx / .txt / .md files',
      uploadBtn: '+ Upload Local Document',
      uploading: 'Parsing...',
      chunks: 'chunks',
      presetsTitle: 'Featured Topics:',
      presets: [
        { title: '⚡ Solid-State Batteries', text: 'Global solid-state battery commercialization timeline, sulfide vs oxide route comparison and key OEM manufacturing barriers' },
        { title: '🤖 Dexterous Robotic Hands', text: '2026 humanoid robot dexterous hands: micro-motor drive vs tendon transmission comparison and mass production roadmap' },
        { title: '✈️ eVTOL Airworthiness', text: 'Global eVTOL airworthiness certification progress, powertrain supply chain and US-China OEM commercialization schedules' },
        { title: '🧠 Brain-Computer Interfaces', text: 'Invasive and semi-invasive BCI clinical trials progress, neural decoding algorithms and regulatory frameworks' }
      ],
      depthLabel: 'Search Depth',
      depthQuick: 'Quick',
      depthStandard: 'Standard',
      depthDeep: 'Exhaustive',
      styleLabel: 'Report Style',
      styleConsulting: 'Consulting',
      styleAcademic: 'Academic',
      styleExecutive: 'Executive',
      footerInfo: 'Real-time Web Search + Deep Reasoning',
      footerInfoHybrid: 'Real-time Web Search + {count} Local Documents Hybrid RAG',
      submitBtn: 'Generate Outline',
      submittingBtn: 'Initializing...'
    },
    // Outline
    outline: {
      statusBadge: 'AGENT PLANNING READY',
      title: '🎯 Research Outline Generated',
      hitlBadge: 'Human-in-the-Loop Collaborative Review',
      addChapter: 'Add Chapter',
      approveBtn: 'Approve & Start Research',
      approvingBtn: 'Starting...',
      clarificationTitle: 'Agent Scope & Boundary Clarification:',
      focusLabel: 'Focus:',
      focusPlaceholder: 'Key data, metrics and entities to verify...',
      queriesLabel: 'Planned Queries:',
      newChapterTitle: 'New Chapter: Policy Environment & Market Penetration Forecast',
      newChapterFocus: 'Subsidies, market access barriers and 2026-2030 penetration forecast',
      newChapterQuery: 'Policy Subsidies Penetration Forecast 2026',
      minChapterAlert: 'At least one chapter is required!'
    },
    // Radar Dashboard
    radar: {
      title: 'Deep Research Radar Dashboard',
      subtitle: 'Multi-Agent Real-time Collaboration Pipeline',
      round: 'Iteration {current}/{max}',
      tabThought: 'Agent Thinking Stream',
      tabScrape: 'Web Scraping Matrix',
      tabFacts: 'Fact Stream & Critic Reflection',
      emptyThought: 'Waiting for Agent thinking logs...',
      emptyScrape: 'Running multi-source search and dynamic scraping...',
      emptyFacts: 'Compressing long-form facts via Map-Reduce...',
      criticHeader: 'Critic Reflection & Validation Feedback',
      passBadge: 'Passed',
      needsMoreBadge: '2nd Search Needed',
      sourceCitations: 'Verified Citations: {count}'
    },
    // Report Viewer
    report: {
      badgeTitle: 'Editorial-Grade Verified Report Ready',
      badgeSubtitle: '100% Traceable Citations · Includes {count} authoritative sources',
      copyFull: 'Copy Full Text',
      copied: 'Copied Full Text',
      exportReport: 'Export Report',
      mindmapBtn: 'Mindmap',
      liveQABtn: 'Live Q&A Chat',
      tocTitle: 'Table of Contents',
      deepDiveTooltip: 'Deep Dive into this passage',
      citationVerified: 'Verified Evidence',
      citationRelevance: 'Confidence',
      viewSource: 'View Original Webpage',
      pinHint: 'Hover to preview, click to pin'
    },
    // Follow up Drawer
    chat: {
      title: 'Report Live Q&A Dialogue',
      subtitle: 'Powered by DeepSeek LLM + Fact-grounded Reasoning',
      welcome: 'Hello! I have fully assimilated the verified facts and complete report. Feel free to ask about any details, quantitative metrics, or highlighted sections.',
      quickPrompt1: '📌 Key Takeaways & Recommendations',
      prompt1Text: 'Summarize the core conclusions and top 3 strategic recommendations of this report.',
      quickPrompt2: '📊 Quantitative Data Summary',
      prompt2Text: 'What key metrics and quantitative data are highlighted in the report?',
      inputPlaceholder: 'Ask a question or dive deeper into selected text...',
      thinking: 'DeepSeek is analyzing the report and synthesizing your answer...'
    },
    // Export Modal
    export: {
      title: 'Export & Share Report',
      docxTitle: 'Download Microsoft Word (.docx)',
      docxDesc: 'Complete hierarchical headings, native data tables and standard styling',
      docxGenerating: 'Generating Word document...',
      mdTitle: 'Download Markdown (.md)',
      mdDesc: 'Preserves raw Markdown structure, tables, and reference anchors',
      pdfTitle: 'Export Editorial PDF / Print',
      pdfDesc: 'Clean A4 print-ready layout for one-click Save as PDF',
      mindmapJsonTitle: 'Download Mindmap JSON Structure (.json)',
      mindmapJsonDesc: 'Import directly into XMind, ProcessOn or MindNode for editing',
      close: 'Close'
    },
    // Mindmap
    mindmap: {
      title: 'Interactive Research Mindmap',
      subtitle: 'Panoramic Knowledge Tree Hierarchy · Supports Branch Folding',
      exportJsonBtn: 'Export Mindmap JSON',
      tip: 'Tip: Click arrows to fold/unfold any branch',
      close: 'Close Mindmap'
    },
    // Themes
    themes: {
      dark: 'Deep Space Dark 🌌',
      vintage: 'Vintage Antique 📜',
      light: 'Crisp Light ☀️',
      emerald: 'Aurora Emerald 🌲'
    }
  }
};
