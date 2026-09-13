import os
import aiofiles
from fastapi import UploadFile

async def save_upload_file(file: UploadFile, upload_dir: str) -> str:
    """Saves file, returns path."""
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    async with aiofiles.open(file_path, 'wb') as out_file:
        while content := await file.read(1024 * 1024):  # read 1MB at a time
            await out_file.write(content)
            
    return file_path

async def cleanup_file(path: str) -> None:
    """Removes a file from the filesystem."""
    if os.path.exists(path):
        os.remove(path)

def get_output_path(job_id: str, output_dir: str, ext: str) -> str:
    """Generates an output path for a job."""
    os.makedirs(output_dir, exist_ok=True)
    if not ext.startswith("."):
        ext = f".{ext}"
    return os.path.join(output_dir, f"{job_id}{ext}")

def validate_file_extension(filename: str) -> bool:
    """Allow .stp, .step only"""
    allowed_extensions = {".stp", ".step"}
    _, ext = os.path.splitext(filename.lower())
    return ext in allowed_extensions
