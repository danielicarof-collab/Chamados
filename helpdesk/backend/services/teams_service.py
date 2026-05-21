"""
Serviço de notificações para Microsoft Teams via Incoming Webhook.
Utiliza Adaptive Cards v1.5 para mensagens ricas e interativas.
"""
import json
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

_PRIORITY_COLORS = {
    "Crítica": "attention",   # vermelho
    "Alta":    "warning",     # laranja
    "Média":   "good",        # amarelo-verde (Teams default)
    "Baixa":   "accent",      # azul
}

_PRIORITY_EMOJIS = {
    "Crítica": "🔴",
    "Alta":    "🟠",
    "Média":   "🟡",
    "Baixa":   "🟢",
}

_EVENT_TITLES = {
    "created":   ("🎫", "Novo chamado aberto"),
    "assigned":  ("👤", "Chamado atribuído"),
    "escalated": ("⬆️", "Chamado escalado"),
    "resolved":  ("✅", "Chamado resolvido"),
    "breached":  ("🚨", "SLA violado"),
    "warning":   ("⚠️", "Alerta de SLA — 70%"),
    "reopened":  ("🔄", "Chamado reaberto"),
    "commented": ("💬", "Nova atualização"),
}


def _build_adaptive_card(ticket, event: str) -> dict:
    """Monta um Adaptive Card compatível com Teams 1.5."""
    emoji, event_title = _EVENT_TITLES.get(event, ("📋", "Atualização de chamado"))
    priority_color = _PRIORITY_COLORS.get(ticket.priority, "default")
    priority_label = f"{_PRIORITY_EMOJIS.get(ticket.priority, '')} {ticket.priority}"
    analyst_name   = ticket.analyst.name if ticket.analyst else "Não atribuído"
    system_url     = f"{settings.BASE_URL}/mockup.html"

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.5",
                    "body": [
                        # Cabeçalho com cor de prioridade
                        {
                            "type": "Container",
                            "style": priority_color,
                            "bleed": True,
                            "items": [
                                {
                                    "type": "ColumnSet",
                                    "columns": [
                                        {
                                            "type": "Column",
                                            "width": "auto",
                                            "items": [
                                                {
                                                    "type": "TextBlock",
                                                    "text": emoji,
                                                    "size": "ExtraLarge",
                                                }
                                            ],
                                        },
                                        {
                                            "type": "Column",
                                            "width": "stretch",
                                            "items": [
                                                {
                                                    "type": "TextBlock",
                                                    "text": event_title,
                                                    "weight": "Bolder",
                                                    "size": "Medium",
                                                    "color": "Light",
                                                },
                                                {
                                                    "type": "TextBlock",
                                                    "text": f"TI HelpDesk — {settings.COMPANY_NAME}",
                                                    "size": "Small",
                                                    "color": "Light",
                                                    "isSubtle": True,
                                                    "spacing": "None",
                                                },
                                            ],
                                        },
                                    ],
                                }
                            ],
                        },
                        # Corpo com detalhes
                        {
                            "type": "Container",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"**{ticket.ticket_number}** — {ticket.title}",
                                    "wrap": True,
                                    "size": "Medium",
                                    "spacing": "Medium",
                                },
                                {
                                    "type": "FactSet",
                                    "spacing": "Small",
                                    "facts": [
                                        {"title": "Prioridade", "value": priority_label},
                                        {"title": "Status",     "value": ticket.status},
                                        {"title": "Nível",      "value": ticket.level},
                                        {"title": "Analista",   "value": analyst_name},
                                        {"title": "SLA",        "value": f"{ticket.sla_percentage}% consumido"},
                                    ],
                                },
                            ],
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "Abrir no Painel",
                            "url": system_url,
                            "style": "positive",
                        }
                    ],
                    "msteams": {"width": "Full"},
                },
            }
        ],
    }
    return card


async def send_teams_notification(ticket, event: str) -> bool:
    """
    Envia notificação para o canal do Teams via Incoming Webhook.
    Retorna True em caso de sucesso, False caso contrário.
    """
    if not settings.TEAMS_WEBHOOK_URL:
        logger.debug("Teams webhook não configurado — notificação ignorada")
        return False

    payload = _build_adaptive_card(ticket, event)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.TEAMS_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                logger.info("Teams notification enviada: %s → %s", ticket.ticket_number, event)
                return True
            else:
                logger.warning(
                    "Teams webhook retornou %d para %s: %s",
                    response.status_code, ticket.ticket_number, response.text[:200],
                )
                return False
    except Exception as exc:
        logger.error("Falha ao enviar Teams notification para %s: %s", ticket.ticket_number, exc)
        return False
