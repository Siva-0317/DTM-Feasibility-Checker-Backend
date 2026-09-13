from typing import Literal, Optional, List, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class DTMRuleResult(BaseModel):
    rule_id: int
    rule_name: str
    status: Literal["PASS", "FAIL", "WARN"]
    measured_value: Optional[float] = None
    threshold: Optional[float] = None
    unit: str
    defect_coordinates: List[Tuple[float, float, float]] = Field(default_factory=list)
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    description: str

class DTMReport(BaseModel):
    job_id: str
    door_type: str
    rules: List[DTMRuleResult] = Field(default_factory=list)
    overall_status: str
    pass_count: int
    fail_count: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
