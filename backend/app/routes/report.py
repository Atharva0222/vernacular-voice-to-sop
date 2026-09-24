import asyncio
import logging
import secrets
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app import asr, auth, corrections, db, routing, triage, tts
from app.config import settings
from app.routes.sop import get_sop
from app.schemas import Report, ReportCreated, ReportKind, ReportReceipt, ReportStatus, ReportUpdate

router = APIRouter()
Reader = Annotated[dict, Depends(auth.report_reader)]
log = logging.getLogger(__name__)

_ALLOWED_LANGS = {"hi", "mr", "auto"}


def process_report(report_id: int, audio_path: Path, sop_id: int, step_hint: int | None, language: str) -> None:
    """Transcribe, delete the audio, then triage against the SOP. Runs in the threadpool."""
    try:
        try:
            text, detected = asr.transcribe(str(audio_path), None if language == "auto" else language)
        finally:
            audio_path.unlink(missing_ok=True)
        if not text:
            raise ValueError("transcription produced empty text")
        result = asyncio.run(triage.triage(get_sop(sop_id).steps, text, detected, step_hint))
        with db.connect() as conn:
            conn.execute(
                "UPDATE reports SET status = 'open', language = ?, kind = ?, summary = ?, step_id = ?, "
                "severity = ?, suggested_change = ? WHERE id = ?",
                (detected, result.kind, result.summary, result.step_id, result.severity,
                 result.suggested_change, report_id),
            )
            routing.route(conn, report_id)
            routing.cluster(conn, report_id)
            corrections.draft(conn, report_id)
    except Exception as exc:
        log.exception("report %s failed", report_id)
        with db.connect() as conn:
            conn.execute("UPDATE reports SET status = 'failed', error = ? WHERE id = ?", (str(exc), report_id))


@router.post("/report", response_model=ReportCreated, status_code=202)
def create_report(
    background: BackgroundTasks,
    audio: UploadFile = File(...),
    sop_id: int = Form(...),
    step_id: Optional[int] = Form(None),
    language: str = Form("auto"),
) -> ReportCreated:
    """Accept a worker's voice report and return at once; ASR and triage run in the background.
    No worker identity is taken or stored; the unguessable receipt is how the worker hears back.
    Unauthenticated on purpose: requiring an account would deter reporting and break anonymity."""
    if language not in _ALLOWED_LANGS:
        raise HTTPException(400, f"language must be one of {_ALLOWED_LANGS}")
    get_sop(sop_id)

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    audio_path = settings.tmp_dir / f"report-{uuid.uuid4().hex}{suffix}"
    audio_path.write_bytes(audio.file.read())

    with db.connect() as conn:
        receipt = secrets.token_urlsafe(16)
        report_id = conn.execute("INSERT INTO reports (sop_id, receipt) VALUES (?, ?)", (sop_id, receipt)).lastrowid
    background.add_task(process_report, report_id, audio_path, sop_id, step_id, language)
    return ReportCreated(report_id=report_id, receipt=receipt, status="received")


@router.get("/receipt/{receipt}", response_model=ReportReceipt)
def get_receipt(receipt: str) -> ReportReceipt:
    """Worker-facing: only processing status and the manager's voiced reply, nothing about the report."""
    with db.connect() as conn:
        row = conn.execute("SELECT status, ack_audio_key FROM reports WHERE receipt = ?", (receipt,)).fetchone()
    if not row:
        raise HTTPException(404, "receipt not found")
    return ReportReceipt(**row)


def _visible_report(report_id: int, person: dict) -> Report:
    """Fetch a report the reader may see; others are 404 so their existence does not leak."""
    where, params = auth.scope_sql(person)
    with db.connect() as conn:
        row = conn.execute(f"SELECT * FROM report_view WHERE id = :id AND {where}", {"id": report_id, **params}).fetchone()
    if not row:
        raise HTTPException(404, "report not found")
    return Report(**row)


@router.get("/report/{report_id}", response_model=Report)
def get_report(report_id: int, person: Reader) -> Report:
    return _visible_report(report_id, person)


@router.get("/reports", response_model=list[Report])
def list_reports(person: Reader, status: ReportStatus | None = None, kind: ReportKind | None = None) -> list[Report]:
    """Manager inbox for the caller's own lines: confirmed clusters first, then newest.
    Text only: report audio is never kept."""
    where, params = auth.scope_sql(person)
    with db.connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM report_view WHERE {where} AND (:status IS NULL OR status = :status) "
            "AND (:kind IS NULL OR kind = :kind) ORDER BY confirmed DESC, created_at DESC, id DESC",
            {"status": status, "kind": kind, **params},
        ).fetchall()
    return [Report(**r) for r in rows]


@router.patch("/report/{report_id}", response_model=Report)
async def update_report(report_id: int, req: ReportUpdate, person: Reader) -> Report:
    """Set status and/or reply; a reply is voiced in the worker's language for playback on the card."""
    report = _visible_report(report_id, person)
    if report.status in ("received", "failed"):
        raise HTTPException(409, f"report is {report.status}, not yet triaged")
    fields = req.model_dump(exclude_none=True)
    if req.response_text:
        fields["ack_audio_key"], _ = await tts.synthesize(req.response_text, report.language)
    if fields:
        with db.connect() as conn:
            conn.execute(
                f"UPDATE reports SET {', '.join(f'{k} = :{k}' for k in fields)} WHERE id = :id",
                {**fields, "id": report_id},
            )
    return _visible_report(report_id, person)
