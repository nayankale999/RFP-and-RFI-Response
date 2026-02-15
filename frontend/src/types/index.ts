export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  upload_context: string | null;
  status: string;
  client_name: string | null;
  industry: string | null;
  deadline: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  requirement_count: number;
  response_count: number;
  processing_status: string | null;
  processing_message: string | null;
  processing_started_at: string | null;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number | null;
  doc_category: string | null;
  page_count: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface Requirement {
  id: string;
  project_id: string;
  document_id: string | null;
  req_number: string;
  title: string;
  description: string;
  type: string;
  category: string | null;
  is_mandatory: boolean;
  reference_page: number | null;
  reference_section: string | null;
  response_required: boolean;
  priority: string;
  confidence_score: number | null;
  created_at: string;
}

export interface Response {
  id: string;
  requirement_id: string;
  project_id: string;
  compliance_status: string;
  response_text: string;
  confidence_score: number | null;
  source_refs: Record<string, unknown> | null;
  is_ai_generated: boolean;
  is_reviewed: boolean;
  reviewed_by: string | null;
  reviewed_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface ScheduleEvent {
  id: string;
  event_type: string;
  event_name: string;
  event_date: string | null;
  notes: string | null;
}

export interface PricingItem {
  id: string;
  category: string;
  line_item: string;
  description: string | null;
  unit_cost: number | null;
  quantity: number | null;
  total: number | null;
  currency: string;
  year: number | null;
  notes: string | null;
}

export interface ComplianceScores {
  overall_score: number;
  functional_score: number;
  non_functional_score: number;
  commercial_score: number;
  technical_score: number;
  scores_by_type: Record<string, number>;
  total_requirements: number;
  total_responses: number;
  status_breakdown: Record<string, number>;
}

export interface ResponsePlan {
  id: string;
  workstreams: Record<string, unknown> | null;
  escalation_matrix: Record<string, unknown> | null;
  version: number;
  notes: string | null;
}

export type ComplianceStatus =
  | "fully_compliant"
  | "partially_compliant"
  | "configurable"
  | "custom_dev"
  | "not_applicable";

export type RequirementType =
  | "functional"
  | "non_functional"
  | "commercial"
  | "legal"
  | "technical";

export type ProjectStatus =
  | "draft"
  | "in_progress"
  | "review"
  | "completed"
  | "archived";
