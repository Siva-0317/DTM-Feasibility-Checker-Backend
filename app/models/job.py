from enum import Enum
from typing import Literal, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

class Job(BaseModel):
    id: str
    filename: str
    door_type: Literal["front", "rear"] = "front"
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: Optional[Dict[str, Any]] = None
