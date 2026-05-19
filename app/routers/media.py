import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.config import get_settings, Settings

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/frames/{filename}")
async def get_frame(filename: str, settings: Settings = Depends(get_settings)):
    safe_name = os.path.basename(filename)
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = os.path.join(settings.media_root, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Frame not found")

    return FileResponse(path)
