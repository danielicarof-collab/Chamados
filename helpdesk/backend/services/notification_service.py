"""
Serviço de notificações por e-mail.
Cobre todos os eventos do ciclo de vida do chamado com templates HTML profissionais.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

logger = logging.getLogger(__name__)

# ── Paleta de cores (alinhada com o frontend) ──────────────────────────────────
_PRIORITY_COLORS = {
    "Crítica": "#ef4444",
    "Alta":    "#f97316",
    "Média":   "#eab308",
    "Baixa":   "#22c55e",
}
_PRIORITY_LABELS = {
    "Crítica": "🔴 Crítica",
    "Alta":    "🟠 Alta",
    "Média":   "🟡 Média",
    "Baixa":   "🟢 Baixa",
}


def _html_base(title: str, body_html: str, cta_url: str = "", cta_label: str = "") -> str:
    """Template base de e-mail — dark-friendly, compatível com principais clientes."""
    cta_btn = ""
    if cta_url and cta_label:
        cta_btn = f"""
        <tr>
          <td style="padding:0 32px 32px;">
            <a href="{cta_url}"
               style="display:inline-block;background:#3b82f6;color:#fff;text-decoration:none;
                      padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px;">
              {cta_label}
            </a>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#0b0f1a;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f1a;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#111827;border-radius:12px;
                      border:1px solid rgba(255,255,255,0.08);
                      box-shadow:0 8px 32px rgba(0,0,0,0.4);overflow:hidden;">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1e3a5f,#0f172a);
                       padding:24px 32px;border-bottom:1px solid rgba(255,255,255,0.08);">
              <span style="font-size:22px;font-weight:800;color:#e2e8f0;letter-spacing:-.5px;">
                🎫 TI HelpDesk
              </span>
              <span style="font-size:12px;color:#64748b;display:block;margin-top:2px;">
                {settings.COMPANY_NAME} — Sistema de Chamados de TI
              </span>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px 32px 24px;">
              {body_html}
            </td>
          </tr>
          {cta_btn}
          <!-- Footer -->
          <tr>
            <td style="padding:16px 32px 24px;
                       border-top:1px solid rgba(255,255,255,0.06);">
              <p style="margin:0;font-size:11px;color:#4b5a72;text-align:center;">
                Este é um e-mail automático do TI HelpDesk. Não responda diretamente.<br>
                {settings.COMPANY_NAME} · Departamento de TI
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _ticket_facts(ticket) -> str:
    """Bloco de detalhes do chamado (tabela de fatos)."""
    priority_color = _PRIORITY_COLORS.get(ticket.priority, "#94a3b8")
    priority_label = _PRIORITY_LABELS.get(ticket.priority, ticket.priority)
    analyst_name = ticket.analyst.name if ticket.analyst else "Não atribuído"
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:#1e2a40;border-radius:8px;overflow:hidden;margin:16px 0;">
      <tr>
        <td style="padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.06);">
          <span style="font-size:11px;color:#64748b;text-transform:uppercase;
                       letter-spacing:.07em;">Número</span>
          <span style="display:block;font-size:15px;font-weight:700;color:#e2e8f0;
                       margin-top:2px;">{ticket.ticket_number}</span>
        </td>
      </tr>
      <tr>
        <td style="padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.06);">
          <span style="font-size:11px;color:#64748b;text-transform:uppercase;
                       letter-spacing:.07em;">Título</span>
          <span style="display:block;font-size:14px;color:#e2e8f0;
                       margin-top:2px;">{ticket.title}</span>
        </td>
      </tr>
      <tr>
        <td style="padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.06);">
          <span style="font-size:11px;color:#64748b;text-transform:uppercase;
                       letter-spacing:.07em;">Prioridade</span>
          <span style="display:block;margin-top:4px;">
            <span style="background:{priority_color};color:#fff;font-size:12px;
                         font-weight:700;padding:2px 10px;border-radius:20px;">
              {priority_label}
            </span>
          </span>
        </td>
      </tr>
      <tr>
        <td style="padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.06);">
          <span style="font-size:11px;color:#64748b;text-transform:uppercase;
                       letter-spacing:.07em;">Status</span>
          <span style="display:block;font-size:14px;color:#e2e8f0;
                       margin-top:2px;">{ticket.status}</span>
        </td>
      </tr>
      <tr>
        <td style="padding:12px 16px;">
          <span style="font-size:11px;color:#64748b;text-transform:uppercase;
                       letter-spacing:.07em;">Analista responsável</span>
          <span style="display:block;font-size:14px;color:#e2e8f0;
                       margin-top:2px;">{analyst_name}</span>
        </td>
      </tr>
    </table>"""


def send_email(to: str | list[str], subject: str, html_body: str) -> bool:
    """Envia e-mail HTML. Suporta um ou múltiplos destinatários."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.debug("SMTP não configurado — notificação ignorada")
        return False

    recipients = [to] if isinstance(to, str) else to
    recipients = [r for r in recipients if r]  # remove vazios

    if not recipients:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.EMAIL_FROM
        msg["To"]      = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, recipients, msg.as_string())

        logger.info("E-mail enviado → %s | %s", recipients, subject)
        return True
    except Exception as exc:
        logger.error("Falha ao enviar e-mail → %s: %s", recipients, exc)
        return False


def _system_url(path: str = "") -> str:
    base = settings.BASE_URL.rstrip("/")
    return f"{base}{path}"


# ─────────────────────────────────────────────────────────────────────────────
# Eventos do chamado
# ─────────────────────────────────────────────────────────────────────────────

def notify_ticket_created(ticket, db=None) -> None:
    """Notifica o solicitante e a fila de TI quando um chamado é aberto."""
    user_email = ticket.user.email if ticket.user else None
    user_name  = ticket.user.name  if ticket.user else "Solicitante"

    system_url = _system_url("/portal.html")
    panel_url  = _system_url("/mockup.html")

    # ── E-mail para o solicitante ──
    if user_email:
        body = f"""
        <h2 style="color:#e2e8f0;margin:0 0 8px;">Seu chamado foi aberto! ✅</h2>
        <p style="color:#94a3b8;margin:0 0 16px;">
          Olá, <strong style="color:#e2e8f0;">{user_name}</strong>!
          Recebemos seu chamado e ele já está sendo tratado pela equipe de TI.
        </p>
        {_ticket_facts(ticket)}
        <p style="color:#94a3b8;font-size:13px;margin-top:16px;">
          Acompanhe o status pelo portal de chamados. Você receberá atualizações por e-mail.
        </p>"""
        send_email(
            user_email,
            f"[{ticket.ticket_number}] Chamado aberto: {ticket.title}",
            _html_base(f"Chamado {ticket.ticket_number} aberto", body, system_url, "Acompanhar Chamado"),
        )

    # ── E-mail para a fila de TI ──
    if settings.TEAM_EMAIL:
        body = f"""
        <h2 style="color:#e2e8f0;margin:0 0 8px;">Novo chamado recebido 🎫</h2>
        <p style="color:#94a3b8;margin:0 0 16px;">
          Um novo chamado foi aberto e aguarda atribuição.
        </p>
        {_ticket_facts(ticket)}"""
        send_email(
            settings.TEAM_EMAIL,
            f"[NOVO] [{ticket.ticket_number}] {ticket.title}",
            _html_base("Novo chamado", body, panel_url, "Abrir no Painel"),
        )


def notify_ticket_assigned(ticket, analyst_email: str, analyst_name: str) -> None:
    """Notifica o analista quando um chamado é atribuído a ele."""
    panel_url = _system_url("/mockup.html")
    body = f"""
    <h2 style="color:#e2e8f0;margin:0 0 8px;">Chamado atribuído a você 👤</h2>
    <p style="color:#94a3b8;margin:0 0 16px;">
      Olá, <strong style="color:#e2e8f0;">{analyst_name}</strong>!
      O chamado abaixo foi atribuído a você e aguarda sua ação.
    </p>
    {_ticket_facts(ticket)}
    <p style="color:#94a3b8;font-size:13px;margin-top:16px;">
      ⏱ Verifique o prazo de SLA e inicie o atendimento o quanto antes.
    </p>"""
    send_email(
        analyst_email,
        f"[ATRIBUÍDO] [{ticket.ticket_number}] {ticket.title}",
        _html_base("Chamado atribuído", body, panel_url, "Ver no Painel"),
    )


def notify_ticket_commented(ticket, comment: str) -> None:
    """Notifica o solicitante quando há uma nova atualização no chamado."""
    user_email = ticket.user.email if ticket.user else None
    if not user_email:
        return

    analyst_name = ticket.analyst.name if ticket.analyst else "Equipe de TI"
    system_url = _system_url("/portal.html")
    body = f"""
    <h2 style="color:#e2e8f0;margin:0 0 8px;">Nova atualização no seu chamado 💬</h2>
    <p style="color:#94a3b8;margin:0 0 16px;">
      A equipe de TI adicionou uma atualização ao seu chamado.
    </p>
    {_ticket_facts(ticket)}
    <div style="background:#1e2a40;border-left:3px solid #3b82f6;
                border-radius:0 8px 8px 0;padding:14px 16px;margin:16px 0;">
      <p style="margin:0;font-size:12px;color:#64748b;text-transform:uppercase;
                letter-spacing:.07em;">Mensagem de {analyst_name}</p>
      <p style="margin:6px 0 0;font-size:14px;color:#e2e8f0;">{comment}</p>
    </div>"""
    send_email(
        user_email,
        f"[ATUALIZAÇÃO] [{ticket.ticket_number}] {ticket.title}",
        _html_base("Atualização no chamado", body, system_url, "Ver Chamado"),
    )


def notify_ticket_escalated(ticket, notified_emails: list[str]) -> None:
    """Notifica a equipe quando um chamado é escalado."""
    if not notified_emails:
        return
    panel_url = _system_url("/mockup.html")
    level_color = {"N1": "#64748b", "N2": "#f97316", "N3": "#ef4444"}.get(ticket.level, "#94a3b8")
    body = f"""
    <h2 style="color:#e2e8f0;margin:0 0 8px;">Chamado escalado ⬆️</h2>
    <p style="color:#94a3b8;margin:0 0 16px;">
      O chamado abaixo foi escalado e agora requer atenção do nível
      <span style="background:{level_color};color:#fff;padding:2px 8px;
                   border-radius:4px;font-weight:700;">{ticket.level}</span>.
    </p>
    {_ticket_facts(ticket)}
    <p style="color:#f97316;font-size:13px;font-weight:600;margin-top:16px;">
      ⚠ SLA consumido: {ticket.sla_percentage}% — Ação imediata necessária.
    </p>"""
    send_email(
        notified_emails,
        f"[ESCALADO → {ticket.level}] [{ticket.ticket_number}] {ticket.title}",
        _html_base("Chamado escalado", body, panel_url, "Ver no Painel"),
    )


def notify_sla_warning(ticket, analyst_email: str) -> None:
    """Alerta quando o SLA atinge 70% do tempo consumido."""
    panel_url = _system_url("/mockup.html")
    body = f"""
    <h2 style="color:#eab308;margin:0 0 8px;">⚠ Alerta de SLA — 70% consumido</h2>
    <p style="color:#94a3b8;margin:0 0 16px;">
      O chamado abaixo atingiu 70% do tempo de SLA. Aja agora para evitar violação.
    </p>
    {_ticket_facts(ticket)}
    <div style="background:#1e2a40;border-radius:8px;padding:14px 16px;margin:16px 0;">
      <p style="margin:0;color:#94a3b8;font-size:13px;">Progresso do SLA</p>
      <div style="background:#0b0f1a;border-radius:4px;height:10px;margin:8px 0;overflow:hidden;">
        <div style="background:#eab308;height:100%;width:{ticket.sla_percentage}%;
                    border-radius:4px;"></div>
      </div>
      <p style="margin:0;color:#eab308;font-weight:700;font-size:14px;">
        {ticket.sla_percentage}% do prazo consumido
      </p>
    </div>"""
    send_email(
        analyst_email,
        f"[⚠ SLA 70%] [{ticket.ticket_number}] {ticket.title}",
        _html_base("Alerta de SLA", body, panel_url, "Ver no Painel"),
    )


def notify_sla_breach(ticket, notified_emails: list[str] | str) -> None:
    """Notifica violação de SLA — analista responsável e gestor."""
    if isinstance(notified_emails, str):
        notified_emails = [notified_emails]
    notified_emails = [e for e in notified_emails if e]
    if not notified_emails:
        return

    panel_url = _system_url("/mockup.html")
    body = f"""
    <h2 style="color:#ef4444;margin:0 0 8px;">🚨 SLA VIOLADO</h2>
    <p style="color:#94a3b8;margin:0 0 16px;">
      O prazo de resolução foi excedido. Escale ou resolva imediatamente.
    </p>
    {_ticket_facts(ticket)}
    <div style="background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3);
                border-radius:8px;padding:14px 16px;margin:16px 0;">
      <p style="margin:0;color:#fca5a5;font-weight:700;">
        ⏰ SLA: {ticket.sla_percentage}% — Chamado em atraso crítico
      </p>
    </div>"""
    send_email(
        notified_emails,
        f"[🚨 SLA VIOLADO] [{ticket.ticket_number}] {ticket.title}",
        _html_base("SLA Violado", body, panel_url, "Resolver Agora"),
    )


def notify_ticket_resolved(ticket, survey_token: str) -> None:
    """Notifica o solicitante da resolução e convida para pesquisa CSAT."""
    user_email = ticket.user.email if ticket.user else None
    user_name  = ticket.user.name  if ticket.user else "Solicitante"
    if not user_email:
        return

    survey_url = _system_url(f"/survey.html?token={survey_token}")
    analyst_name = ticket.analyst.name if ticket.analyst else "Equipe de TI"

    body = f"""
    <h2 style="color:#22c55e;margin:0 0 8px;">Seu chamado foi resolvido! 🎉</h2>
    <p style="color:#94a3b8;margin:0 0 16px;">
      Olá, <strong style="color:#e2e8f0;">{user_name}</strong>!
      O analista <strong style="color:#e2e8f0;">{analyst_name}</strong>
      marcou seu chamado como resolvido.
    </p>
    {_ticket_facts(ticket)}
    <div style="background:#1e2a40;border-radius:8px;padding:20px;margin:16px 0;
                text-align:center;">
      <p style="margin:0 0 12px;color:#e2e8f0;font-size:15px;font-weight:700;">
        O problema foi resolvido para você?
      </p>
      <p style="margin:0 0 16px;color:#94a3b8;font-size:13px;">
        Sua opinião é muito importante para melhorar nosso atendimento.
        Responda em menos de 1 minuto!
      </p>
      <a href="{survey_url}"
         style="display:inline-block;background:#3b82f6;color:#fff;text-decoration:none;
                padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px;">
        ⭐ Avaliar Atendimento
      </a>
      <p style="margin:12px 0 0;font-size:11px;color:#64748b;">
        Se o problema <strong>não foi resolvido</strong>, você poderá reabrir o chamado
        diretamente pela pesquisa.
      </p>
    </div>"""
    send_email(
        user_email,
        f"[RESOLVIDO] [{ticket.ticket_number}] {ticket.title}",
        _html_base("Chamado resolvido", body),
    )


def notify_ticket_reopened(ticket) -> None:
    """Notifica a equipe quando um chamado é reaberto via pesquisa CSAT."""
    if not settings.TEAM_EMAIL:
        return
    panel_url = _system_url("/mockup.html")
    user_name = ticket.user.name if ticket.user else "Solicitante"
    body = f"""
    <h2 style="color:#f97316;margin:0 0 8px;">Chamado reaberto pelo solicitante 🔄</h2>
    <p style="color:#94a3b8;margin:0 0 16px;">
      <strong style="color:#e2e8f0;">{user_name}</strong> indicou na pesquisa de satisfação
      que o problema <strong style="color:#ef4444;">não foi resolvido</strong>.
      O chamado foi reaberto automaticamente.
    </p>
    {_ticket_facts(ticket)}"""
    send_email(
        settings.TEAM_EMAIL,
        f"[REABERTO] [{ticket.ticket_number}] {ticket.title}",
        _html_base("Chamado reaberto", body, panel_url, "Ver no Painel"),
    )
