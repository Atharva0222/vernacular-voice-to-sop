export type Language = 'hi' | 'mr'
export type Role = 'supervisor' | 'manager' | 'plant_head' | 'hr_admin' | 'recruiter'

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

export type EmployeeRole = 'worker' | 'supervisor' | 'manager' | 'plant_head' | 'hr_admin' | 'recruiter'
export type EmploymentStatus = 'active' | 'on_leave' | 'terminated'

export interface Department {
  id: number
  plant_id: number
  name: string
  head_employee_id: number | null
}

export interface Shift {
  id: number
  plant_id: number
  name: string
  starts_at: string
  ends_at: string
}

export interface ShiftAssignment {
  id: number
  employee_id: number
  employee_name: string
  shift_id: number
  shift_name: string
  line_id: number
  work_date: string
}

export interface Attendance {
  id: number
  shift_assignment_id: number
  clock_in: string | null
  clock_out: string | null
  machine_id: number | null
}

export interface LeaveType {
  id: number
  name: string
  annual_quota_days: number
}

export interface LeaveBalance {
  employee_id: number
  leave_type_id: number
  year: number
  remaining_days: number
}

export type LeaveRequestStatus = 'pending' | 'approved' | 'rejected'

export interface LeaveRequest {
  id: number
  employee_id: number
  employee_name: string
  leave_type_id: number
  leave_type_name: string
  starts_on: string
  ends_on: string
  status: LeaveRequestStatus
  approved_by: number | null
  created_at: string
}

export type JobPostingStatus = 'open' | 'closed'
export type ApplicationStage = 'applied' | 'screening' | 'interview' | 'offer' | 'rejected' | 'hired'

export interface JobPosting {
  id: number
  plant_id: number
  title: string
  department_id: number | null
  status: JobPostingStatus
  created_by: number
  created_at: string
}

export interface Candidate {
  id: number
  name: string
  phone: string | null
  email: string | null
  resume_storage_path: string | null
}

export interface Application {
  id: number
  job_posting_id: number
  candidate_id: number
  candidate_name: string
  stage: ApplicationStage
  created_at: string
}

export interface EmployeeSummary {
  id: number
  name: string
  role: EmployeeRole
  phone: string | null
  language: string
  plant_id: number
  employee_code: string | null
  department_id: number | null
  job_title: string | null
  direct_manager_id: number | null
  employment_status: EmploymentStatus
  hire_date: string | null
  created_at: string
}
