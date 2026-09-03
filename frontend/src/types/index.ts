export interface CitationSource {
  id: number;
  url: string;
  title: string;
  snippet: string;
  score?: number;
  published_date?: string | null;
}

export interface ChapterOutline {
  chapter_num: number;
  title: string;
  focus: string;
  search_queries?: string[];
  extracted_facts?: string[];
  bound_documents?: string[];
}

export type ReportStyle = 
  | 'consulting' 
  | 'literature_review' 
  | 'tutorial_docs' 
  | 'executive' 
  | 'briefing'
  | 'academic'; // 向后兼容

export interface CustomLLMConfig {
  provider_type: 'openai' | 'anthropic';
  base_url?: string;
  api_key?: string;
  model_name?: string;
  temperature?: number;
}

export interface TestConnectionResponse {
  success: boolean;
  message?: string;
  reply?: string;
  latency_ms?: number;
  error?: string;
}

export interface StyleRegistryItem {
  id: string;
  name_zh: string;
  name_en: string;
  color: string;
}

export interface ResearchState {
  task_id: string;
  user_query: string;
  research_depth: 'quick' | 'standard' | 'deep';
  report_style: ReportStyle;
  custom_llm_config?: CustomLLMConfig;
  clarification?: string;
  outline: ChapterOutline[];
  citations: CitationSource[];
  current_step: string;
  local_documents?: any[];
  iteration_count?: number;
  max_iterations?: number;
  critic_feedback?: string;
  needs_more_research?: boolean;
  draft_report?: string;
  final_report?: string;
  logs?: string[];
}

export type TaskStatus = 
  | 'pending'
  | 'planning'
  | 'waiting_outline_approval'
  | 'researching'
  | 'writing'
  | 'verifying'
  | 'completed'
  | 'cancelled'
  | 'failed';

export interface TaskDetail {
  task_id: string;
  status: TaskStatus;
  created_at: number;
  updated_at: number;
  auto_approve_outline: boolean;
  state: ResearchState;
  error?: string | null;
}

export interface CreateTaskResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface TaskDetailResponse extends TaskDetail {}
