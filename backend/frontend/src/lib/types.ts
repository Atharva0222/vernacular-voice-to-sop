export type Language = 'hi' | 'mr'
export type Role = 'supervisor' | 'manager' | 'plant_head'

export interface Step {
  step_number: number
  text: string
  is_safety_warning: boolean
  icon: string
}

export interface StoredStep extends Step {
  id: number
  audio_url?: string | null
}

export interface MachineSummary {
  id: number
  name: string
  line_id: number
  line_name: string
  sop_id: number | null
  sop_version: number | null
  language: Language | null
  step_count: number
}

export interface Line {
  id: number
  name: string
  plant_id: number
}

export interface SOPSummary {
  id: number
  machine_id: number
  title: string
  language: Language
  version: number
  created_at: string
}

export interface StoredSOP extends SOPSummary {
  transcript: string
  steps: StoredStep[]
}

export type ReportKind = 'machine' | 'sop' | 'understanding'
export type ReportStatus = 'received' | 'failed' | 'open' | 'acknowledged' | 'resolved'

export interface ReportCreated {
  report_id: number
  receipt: string
  status: ReportStatus
}

export interface ReportReceipt {
  status: ReportStatus
  ack_audio_key: string | null
  answered_by_sop: boolean
}

export interface Report {
  id: number
  sop_id: number
  step_id: number | null
  language: string | null
  status: ReportStatus
  kind: ReportKind | null
  summary: string | null
  severity: string | null
  suggested_change: string | null
  error: string | null
  response_text: string | null
  ack_audio_key: string | null
  created_at: string
  machine_id: number
  assigned_to: number | null
  escalate_after: string | null
  escalated: boolean
  effective_assignee: number | null
  cluster_id: number | null
  cluster_size: number
  confirmed: boolean
}

export interface StepEdit {
  id: number
  cluster_id: number
  machine_id: number
  sop_id: number
  step_id: number
  step_number: number
  old_text: string
  new_text: string
  status: 'pending' | 'approved' | 'rejected'
  new_sop_id: number | null
  report_count: number
  created_at: string
}

export interface LoginResponse {
  token: string
  name: string
  role: Role
}
