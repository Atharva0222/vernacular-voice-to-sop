import asyncio
import logging
import secrets
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import text

from app import asr, auth, corrections, db, guidance, routing, triage, tts
from app.config import settings
from app.limiter import limiter
from app.routes.sop import get_sop
from app.schemas import Report, ReportCreated, ReportKind, ReportReceipt, ReportStatus, ReportUpdate

router = APIRouter()
Reader = Annotated[dict, Depends(auth.report_reader)]
log = logging.getLogger(__name__)

_ALLOWED_LANGS = {"hi", "mr", "auto"}


def _transcribe_and_discard(audio_path: Path, language: str) -> tuple[str, str]:
    """Voice in, text out. The recording is deleted either way, so it can never be played back."""
    try:
        text_out, detected = asr.transcribe(str(audio_path), None if language == "auto" else language)
    finally:
        audio_path.unlink(missing_ok=True)
    if not text_out:
        raise ValueError("transcription produced empty text")
    return text_out, detected


def _send_to_manager(report_id: int, text_in: str, detected: str, sop_id: int, step_hint: int | None) -> None:
    """Triage against the SOP, then route, cluster and draft a card fix as usual."""
    result = asyncio.run(triage.triage(get_sop(sop_id).steps, text_in, detected, step_hint))
    with db.connect_service() as conn:
        conn.execute(
            text(
                "UPDATE reports SET status = 'open', language = :language, kind = :kind, summary = :summary, "
                "step_id = :step_id, severity = :severity, suggested_change = :suggested_change WHERE id = :id"
            ),
            {
                "language": detected,
                "kind": result.kind,
                "summary": result.summary,
                "step_id": result.step_id,
                "severity": result.severity,
                "suggested_change": result.suggested_change,
                "id": report_id,
            },
        )
        routing.route(conn, report_id)
        routing.cluster(conn, report_id)
        corrections.draft(conn, report_id)


def _fail(report_id: int, exc: Exception) -> None:
    log.exception("report %s failed", report_id)
    with db.connect_service() as conn:
        conn.execute(
            text("UPDATE reports SET status = 'failed', error = :error WHERE id = :id"),
            {"error": str(exc), "id": report_id},
        )


def process_report(report_id: int, audio_path: Path, sop_id: int, step_hint: int | None, language: str) -> None:
    """Transcribe, delete the audio, then triage against the SOP. Runs in the threadpool."""
    try:
        text_out, detected = _transcribe_and_discard(audio_path, language)
        _send_to_manager(report_id, text_out, detected, sop_id, step_hint)
    except Exception as exc:
        _fail(report_id, exc)


def process_question(report_id: int, audio_path: Path, sop_id: int, language: str) -> None:
    """Answer from the machine's own SOP when it covers this; otherwise pass it to a manager.

    An answered question keeps no text: only the spoken answer the worker plays back."""
    try:
        text_out, detected = _transcribe_and_discard(audio_path, language)
        answer = asyncio.run(guidance.answer_from_sop(get_sop(sop_id).steps, text_out, detected))
        if not answer.covered_by_sop:
            return _send_to_manager(report_id, text_out, detected, sop_id, None)

        audio_key, _ = asyncio.run(tts.synthesize(answer.answer, detected))
        with db.connect_service() as conn:
            conn.execute(
                text(
                    "UPDATE reports SET status = 'resolved', language = :language, step_id = :step_id, "
                    "answered_by_sop = TRUE, ack_audio_key = :ack_audio_key WHERE id = :id"
                ),
                {"language": detected, "step_id": answer.step_id, "ack_audio_key": audio_key, "id": report_id},
            )
    except Exception as exc:
        _fail(report_id, exc)


@router.post("/report", response_model=ReportCreated, status_code=202)
@limiter.limit("20/minute")
def create_report(
    request: Request,
    background: BackgroundTasks,
    audio: UploadFile = File(...),
    sop_id: int = Form(...),
    step_id: int | None = Form(None),
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

    with db.connect_service() as conn:
        receipt = secrets.token_urlsafe(16)
        report_id = conn.execute(
            text("INSERT INTO reports (sop_id, receipt) VALUES (:sop_id, :receipt) RETURNING id"),
            {"sop_id": sop_id, "receipt": receipt},
        ).scalar_one()
    background.add_task(process_report, report_id, audio_path, sop_id, step_id, language)
    return ReportCreated(report_id=report_id, receipt=receipt, status="received")


@router.post("/ask", response_model=ReportCreated, status_code=202)
@limiter.limit("20/minute")
def ask(
    request: Request,
    background: BackgroundTasks,
    audio: UploadFile = File(...),
    sop_id: int = Form(...),
    language: str = Form("auto"),
) -> ReportCreated:
    """A worker speaks about the machine as a whole. If the SOP already says what to do, they
    hear it back; if it does not, it becomes a report for the manager, exactly as before."""
    if language not in _ALLOWED_LANGS:
        raise HTTPException(400, f"language must be one of {_ALLOWED_LANGS}")
    get_sop(sop_id)

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    audio_path = settings.tmp_dir / f"report-{uuid.uuid4().hex}{suffix}"
    audio_path.write_bytes(audio.file.read())

    with db.connect_service() as conn:
        receipt = secrets.token_urlsafe(16)
        report_id = conn.execute(
            text("INSERT INTO reports (sop_id, receipt) VALUES (:sop_id, :receipt) RETURNING id"),
            {"sop_id": sop_id, "receipt": receipt},
        ).scalar_one()
    background.add_task(process_question, report_id, audio_path, sop_id, language)
    return ReportCreated(report_id=report_id, receipt=receipt, status="received")


@router.get("/receipt/{receipt}", response_model=ReportReceipt)
def get_receipt(receipt: str) -> ReportReceipt:
    """Worker-facing: only processing status and the manager's voiced reply, nothing about the report."""
    with db.connect_service() as conn:
        row = conn.execute(
            text("SELECT status, ack_audio_key, answered_by_sop FROM reports WHERE receipt = :receipt"),
            {"receipt": receipt},
        ).mappings().fetchone()
    if not row:
        raise HTTPException(404, "receipt not found")
    return ReportReceipt(**row)


def _visible_report(report_id: int, person: dict) -> Report:
    """Fetch a report the reader may see; others are 404 so their existence does not leak."""
    where, params = auth.scope_sql(person)
    with db.connect(person) as conn:
        row = conn.execute(
            text(f"SELECT * FROM report_view WHERE id = :id AND {where}"), {"id": report_id, **params}
        ).mappings().fetchone()
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
    with db.connect(person) as conn:
        rows = conn.execute(
            # CAST(...): an untyped NULL parameter used only in `x IS NULL` gives psycopg's
            # extended protocol no type to infer (unlike SQLite, which is dynamically typed) -
            # confirmed by hitting `AmbiguousParameter` against a real Postgres instance. A
            # trailing `::text` short-cast after a bind param isn't parsed correctly by
            # SQLAlchemy's text() either (also confirmed live), hence CAST(...) instead.
            text(
                f"SELECT * FROM report_view WHERE {where} "
                "AND (CAST(:status AS text) IS NULL OR status = :status) "
                "AND (CAST(:kind AS text) IS NULL OR kind = :kind) ORDER BY confirmed DESC, created_at DESC, id DESC"
            ),
            {"status": status, "kind": kind, **params},
        ).mappings().fetchall()
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
        with db.connect(person) as conn:
            conn.execute(
                text(f"UPDATE reports SET {', '.join(f'{k} = :{k}' for k in fields)} WHERE id = :id"),
                {**fields, "id": report_id},
            )
    return _visible_report(report_id, person)
