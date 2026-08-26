import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import APIKeyHeader
from ..config import get_settings
from ..ingest import DATA_ROOT, ingest_path
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


def _resolve_data_path(raw: str) -> Path:
    """Yolu backend/data/ altina hapseder.

    Onceden body.path dogrudan Path()'e gidiyordu: sizmis bir admin key,
    sunucudaki her .md/.txt/.pdf/.docx'i vektor DB'ye yazip chatbot uzerinden
    okutabilirdi — yani key sizintisini bir dosya okuma primitifine cevirirdi.

    .resolve() her iki tarafta cagriliyor; boylece ../ ve symlink kacislari da kapanir.
    """
    try:
        target = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail="invalid path") from exc
    if not target.is_relative_to(DATA_ROOT.resolve()):
        raise HTTPException(status_code=400, detail="path must be under backend/data/")
    return target


@router.post("/ingest-path", dependencies=[Depends(_require_admin)])
async def ingest_by_path(body: IngestPathRequest) -> dict:
    target = _resolve_data_path(body.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="path not found")
    n = await ingest_path(str(target), source_label=body.source)
    return {"chunks": n, "path": str(target)}
