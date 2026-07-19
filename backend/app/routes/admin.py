import os
import tempfile
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import APIKeyHeader
from ..config import get_settings
from ..ingest import ingest_path
from ..schemas import IngestPathRequest

router = APIRouter(prefix="/admin", tags=["admin"])
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_admin(key: str | None = Depends(_api_key_header)) -> None:
    if not key or key != get_settings().ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")


@router.post("/ingest", dependencies=[Depends(_require_admin)])
async def ingest_upload(
    file: UploadFile = File(...),
    source: str | None = Form(default=None),
) -> dict:
    suffix = os.path.splitext(file.filename or "")[1] or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        n = await ingest_path(tmp_path, source_label=source or file.filename)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return {"chunks": n, "filename": file.filename}


@router.post("/ingest-path", dependencies=[Depends(_require_admin)])
async def ingest_by_path(body: IngestPathRequest) -> dict:
    n = await ingest_path(body.path, source_label=body.source, wipe=body.wipe)
    return {"chunks": n, "path": body.path}
