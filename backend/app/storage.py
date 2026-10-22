import httpx

from app.config import settings


def create_signed_upload_url(bucket: str, path: str) -> str:
    """Issues a short-lived, browser-usable upload URL via Supabase Storage's own signing
    endpoint (POST .../object/upload/sign/{bucket}/{path} -> {url, token}). The service-role
    key never leaves the backend; only the resulting signed URL does."""
    r = httpx.post(
        f"{settings.supabase_url}/storage/v1/object/upload/sign/{bucket}/{path}",
        headers={
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        },
        json={},
        timeout=10,
    )
    r.raise_for_status()
    return f"{settings.supabase_url}/storage/v1{r.json()['url']}"
