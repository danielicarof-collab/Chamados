"""
Chatbot de abertura de chamados via conversa guiada.
Suporta canais: web, teams.

Fluxo:
  greeting → collecting_description → collecting_impact →
  collecting_equipment → confirming → done
"""
import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.chatbot import ChatbotSession
from models.user import User
from models.ticket import Ticket
from models.timeline import TicketTimeline
from services.ai_service import analyze_ticket
from services.sla_service import calculate_sla_deadlines
from services.notification_service import notify_ticket_created
from services.teams_service import send_teams_notification

logger = logging.getLogger(__name__)

# Mapeamento de resposta rápida de impacto para texto
_IMPACT_MAP = {
    "1": "Alto — não consigo trabalhar",
    "2": "Médio — trabalho com dificuldades",
    "3": "Baixo — impacto mínimo",
    "alto": "Alto — não consigo trabalhar",
    "médio": "Médio — trabalho com dificuldades",
    "baixo": "Baixo — impacto mínimo",
    "medio": "Médio — trabalho com dificuldades",
}

_QUICK_IMPACT = ["1 — Não consigo trabalhar", "2 — Com dificuldades", "3 — Impacto mínimo"]
_QUICK_CONFIRM = ["Sim, confirmar", "Não, corrigir"]
_QUICK_DONE = ["Abrir outro chamado", "Verificar meus chamados"]


def _next_ticket_number(db: Session) -> str:
    count = db.query(Ticket).count()
    return f"TI-{count + 1:04d}"


def _get_or_create_session(session_id: str, channel: str, db: Session) -> ChatbotSession:
    session = db.query(ChatbotSession).filter(ChatbotSession.session_id == session_id).first()
    if not session:
        session = ChatbotSession(
            session_id=session_id,
            channel=channel,
            context={"state": "greeting", "history": []},
        )
        db.add(session)
        db.flush()
    return session


def _append_history(ctx: dict, role: str, text: str) -> None:
    ctx.setdefault("history", [])
    ctx["history"].append({
        "role": role,
        "text": text,
        "ts": datetime.now(timezone.utc).isoformat(),
    })


async def process_message(
    session_id: str,
    message: str,
    channel: str,
    db: Session,
    user_email: str | None = None,
    user_name: str | None = None,
) -> dict:
    """
    Processa uma mensagem do usuário e retorna a resposta do bot.
    Retorna: {session_id, response, state, ticket_number, quick_replies}
    """
    session = _get_or_create_session(session_id, channel, db)
    ctx: dict = dict(session.context or {})
    ctx.setdefault("state", "greeting")
    ctx.setdefault("history", [])

    _append_history(ctx, "user", message)

    state = ctx["state"]
    response = ""
    quick_replies = None
    ticket_number = None

    try:
        # ── Estado: greeting ──────────────────────────────────────────────────
        if state == "greeting":
            # Checar se o usuário está autenticado no portal
            if user_email:
                ctx["user_email"] = user_email
                ctx["user_name"] = user_name or user_email.split("@")[0].title()
                # Verificar no banco
                user = db.query(User).filter(User.email == user_email, User.active == True).first()
                if user:
                    ctx["user_id"] = user.id
                    ctx["user_name"] = user.name
                ctx["state"] = "collecting_description"
                response = (
                    f"Olá, **{ctx['user_name']}**! 👋 Sou o assistente de TI.\n\n"
                    "Descreva o problema que você está enfrentando. "
                    "Quanto mais detalhes, melhor!"
                )
            else:
                # Sem autenticação — pedir e-mail
                email_input = message.strip().lower()
                if "@" in email_input and "." in email_input:
                    # Validar e-mail no banco
                    user = db.query(User).filter(
                        User.email == email_input, User.active == True
                    ).first()
                    if user:
                        ctx["user_email"] = user.email
                        ctx["user_name"] = user.name
                        ctx["user_id"] = user.id
                        ctx["state"] = "collecting_description"
                        response = (
                            f"Olá, **{user.name}**! 👋 Encontrei seu cadastro.\n\n"
                            "Descreva o problema que você está enfrentando:"
                        )
                    else:
                        # Usuário não cadastrado — usar e-mail mesmo assim
                        ctx["user_email"] = email_input
                        ctx["user_name"] = email_input.split("@")[0].title()
                        ctx["state"] = "collecting_description"
                        response = (
                            f"Olá! 👋 Sou o assistente de TI.\n\n"
                            "Descreva o problema que você está enfrentando:"
                        )
                else:
                    # Primeira mensagem — pedir e-mail
                    response = (
                        "Olá! 👋 Sou o assistente de TI da empresa.\n\n"
                        "Posso abrir um chamado para você agora mesmo! "
                        "Para começar, qual é o seu **e-mail corporativo**?"
                    )

        # ── Estado: collecting_description ────────────────────────────────────
        elif state == "collecting_description":
            if len(message.strip()) < 10:
                response = (
                    "Preciso de um pouco mais de detalhes. "
                    "Descreva o problema com mais informações:"
                )
            else:
                ctx["description"] = message.strip()
                ctx["state"] = "collecting_impact"
                response = (
                    "Entendido! Qual é o **impacto** deste problema no seu trabalho?\n\n"
                    "Selecione uma opção:"
                )
                quick_replies = _QUICK_IMPACT

        # ── Estado: collecting_impact ─────────────────────────────────────────
        elif state == "collecting_impact":
            msg_lower = message.strip().lower()
            # Aceitar número (1/2/3) ou palavra-chave
            key = msg_lower.split("—")[0].strip()
            impact = _IMPACT_MAP.get(key) or _IMPACT_MAP.get(msg_lower)
            if not impact:
                # Tentar extrair palavra-chave do texto
                for k, v in _IMPACT_MAP.items():
                    if k in msg_lower:
                        impact = v
                        break
            if not impact:
                impact = "Médio — trabalho com dificuldades"  # fallback

            ctx["impact"] = impact
            ctx["state"] = "collecting_equipment"
            response = (
                "Em qual **equipamento** ou sistema ocorre o problema?\n"
                "*(Ex: Notebook Dell, Desktop, Teams, SAP, impressora HP)*"
            )

        # ── Estado: collecting_equipment ──────────────────────────────────────
        elif state == "collecting_equipment":
            ctx["equipment"] = message.strip() if message.strip() else "Não informado"
            ctx["state"] = "confirming"

            # Chamar IA para classificar prioridade
            try:
                ai_result = await analyze_ticket(
                    title=ctx["description"][:100],
                    description=ctx["description"],
                    impact=ctx["impact"],
                )
            except Exception:
                ai_result = {"priority": "Média", "level": "N1",
                             "justification": "Análise automática", "confidence": 0.5}

            ctx["ai_analysis"] = ai_result
            priority = ai_result.get("priority", "Média")
            level = ai_result.get("level", "N1")

            _PRIORITY_EMOJIS = {"Crítica": "🔴", "Alta": "🟠", "Média": "🟡", "Baixa": "🟢"}
            p_emoji = _PRIORITY_EMOJIS.get(priority, "⚪")

            response = (
                f"Perfeito! Vou abrir o chamado com as seguintes informações:\n\n"
                f"📋 **Problema:** {ctx['description'][:200]}\n"
                f"💻 **Equipamento:** {ctx['equipment']}\n"
                f"📊 **Impacto:** {ctx['impact']}\n"
                f"{p_emoji} **Prioridade (IA):** {priority} — {level}\n\n"
                "Posso confirmar a abertura?"
            )
            quick_replies = _QUICK_CONFIRM

        # ── Estado: confirming ────────────────────────────────────────────────
        elif state == "confirming":
            msg_lower = message.strip().lower()
            if any(w in msg_lower for w in ["sim", "confirmar", "ok", "yes", "s", "1"]):
                # Criar o chamado
                ai = ctx.get("ai_analysis", {})
                user_id = ctx.get("user_id")

                # Buscar departamento do usuário
                dept_id = None
                if user_id:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user and user.department_id:
                        dept_id = user.department_id

                ticket_number_str = _next_ticket_number(db)
                ticket = Ticket(
                    ticket_number=ticket_number_str,
                    title=ctx["description"][:200],
                    description=ctx["description"],
                    priority=ai.get("priority", "Média"),
                    priority_source="ai",
                    status="Aberto",
                    level=ai.get("level", "N1"),
                    impact=ctx.get("impact", ""),
                    equipment=ctx.get("equipment", ""),
                    user_id=user_id,
                    department_id=dept_id,
                    ai_analysis=ai,
                )
                db.add(ticket)
                db.flush()

                calculate_sla_deadlines(db, ticket)

                # Auto-escalar Crítica para N2
                if ticket.priority == "Crítica" and ticket.level == "N1":
                    ticket.level = "N2"
                    db.add(TicketTimeline(
                        ticket_id=ticket.id,
                        type="escalate",
                        action="Escalado automaticamente para N2 (prioridade Crítica)",
                        by_name="Sistema",
                        icon="arrow-up",
                        icon_color="red",
                    ))

                db.add(TicketTimeline(
                    ticket_id=ticket.id,
                    type="open",
                    action=f"Chamado {ticket_number_str} aberto via Chatbot ({channel})",
                    by_name=ctx.get("user_name", "Chatbot"),
                    icon="message",
                    icon_color="blue",
                ))
                db.add(TicketTimeline(
                    ticket_id=ticket.id,
                    type="ai",
                    action=f"Prioridade '{ticket.priority}' definida pela IA",
                    note=ai.get("justification", ""),
                    by_name="IA",
                    icon="robot",
                    icon_color="purple",
                ))

                # Vincular sessão ao ticket
                session.ticket_id = ticket.id

                # Notificações
                try:
                    notify_ticket_created(ticket, db)
                except Exception as exc:
                    logger.error("Falha na notificação de criação: %s", exc)

                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(send_teams_notification(ticket, "created"))
                except Exception:
                    pass  # Teams é opcional

                db.commit()

                ctx["state"] = "done"
                ctx["ticket_number"] = ticket_number_str
                ticket_number = ticket_number_str

                response = (
                    f"✅ **Chamado {ticket_number_str} aberto com sucesso!**\n\n"
                    f"Nossa equipe de TI entrará em contato em breve. "
                    f"Você receberá atualizações por e-mail em **{ctx.get('user_email', '')}**.\n\n"
                    f"Posso ajudar com mais alguma coisa?"
                )
                quick_replies = _QUICK_DONE

            elif any(w in msg_lower for w in ["não", "nao", "corrigir", "no", "n", "2"]):
                ctx["state"] = "collecting_description"
                ctx.pop("description", None)
                ctx.pop("equipment", None)
                ctx.pop("impact", None)
                ctx.pop("ai_analysis", None)
                response = "Sem problema! Vamos recomeçar. Descreva novamente o seu problema:"
            else:
                response = "Por favor, confirme: deseja abrir o chamado? (Sim / Não)"
                quick_replies = _QUICK_CONFIRM

        # ── Estado: done ──────────────────────────────────────────────────────
        elif state == "done":
            ticket_number = ctx.get("ticket_number")
            msg_lower = message.strip().lower()
            if "outro" in msg_lower or "novo" in msg_lower or "abrir" in msg_lower:
                # Reiniciar para novo chamado
                ctx = {
                    "state": "collecting_description",
                    "history": ctx["history"],
                    "user_email": ctx.get("user_email"),
                    "user_name": ctx.get("user_name"),
                    "user_id": ctx.get("user_id"),
                }
                response = "Claro! Descreva o próximo problema:"
            else:
                response = (
                    f"Seu chamado **{ticket_number}** está na fila de atendimento. "
                    "Assim que houver uma atualização, você receberá um e-mail. "
                    "Posso ajudar com mais alguma coisa?"
                )
                quick_replies = _QUICK_DONE

        else:
            ctx["state"] = "greeting"
            response = "Olá! Como posso ajudar? Qual é o seu e-mail corporativo?"

    except Exception as exc:
        logger.exception("Erro no chatbot (session=%s): %s", session_id, exc)
        ctx["state"] = "error"
        response = (
            "Desculpe, ocorreu um erro interno. "
            "Tente novamente ou abra o chamado diretamente pelo painel."
        )

    _append_history(ctx, "bot", response)
    session.context = ctx
    db.add(session)

    return {
        "session_id": session_id,
        "response": response,
        "state": ctx["state"],
        "ticket_number": ticket_number,
        "quick_replies": quick_replies,
    }
