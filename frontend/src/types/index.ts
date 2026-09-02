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
}

export interface ResearchState {
  task_id: string;
  user_query: string;
  research_depth: 'quick' | 'standard' | 'deep';
  report_style: 'consulting' | 'academic' | 'executive';
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
