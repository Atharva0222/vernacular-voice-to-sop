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
    created_at: str


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
    created_at: str
    machine_id: int
    assigned_to: int | None
    escalate_after: str | None
    escalated: bool
    effective_assignee: int | None
    cluster_id: int | None
    cluster_size: int
    confirmed: bool


class ReportUpdate(BaseModel):
    status: Literal["open", "acknowledged", "resolved"] | None = None
    response_text: str | None = None


class LoginRequest(BaseModel):
    person_id: int
    pin: str


class LoginResponse(BaseModel):
    token: str
    name: str
    role: str


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
    created_at: str
