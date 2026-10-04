from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["hi", "mr"]


class TranscribeResponse(BaseModel):
    transcript: str
    detected_language: Language


class Step(BaseModel):
    step_number: int
    text: str
    is_safety_warning: bool
    icon: str


class StructureRequest(BaseModel):
    transcript: str
    language: Language


class SOPResponse(BaseModel):
    steps: list[Step] = Field(default_factory=list)


class TTSRequest(BaseModel):
    text: str
    language: Language


class TTSResponse(BaseModel):
    audio_url: str


class SOPCreate(BaseModel):
    machine_id: int
    title: str
    language: Language
    transcript: str
    steps: list[Step]


class StoredStep(Step):
    id: int


class Line(BaseModel):
    id: int
    name: str
    plant_id: int


class MachineCreate(BaseModel):
    line_id: int
    name: str = Field(min_length=1, max_length=60)


class MachineSummary(BaseModel):
    id: int
    name: str
    line_id: int
    line_name: str
    sop_id: int | None
    sop_version: int | None
    language: Language | None
    step_count: int


class SOPSummary(BaseModel):
    id: int
    machine_id: int
    title: str
    language: Language
    version: int
    created_at: datetime


class StoredSOP(SOPSummary):
    transcript: str
    steps: list[StoredStep]


ReportKind = Literal["machine", "sop", "understanding"]
ReportStatus = Literal["received", "failed", "open", "acknowledged", "resolved"]


class Triage(BaseModel):
    kind: ReportKind
    summary: str
    step_id: int | None
    severity: Literal["low", "medium", "high"]
    suggested_change: str | None


class Guidance(BaseModel):
    """Whether the machine's own SOP already answers what the worker said."""

    covered_by_sop: bool
    answer: str | None
    step_id: int | None


class ReportCreated(BaseModel):
    report_id: int
    receipt: str
    status: ReportStatus


class ReportReceipt(BaseModel):
    status: ReportStatus
    ack_audio_key: str | None
    answered_by_sop: bool


class Report(BaseModel):
    id: int
    sop_id: int
    step_id: int | None
    language: str | None
    status: ReportStatus
    kind: ReportKind | None
    summary: str | None
    severity: str | None
    suggested_change: str | None
    error: str | None
    response_text: str | None
    ack_audio_key: str | None
    created_at: datetime
    machine_id: int
    assigned_to: int | None
    escalate_after: datetime | None
    escalated: bool
    effective_assignee: int | None
    cluster_id: int | None
    cluster_size: int
    confirmed: bool


class ReportUpdate(BaseModel):
    status: Literal["open", "acknowledged", "resolved"] | None = None
    response_text: str | None = None


class StepEdit(BaseModel):
    id: int
    cluster_id: int
    machine_id: int
    sop_id: int
    step_id: int
    step_number: int
    old_text: str
    new_text: str
    status: Literal["pending", "approved", "rejected"]
    new_sop_id: int | None
    report_count: int
    created_at: datetime


EmployeeRole = Literal["worker", "supervisor", "manager", "plant_head", "hr_admin", "recruiter"]
EmploymentStatus = Literal["active", "on_leave", "terminated"]


class Department(BaseModel):
    id: int
    plant_id: int
    name: str
    head_employee_id: int | None


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    head_employee_id: int | None = None


class EmployeeSummary(BaseModel):
    id: int
    name: str
    role: EmployeeRole
    phone: str | None
    language: str
    plant_id: int
    employee_code: str | None
    department_id: int | None
    job_title: str | None
    direct_manager_id: int | None
    employment_status: EmploymentStatus
    hire_date: date | None
    created_at: datetime


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: EmployeeRole
    phone: str | None = None
    language: str = "hi"
    employee_code: str | None = None
    department_id: int | None = None
    job_title: str | None = None
    direct_manager_id: int | None = None
    hire_date: str | None = None


class EmployeeUpdate(BaseModel):
    department_id: int | None = None
    job_title: str | None = None
    direct_manager_id: int | None = None
    employment_status: EmploymentStatus | None = None


class Shift(BaseModel):
    id: int
    plant_id: int
    name: str
    starts_at: time
    ends_at: time


class ShiftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    starts_at: time
    ends_at: time


class ShiftAssignment(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    shift_id: int
    shift_name: str
    line_id: int
    work_date: date


class ShiftAssignmentCreate(BaseModel):
    employee_id: int
    shift_id: int
    line_id: int
    work_date: date


class Attendance(BaseModel):
    id: int
    shift_assignment_id: int
    clock_in: datetime | None
    clock_out: datetime | None
    machine_id: int | None


class ClockIn(BaseModel):
    shift_assignment_id: int
    machine_id: int | None = None


class LeaveType(BaseModel):
    id: int
    name: str
    annual_quota_days: int


class LeaveTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    annual_quota_days: int = Field(ge=0, le=365)


class LeaveBalance(BaseModel):
    employee_id: int
    leave_type_id: int
    year: int
    remaining_days: float


class LeaveBalanceSet(BaseModel):
    employee_id: int
    leave_type_id: int
    year: int
    remaining_days: float = Field(ge=0)


LeaveRequestStatus = Literal["pending", "approved", "rejected"]


class LeaveRequest(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    leave_type_id: int
    leave_type_name: str
    starts_on: date
    ends_on: date
    status: LeaveRequestStatus
    approved_by: int | None
    created_at: datetime


class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    starts_on: date
    ends_on: date


JobPostingStatus = Literal["open", "closed"]
ApplicationStage = Literal["applied", "screening", "interview", "offer", "rejected", "hired"]


class JobPosting(BaseModel):
    id: int
    plant_id: int
    title: str
    department_id: int | None
    status: JobPostingStatus
    created_by: int
    created_at: datetime


class JobPostingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    department_id: int | None = None


class Candidate(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    resume_storage_path: str | None


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = None
    email: str | None = None


class ResumeUploadUrl(BaseModel):
    upload_url: str
    storage_path: str


class CandidateUpdate(BaseModel):
    resume_storage_path: str


class Application(BaseModel):
    id: int
    job_posting_id: int
    candidate_id: int
    candidate_name: str
    stage: ApplicationStage
    created_at: datetime


class ApplicationCreate(BaseModel):
    job_posting_id: int
    candidate_id: int


class ApplicationStageUpdate(BaseModel):
    stage: ApplicationStage
