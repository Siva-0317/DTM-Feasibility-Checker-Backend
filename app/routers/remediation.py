from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.models.job import JobStatus
from app.models.dtm_result import DTMReport
from app.services.ai_engine import generate_remediation_report

router = APIRouter()

class RemediationRequest(BaseModel):
    job_id: str

def get_jobs():
    from app.main import jobs
    return jobs

@router.post("")
async def request_remediation(req: RemediationRequest):
    jobs = get_jobs()
    
    job_id = req.job_id
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = jobs[job_id]
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Job is not COMPLETE. Cannot generate remediation.")
        
    dtm_report_data = job.result.get("dtm_report")
    if not dtm_report_data:
        raise HTTPException(status_code=400, detail="No DTM report found for this job.")
        
    try:
        dtm_report = DTMReport(**dtm_report_data)
        remediation_result = await generate_remediation_report(dtm_report, settings)
        return remediation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate remediation: {e}")
