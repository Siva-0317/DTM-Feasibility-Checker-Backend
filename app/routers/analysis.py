import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter()

def get_jobs():
    from app.main import jobs
    return jobs

@router.get("/{job_id}")
async def get_job_analysis(job_id: str):
    jobs = get_jobs()
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return jobs[job_id]

@router.get("/{job_id}/mesh")
async def get_job_mesh(job_id: str):
    jobs = get_jobs()
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    glb_path = os.path.join(settings.output_dir, f"{job_id}.glb")
    if not os.path.exists(glb_path):
        raise HTTPException(status_code=404, detail="Mesh file not found")
        
    return FileResponse(glb_path, media_type="model/gltf-binary", filename=f"{job_id}.glb")
