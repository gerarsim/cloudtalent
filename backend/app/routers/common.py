from pathlib import PurePath
from typing import TypeVar
from urllib.parse import quote

from fastapi import HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

T = TypeVar("T")


def get_or_404(db: Session, model: type[T], obj_id: int, label: str) -> T:
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} {obj_id} introuvable")
    return obj


async def read_upload(file: UploadFile, types: dict[str, str], max_bytes: int, label: str) -> tuple[str, str, bytes]:
    """Valide un fichier envoyé : extension dans `types` (qui fixe aussi le type MIME, jamais
    celui du client), taille max. Renvoie (nom, type, contenu)."""
    filename = PurePath(file.filename or "").name[:200]
    content_type = types.get(PurePath(filename).suffix.lower())
    if content_type is None:
        formats = ", ".join(ext[1:].upper() for ext in types)
        raise HTTPException(status_code=422, detail=f"Format de {label} accepté : {formats}")
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"{label} trop volumineux ({max_bytes // (1024 * 1024)} Mo maximum)")
    if not data:
        raise HTTPException(status_code=422, detail="Fichier vide")
    return filename, content_type, data


def file_response(data: bytes, content_type: str, filename: str) -> Response:
    # nosniff : le navigateur ne devine pas un autre type que celui de notre liste blanche
    return Response(data, media_type=content_type, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        "X-Content-Type-Options": "nosniff",
    })
