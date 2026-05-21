from pydantic import BaseModel
from typing import Dict, List, Optional


class KPIReport(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress: int
    pending: int
    resolved: int
    resolution_rate: float
    sla_breach_count: int
    sla_compliance_rate: float
    avg_response_time_hours: Optional[float] = None
    avg_resolution_time_hours: Optional[float] = None
    fcr_rate: float
    escalation_rate: float
    tickets_by_priority: Dict[str, int]
    tickets_by_category: List[Dict]
    tickets_by_level: Dict[str, int]
    tickets_by_analyst: List[Dict]
