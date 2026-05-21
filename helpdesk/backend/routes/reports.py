from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io

from database import get_db
from models.analyst import Analyst
from models.ticket import Ticket
from models.category import Category
from schemas.reports import KPIReport
from services.report_service import get_kpis, export_csv
from middleware.auth import get_current_analyst

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/kpis", response_model=KPIReport)
def kpis(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    return get_kpis(db, start, end)


@router.get("/by-category")
def by_category(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    categories = {c.id: c.name for c in db.query(Category).all()}
    result: dict = {}
    for t in db.query(Ticket).all():
        key = categories.get(t.category_id, "Sem categoria")
        result[key] = result.get(key, 0) + 1
    return [{"category": k, "count": v} for k, v in sorted(result.items(), key=lambda x: -x[1])]


@router.get("/by-analyst")
def by_analyst(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    analysts = {a.id: a.name for a in db.query(Analyst).all()}
    result: dict = {}
    for t in db.query(Ticket).filter(Ticket.analyst_id.isnot(None)).all():
        key = analysts.get(t.analyst_id, f"#{t.analyst_id}")
        result[key] = result.get(key, 0) + 1
    return [{"analyst": k, "count": v} for k, v in sorted(result.items(), key=lambda x: -x[1])]


@router.get("/by-priority")
def by_priority(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    result: dict = {}
    for t in db.query(Ticket).all():
        result[t.priority] = result.get(t.priority, 0) + 1
    return result


@router.get("/sla-performance")
def sla_performance(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    q = db.query(Ticket)
    if start:
        q = q.filter(Ticket.created_at >= start)
    if end:
        q = q.filter(Ticket.created_at <= end)
    tickets = q.all()
    total = len(tickets)
    breached = sum(1 for t in tickets if t.sla_breached)
    return {
        "total": total,
        "breached": breached,
        "compliant": total - breached,
        "compliance_rate": round((1 - breached / total) * 100, 1) if total else 100.0,
    }


@router.get("/escalation")
def escalation_report(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    from models.timeline import TicketTimeline

    escalated_n2 = (
        db.query(TicketTimeline)
        .filter(TicketTimeline.type == "escalate", TicketTimeline.action.contains("N2"))
        .count()
    )
    escalated_n3 = (
        db.query(TicketTimeline)
        .filter(TicketTimeline.type == "escalate", TicketTimeline.action.contains("N3"))
        .count()
    )
    total = db.query(Ticket).count()
    return {
        "total_tickets": total,
        "escalated_to_n2": escalated_n2,
        "escalated_to_n3": escalated_n3,
        "escalation_rate_n2": round(escalated_n2 / total * 100, 1) if total else 0.0,
        "escalation_rate_n3": round(escalated_n3 / total * 100, 1) if total else 0.0,
    }


@router.get("/resolution-time")
def resolution_time(
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    from datetime import timezone

    tickets = db.query(Ticket).filter(Ticket.resolved_at.isnot(None)).all()
    if not tickets:
        return {"avg_resolution_hours": None, "total_resolved": 0}

    def _utc(dt):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    times = [
        (_utc(t.resolved_at) - _utc(t.created_at)).total_seconds() / 3600
        for t in tickets
        if t.created_at
    ]
    return {
        "avg_resolution_hours": round(sum(times) / len(times), 1) if times else None,
        "total_resolved": len(tickets),
    }


@router.get("/export")
def export(
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
    _: Analyst = Depends(get_current_analyst),
):
    data = export_csv(db)
    filename = f"chamados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
