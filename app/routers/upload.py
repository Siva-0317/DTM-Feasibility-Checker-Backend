import uuid
import os
import logging
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException

from app.config import settings
from app.models.job import Job, JobStatus
from app.utils.file_handler import validate_file_extension, save_upload_file
from app.services.cad_parser import load_step_file, extract_geometry_report
from app.services.dtm_engine import run_all_rules
from app.services.mesh_converter import convert_step_to_glb

logger = logging.getLogger(__name__)
router = APIRouter()

def get_jobs():
    from app.main import jobs
    return jobs

def process_cad_job(job_id: str, file_path: str, door_type: str):
    jobs = get_jobs()
    try:
        job = jobs[job_id]
        job.status = JobStatus.PROCESSING
        
        shape = load_step_file(file_path)
        geometry_report = extract_geometry_report(shape)
        
        dtm_report = run_all_rules(shape, geometry_report, job_id, door_type)
        glb_path = convert_step_to_glb(file_path, job_id, settings.output_dir)
        
        job.result = {
            "dtm_report": dtm_report.model_dump(),
            "glb_url": f"/api/analysis/{job_id}/mesh"
        }
        job.status = JobStatus.COMPLETE
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        if job_id in jobs:
            jobs[job_id].status = JobStatus.FAILED
            jobs[job_id].result = {"error": str(e)}

@router.post("")
async def upload_step_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    door_type: str = Form("front")
):
    jobs = get_jobs()
    
    if not validate_file_extension(file.filename):
        raise HTTPException(status_code=400, detail="Invalid file extension. Only .stp or .step allowed.")
        
    if file.size and (file.size / (1024 * 1024) > settings.max_file_size_mb):
        raise HTTPException(status_code=413, detail=f"File too large. Max allowed is {settings.max_file_size_mb} MB.")
        
    job_id = str(uuid.uuid4())
    job = Job(id=job_id, filename=file.filename, door_type=door_type, status=JobStatus.PENDING)
    jobs[job_id] = job
    
    file_path = await save_upload_file(file, settings.upload_dir)
    
    background_tasks.add_task(process_cad_job, job_id, file_path, door_type)
    
    return {"job_id": job_id, "status": "PENDING", "message": "Processing started"}
