import { 
  CreateTaskResponse, 
  TaskDetailResponse, 
  ChapterOutline, 
  ReportStyle, 
  CustomLLMConfig, 
  TestConnectionResponse, 
  StyleRegistryItem 
} from '../types';

const API_BASE = '/api/v1/research';

export async function uploadDocument(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '上传文件失败' }));
    throw new Error(err.detail || '上传文件解析失败');
  }
  return response.json();
}

export async function createTask(
  query: string,
  depth: 'quick' | 'standard' | 'deep' = 'standard',
  style: ReportStyle = 'consulting',
  autoApproveOutline: boolean = true,
  maxIterations: number = 2,
  localDocuments?: any[],
  customLLMConfig?: CustomLLMConfig
): Promise<CreateTaskResponse> {
  const payload: any = {
    query,
    depth,
    style,
    auto_approve_outline: autoApproveOutline,
    max_iterations: maxIterations,
    local_documents: localDocuments && localDocuments.length > 0 ? localDocuments : null
  };
  if (customLLMConfig && (customLLMConfig.api_key || customLLMConfig.base_url || customLLMConfig.model_name)) {
    payload.custom_llm_config = customLLMConfig;
  }

  const response = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '创建任务失败' }));
    throw new Error(err.detail || `HTTP Error ${response.status}`);
  }
  return response.json();
}

export async function testCustomModelConnection(config: CustomLLMConfig): Promise<TestConnectionResponse> {
  const response = await fetch(`${API_BASE}/models/test-connection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '测试连通性请求失败' }));
    return { success: false, error: err.detail || `HTTP Error ${response.status}` };
  }
  return response.json();
}

export async function fetchReportStyles(): Promise<StyleRegistryItem[]> {
  try {
    const response = await fetch(`${API_BASE}/styles`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.styles || [];
  } catch {
    return [];
  }
}

export async function getTaskDetail(taskId: string): Promise<TaskDetailResponse> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}`);
  if (!response.ok) {
    throw new Error(`获取任务详情失败: ${response.status}`);
  }
  return response.json();
}

export async function approveOutline(taskId: string, outline: ChapterOutline[]): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/approve_outline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ outline })
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '确认大纲失败' }));
    throw new Error(err.detail || `HTTP Error ${response.status}`);
  }
  return response.json();
}

export async function cancelTask(taskId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
    method: 'POST'
  });
  if (!response.ok) {
    throw new Error(`取消任务失败: ${response.status}`);
  }
  return response.json();
}

export function subscribeToTaskStream(
  taskId: string,
  onMessage: (eventType: string, data: any) => void,
  onError?: (err: any) => void
): () => void {
  let eventSource: EventSource | null = null;
  let isClosed = false;
  let lastEventId: string | null = null;
  let retryCount = 0;
  const maxRetries = 3;
  let retryTimer: any = null;

  const customEvents = [
    'status',
    'thought',
    'outline_ready',
    'waiting_approval',
    'search',
    'facts_extracted',
    'critic_evaluated',
    'completed',
    'cancelled',
    'failed',
    'error'
  ];

  function connect() {
    if (isClosed) return;

    const url = lastEventId
      ? `${API_BASE}/tasks/${taskId}/stream?last_event_id=${lastEventId}`
      : `${API_BASE}/tasks/${taskId}/stream`;

    eventSource = new EventSource(url);

    eventSource.onopen = () => {
      retryCount = 0;
    };

    eventSource.onmessage = (event) => {
      if (event.lastEventId) {
        lastEventId = event.lastEventId;
      }
      try {
        const data = JSON.parse(event.data);
        onMessage(event.type || 'message', data);
      } catch {
        onMessage(event.type || 'message', event.data);
      }
    };

    customEvents.forEach((evt) => {
      eventSource?.addEventListener(evt, (event: any) => {
        if (event.lastEventId) {
          lastEventId = event.lastEventId;
        }
        try {
          const data = JSON.parse(event.data);
          onMessage(evt, data);
        } catch {
          onMessage(evt, event.data);
        }
        if (evt === 'completed' || evt === 'cancelled' || evt === 'failed') {
          isClosed = true;
          eventSource?.close();
        }
      });
    });

    eventSource.onerror = (err) => {
      eventSource?.close();
      if (isClosed) return;

      if (retryCount < maxRetries) {
        const delay = Math.pow(2, retryCount) * 1000;
        retryCount++;
        retryTimer = setTimeout(connect, delay);
      } else {
        if (onError) onError(err);
      }
    };
  }

  connect();

  return () => {
    isClosed = true;
    if (retryTimer) clearTimeout(retryTimer);
    if (eventSource) eventSource.close();
  };
}

export function getAudioSummaryUrl(taskId: string, voice: string = 'zh-CN-YunxiNeural'): string {
  return `${API_BASE}/tasks/${taskId}/audio-summary?voice=${encodeURIComponent(voice)}`;
}

export async function fetchMarpSlides(taskId: string): Promise<{ task_id: string; title: string; marp_markdown: string; page_count: number }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/slides-data`);
  if (!response.ok) {
    throw new Error(`获取 Marp 演示文稿失败: ${response.status}`);
  }
  return response.json();
}

export async function previewMarpSlides(title: string, report: string): Promise<{ title: string; marp_markdown: string; page_count: number }> {
  const response = await fetch(`${API_BASE}/export/marp-preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, report })
  });
  if (!response.ok) {
    throw new Error(`预览 Marp 演示文稿失败: ${response.status}`);
  }
  return response.json();
}

export async function downloadMarpFile(title: string, report?: string, taskId?: string): Promise<void> {
  let blob: Blob;
  if (taskId) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}/export/marp`);
    if (!response.ok) throw new Error(`下载 Marp 失败: ${response.status}`);
    blob = await response.blob();
  } else {
    const response = await fetch(`${API_BASE}/export/marp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, report: report || '' })
    });
    if (!response.ok) throw new Error(`下载 Marp 失败: ${response.status}`);
    blob = await response.blob();
  }
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${title || '深度研究'}_slides.md`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export interface PreparePresentationResult {
  status: string;
  task_id: string;
  title: string;
  slide_count: number;
  presentation_url: string;
}

export function getLivePresentationUrl(taskId: string): string {
  return `${API_BASE}/tasks/${taskId}/presentation`;
}

export async function preparePresentation(
  taskId: string,
  customLLMConfig?: any,
  forceRefresh: boolean = false
): Promise<PreparePresentationResult> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/presentation/prepare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      custom_llm_config: customLLMConfig || null,
      force_refresh: forceRefresh
    })
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `准备演示文稿失败: ${response.status}`);
  }
  return response.json();
}

export async function downloadPptxFile(title: string, report?: string, taskId?: string): Promise<void> {
  let blob: Blob;
  if (taskId) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}/export/pptx`);
    if (!response.ok) throw new Error(`下载 PPTX 失败: ${response.status}`);
    blob = await response.blob();
  } else {
    const response = await fetch(`${API_BASE}/export/pptx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, report: report || '' })
    });
    if (!response.ok) throw new Error(`下载 PPTX 失败: ${response.status}`);
    blob = await response.blob();
  }
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${title || '深度研究'}_演示文稿.pptx`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function downloadHtmlSlidesFile(title: string, report?: string, taskId?: string): Promise<void> {
  let blob: Blob;
  if (taskId) {
    const response = await fetch(`${API_BASE}/tasks/${taskId}/export/html-slides`);
    if (!response.ok) throw new Error(`下载 HTML 幻灯片失败: ${response.status}`);
    blob = await response.blob();
  } else {
    const response = await fetch(`${API_BASE}/export/html-slides`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, report: report || '' })
    });
    if (!response.ok) throw new Error(`下载 HTML 幻灯片失败: ${response.status}`);
    blob = await response.blob();
  }
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${title || '深度研究'}_网页演示文稿.html`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export interface GlossaryResult {
  term: string;
  explanation: string;
  status: string;
  cached?: boolean;
}

export async function explainTerm(
  term: string,
  context?: string,
  customLLMConfig?: any
): Promise<GlossaryResult> {
  const response = await fetch(`${API_BASE}/glossary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      term,
      context: context || '',
      custom_llm_config: customLLMConfig || null
    })
  });
  if (!response.ok) {
    throw new Error(`获取释义失败: ${response.status}`);
  }
  return response.json();
}

export interface TaskMetricsResult {
  task_id: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost_cny: number;
  total_cost_usd: number;
  search_count: number;
  node_breakdown: {
    planner: { input: number; output: number; tokens: number };
    researcher: { input: number; output: number; tokens: number };
    writer: { input: number; output: number; tokens: number };
    verifier: { input: number; output: number; tokens: number };
  };
}

export async function fetchTaskMetrics(taskId: string): Promise<TaskMetricsResult> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/metrics`);
  if (!response.ok) {
    throw new Error(`获取算力指标失败: ${response.status}`);
  }
  return response.json();
}

export interface RecommendedTopic {
  title: string;
  text: string;
}

export async function fetchRecommendedTopics(
  customLLMConfig?: any,
  count: number = 4
): Promise<RecommendedTopic[]> {
  const response = await fetch(`${API_BASE}/recommendations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      count,
      custom_llm_config: customLLMConfig || null
    })
  });
  if (!response.ok) {
    throw new Error(`获取推荐课题失败: ${response.status}`);
  }
  const data = await response.json();
  return data.topics || [];
}

export interface InfographicMetric {
  value: string;
  label: string;
  sub: string;
}

export interface InfographicInsight {
  num: string;
  title: string;
  content: string;
}

export interface InfographicData {
  title: string;
  metrics: InfographicMetric[];
  summary_lines: string[];
  insights: InfographicInsight[];
  status: string;
  source?: string;
}

export async function fetchInfographicData(
  title: string,
  report: string,
  customLLMConfig?: any
): Promise<InfographicData> {
  const response = await fetch(`${API_BASE}/infographic/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      report,
      custom_llm_config: customLLMConfig || null
    })
  });
  if (!response.ok) {
    throw new Error(`提炼长图内容失败: ${response.status}`);
  }
  return response.json();
}

// ============================================================================
// 【阶段五】AI 认知深度与多模态交互全维度升华 API
// ============================================================================

export interface PodcastTurn {
  speaker: 'Yunxi' | 'Xiaoxiao' | string;
  name: string;
  role: string;
  text: string;
}

export interface PodcastData {
  task_id: string;
  title: string;
  script: PodcastTurn[];
  audio_url: string;
  audio_size?: number;
  status: string;
}

export async function generatePodcast(
  taskId: string,
  customLLMConfig?: any
): Promise<PodcastData> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/podcast/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ custom_llm_config: customLLMConfig || null })
  });
  if (!response.ok) {
    throw new Error(`生成双角色播客失败: ${response.status}`);
  }
  return response.json();
}

export async function fetchPodcastMetadata(taskId: string): Promise<PodcastData> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/podcast`);
  if (!response.ok) {
    throw new Error(`获取播客信息失败: ${response.status}`);
  }
  return response.json();
}

export interface MindmapNode {
  id: string;
  label: string;
  type: string;
  detail?: string;
}

export interface MindmapEdge {
  from: string;
  to: string;
  relation: string;
  label: string;
}

export interface CausalMindmapData {
  title: string;
  summary: string;
  mermaid_code: string;
  nodes: MindmapNode[];
  edges: MindmapEdge[];
  status: string;
}

export async function generateCausalMindmap(
  taskId: string,
  title?: string,
  report?: string,
  customLLMConfig?: any
): Promise<CausalMindmapData> {
  // 如果提供了完整文本，直接走纯文本接口，否则走任务关联接口
  if (title && report) {
    const res = await fetch(`${API_BASE}/mindmap/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, report, custom_llm_config: customLLMConfig || null })
    });
    if (!res.ok) throw new Error(`生成因果脑图失败: ${res.status}`);
    return res.json();
  }
  const response = await fetch(`${API_BASE}/tasks/${taskId}/mindmap/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ custom_llm_config: customLLMConfig || null })
  });
  if (!response.ok) {
    throw new Error(`提炼因果脑图失败: ${response.status}`);
  }
  return response.json();
}

export interface SocialQuotesData {
  title: string;
  punchline: string;
  predictions: string[];
  action_advice: string;
  platforms: {
    twitter_thread: string;
    jike_post: string;
    xiaohongshu: string;
  };
  status: string;
}

export async function generateSocialQuotes(
  taskId: string,
  title?: string,
  report?: string,
  customLLMConfig?: any
): Promise<SocialQuotesData> {
  if (title && report) {
    const res = await fetch(`${API_BASE}/social-quotes/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, report, custom_llm_config: customLLMConfig || null })
    });
    if (!res.ok) throw new Error(`生成社交金句失败: ${res.status}`);
    return res.json();
  }
  const response = await fetch(`${API_BASE}/tasks/${taskId}/social-quotes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ custom_llm_config: customLLMConfig || null })
  });
  if (!response.ok) {
    throw new Error(`提炼社交金句失败: ${response.status}`);
  }
  return response.json();
}

export interface NLIEvaluation {
  claim: string;
  verdict: 'Entailment' | 'Neutral' | 'Contradiction' | string;
  confidence: number;
  rationale: string;
}

export interface NLIRadarData {
  fact_grounding_score: number;
  entailment_rate: number;
  summary: string;
  evaluations: NLIEvaluation[];
  status: string;
}

export async function evaluateNLIRadar(
  taskId: string,
  report?: string,
  citations?: any[],
  customLLMConfig?: any
): Promise<NLIRadarData> {
  if (report) {
    const res = await fetch(`${API_BASE}/nli/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report, citations, custom_llm_config: customLLMConfig || null })
    });
    if (!res.ok) throw new Error(`评估 NLI 雷达失败: ${res.status}`);
    return res.json();
  }
  const response = await fetch(`${API_BASE}/tasks/${taskId}/nli-radar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ custom_llm_config: customLLMConfig || null })
  });
  if (!response.ok) {
    throw new Error(`计算 NLI 事实雷达失败: ${response.status}`);
  }
  return response.json();
}






