import io
import csv
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.ticket import Ticket
from models.analyst import Analyst
from models.timeline import TicketTimeline
from models.category import Category


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_kpis(db: Session, start: datetime = None, end: datetime = None) -> dict:
    q = db.query(Ticket)
    if start:
        q = q.filter(Ticket.created_at >= start)
    if end:
        q = q.filter(Ticket.created_at <= end)

    tickets = q.all()
    total = len(tickets)
    if total == 0:
        return _empty_kpis()

    open_t = sum(1 for t in tickets if t.status == "Aberto")
    in_prog = sum(1 for t in tickets if t.status == "Em andamento")
    pending = sum(1 for t in tickets if t.status == "Pendente")
    resolved = sum(1 for t in tickets if t.status == "Resolvido")
    breaches = sum(1 for t in tickets if t.sla_breached)

    ticket_ids = {t.id for t in tickets}
    escalated_ids = {
        e.ticket_id
        for e in db.query(TicketTimeline.ticket_id)
        .filter(
            TicketTimeline.type == "escalate",
            TicketTimeline.ticket_id.in_(ticket_ids),
        )
        .all()
    }
    fcr_count = sum(
        1 for t in tickets if t.status == "Resolvido" and t.id not in escalated_ids
    )

    response_times, resolution_times = [], []
    for t in tickets:
        if t.sla_responded_at and t.created_at:
            delta = (_utc(t.sla_responded_at) - _utc(t.created_at)).total_seconds() / 3600
            response_times.append(delta)
        if t.resolved_at and t.created_at:
            delta = (_utc(t.resolved_at) - _utc(t.created_at)).total_seconds() / 3600
            resolution_times.append(delta)

    by_priority: dict = {}
    by_level: dict = {}
    by_category: dict = {}
    by_analyst_map: dict = {}

    for t in tickets:
        by_priority[t.priority] = by_priority.get(t.priority, 0) + 1
        by_level[t.level] = by_level.get(t.level, 0) + 1
        key = t.category_id or 0
        by_category[key] = by_category.get(key, 0) + 1
        if t.analyst_id:
            rec = by_analyst_map.setdefault(t.analyst_id, {"count": 0, "res": []})
            rec["count"] += 1
            if t.resolved_at and t.created_at:
                rec["res"].append(
                    (_utc(t.resolved_at) - _utc(t.created_at)).total_seconds() / 3600
                )

    categories = {c.id: c.name for c in db.query(Category).all()}
    analysts = {a.id: a.name for a in db.query(Analyst).all()}

    by_category_list = sorted(
        [{"category": categories.get(k, "Sem categoria"), "count": v} for k, v in by_category.items()],
        key=lambda x: -x["count"],
    )
    by_analyst_list = [
        {
            "analyst": analysts.get(k, f"Analista {k}"),
            "count": v["count"],
            "avg_resolution": round(sum(v["res"]) / len(v["res"]), 1) if v["res"] else None,
        }
        for k, v in by_analyst_map.items()
    ]

    return {
        "total_tickets": total,
        "open_tickets": open_t,
        "in_progress": in_prog,
        "pending": pending,
        "resolved": resolved,
        "resolution_rate": round(resolved / total * 100, 1),
        "sla_breach_count": breaches,
        "sla_compliance_rate": round((1 - breaches / total) * 100, 1),
        "avg_response_time_hours": round(sum(response_times) / len(response_times), 1) if response_times else None,
        "avg_resolution_time_hours": round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None,
        "fcr_rate": round(fcr_count / resolved * 100, 1) if resolved else 0.0,
        "escalation_rate": round(len(escalated_ids & ticket_ids) / total * 100, 1),
        "tickets_by_priority": by_priority,
        "tickets_by_category": by_category_list,
        "tickets_by_level": by_level,
        "tickets_by_analyst": by_analyst_list,
    }


def _empty_kpis() -> dict:
    return {
        "total_tickets": 0,
        "open_tickets": 0,
        "in_progress": 0,
        "pending": 0,
        "resolved": 0,
        "resolution_rate": 0.0,
        "sla_breach_count": 0,
        "sla_compliance_rate": 100.0,
        "avg_response_time_hours": None,
        "avg_resolution_time_hours": None,
        "fcr_rate": 0.0,
        "escalation_rate": 0.0,
        "tickets_by_priority": {},
        "tickets_by_category": [],
        "tickets_by_level": {},
        "tickets_by_analyst": [],
    }


def export_csv(db: Session) -> bytes:
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    categories = {c.id: c.name for c in db.query(Category).all()}
    analysts = {a.id: a.name for a in db.query(Analyst).all()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Número", "Título", "Prioridade", "Status", "Nível",
        "Categoria", "Analista", "SLA%", "SLA Violado",
        "Aberto em", "Atualizado em", "Resolvido em",
    ])
    for t in tickets:
        writer.writerow([
            t.ticket_number,
            t.title,
            t.priority,
            t.status,
            t.level,
            categories.get(t.category_id, ""),
            analysts.get(t.analyst_id, ""),
            t.sla_percentage,
            "Sim" if t.sla_breached else "Não",
            t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else "",
            t.updated_at.strftime("%d/%m/%Y %H:%M") if t.updated_at else "",
            t.resolved_at.strftime("%d/%m/%Y %H:%M") if t.resolved_at else "",
        ])

    return output.getvalue().encode("utf-8-sig")
