import secrets
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app import auth, db
from app.config import settings
from app.schemas import (
    Application,
    ApplicationCreate,
    ApplicationStageUpdate,
    Candidate,
    CandidateCreate,
    CandidateUpdate,
    JobPosting,
    JobPostingCreate,
    ResumeUploadUrl,
)

router = APIRouter()
Recruiter = Annotated[dict, Depends(auth.recruiter_access)]

_APPLICATION_SQL = """
SELECT a.id, a.job_posting_id, a.candidate_id, c.name AS candidate_name, a.stage, a.created_at
FROM applications a JOIN candidates c ON c.id = a.candidate_id
"""


def _create_signed_upload_url(path: str) -> str:
    """Issues a short-lived, browser-usable upload URL via Supabase Storage's own signing
    endpoint - verified directly against the local Storage API (POST .../object/upload/sign/
    {bucket}/{path} -> {url, token}) while building this, not assumed from memory. The
    service-role key never leaves the backend; only the resulting signed URL does."""
    r = httpx.post(
        f"{settings.supabase_url}/storage/v1/object/upload/sign/{settings.storage_resume_bucket}/{path}",
        headers={
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        },
        json={},
        timeout=10,
    )
    r.raise_for_status()
    return f"{settings.supabase_url}/storage/v1{r.json()['url']}"


@router.get("/job-postings", response_model=list[JobPosting])
def list_job_postings(person: Recruiter) -> list[JobPosting]:
    with db.connect(person) as conn:
        rows = conn.execute(
            text(
                "SELECT id, plant_id, title, department_id, status, created_by, created_at "
                "FROM job_postings ORDER BY created_at DESC"
            )
        ).mappings().fetchall()
    return [JobPosting(**r) for r in rows]


@router.post("/job-postings", response_model=JobPosting, status_code=201)
def create_job_posting(req: JobPostingCreate, person: Recruiter) -> JobPosting:
    with db.connect(person) as conn:
        row = conn.execute(
            text(
                "INSERT INTO job_postings (plant_id, title, department_id, created_by) "
                "VALUES (:plant_id, :title, :department_id, :created_by) "
                "RETURNING id, plant_id, title, department_id, status, created_by, created_at"
            ),
            {"plant_id": person["plant_id"], "created_by": person["id"], **req.model_dump()},
        ).mappings().fetchone()
    return JobPosting(**row)


@router.get("/candidates", response_model=list[Candidate])
def list_candidates(person: Recruiter) -> list[Candidate]:
    with db.connect(person) as conn:
        rows = conn.execute(
            text("SELECT id, name, phone, email, resume_storage_path FROM candidates ORDER BY id DESC")
        ).mappings().fetchall()
    return [Candidate(**r) for r in rows]


@router.post("/candidates", response_model=Candidate, status_code=201)
def create_candidate(req: CandidateCreate, person: Recruiter) -> Candidate:
    with db.connect(person) as conn:
        row = conn.execute(
            text(
                "INSERT INTO candidates (name, phone, email) VALUES (:name, :phone, :email) "
                "RETURNING id, name, phone, email, resume_storage_path"
            ),
            req.model_dump(),
        ).mappings().fetchone()
    return Candidate(**row)


@router.post("/candidates/{candidate_id}/resume-upload-url", response_model=ResumeUploadUrl)
def create_resume_upload_url(candidate_id: int, person: Recruiter) -> ResumeUploadUrl:
    with db.connect(person) as conn:
        if not conn.execute(text("SELECT 1 FROM candidates WHERE id = :id"), {"id": candidate_id}).fetchone():
            raise HTTPException(404, "candidate not found")
    path = f"{candidate_id}/{secrets.token_hex(8)}.pdf"
    return ResumeUploadUrl(upload_url=_create_signed_upload_url(path), storage_path=path)


@router.patch("/candidates/{candidate_id}", response_model=Candidate)
def update_candidate(candidate_id: int, req: CandidateUpdate, person: Recruiter) -> Candidate:
    """Called once the browser has PUT the file to the signed URL above, to record where it
    landed - the backend never sees the file bytes themselves."""
    with db.connect(person) as conn:
        row = conn.execute(
            text(
                "UPDATE candidates SET resume_storage_path = :resume_storage_path WHERE id = :id "
                "RETURNING id, name, phone, email, resume_storage_path"
            ),
            {"resume_storage_path": req.resume_storage_path, "id": candidate_id},
        ).mappings().fetchone()
    if not row:
        raise HTTPException(404, "candidate not found")
    return Candidate(**row)


@router.get("/applications", response_model=list[Application])
def list_applications(person: Recruiter, job_posting_id: int | None = None) -> list[Application]:
    with db.connect(person) as conn:
        rows = conn.execute(
            text(
                f"SELECT * FROM ({_APPLICATION_SQL}) AS a "
                "WHERE (CAST(:jp AS bigint) IS NULL OR job_posting_id = :jp) ORDER BY created_at DESC"
            ),
            {"jp": job_posting_id},
        ).mappings().fetchall()
    return [Application(**r) for r in rows]


@router.post("/applications", response_model=Application, status_code=201)
def create_application(req: ApplicationCreate, person: Recruiter) -> Application:
    with db.connect(person) as conn:
        application_id = conn.execute(
            text(
                "INSERT INTO applications (job_posting_id, candidate_id) "
                "VALUES (:job_posting_id, :candidate_id) RETURNING id"
            ),
            req.model_dump(),
        ).scalar_one()
        row = conn.execute(text(f"{_APPLICATION_SQL} WHERE a.id = :id"), {"id": application_id}).mappings().fetchone()
    return Application(**row)


@router.patch("/applications/{application_id}", response_model=Application)
def update_application_stage(application_id: int, req: ApplicationStageUpdate, person: Recruiter) -> Application:
    with db.connect(person) as conn:
        result = conn.execute(
            text("UPDATE applications SET stage = :stage WHERE id = :id"), {"stage": req.stage, "id": application_id}
        )
        if result.rowcount == 0:
            raise HTTPException(404, "application not found")
        row = conn.execute(text(f"{_APPLICATION_SQL} WHERE a.id = :id"), {"id": application_id}).mappings().fetchone()
    return Application(**row)
