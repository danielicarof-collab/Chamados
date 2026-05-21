import json
import logging
from anthropic import Anthropic
from config import settings

logger = logging.getLogger(__name__)

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """Você é um especialista em TI que classifica chamados de suporte.
Analise o chamado e retorne APENAS um JSON válido, sem texto adicional:
{
  "priority": "Crítica|Alta|Média|Baixa",
  "level": "N1|N2|N3",
  "justification": "máximo 25 palavras explicando a decisão",
  "tags": ["tag1", "tag2"],
  "confidence": 0.0
}

Regras:
- Crítica: sistema parado, negócio parado, servidor/banco de dados instável
- Alta: impacto alto em processo essencial, sem alternativa
- Média: impacto moderado, existe workaround
- Baixa: solicitação de melhoria, sem impacto imediato
- N3: banco de dados, servidor, infraestrutura crítica
- N2: rede, VPN, ERP, Active Directory, sistemas complexos
- N1: hardware simples, impressora, software desktop, e-mail"""

_FALLBACK = {
    "priority": "Média",
    "level": "N1",
    "justification": "Análise automática indisponível",
    "tags": [],
    "confidence": 0.0,
}


async def analyze_ticket(
    title: str,
    description: str,
    category: str = "",
    impact: str = "",
) -> dict:
    prompt = f"Título: {title}\nDescrição: {description}"
    if category:
        prompt += f"\nCategoria: {category}"
    if impact:
        prompt += f"\nImpacto informado: {impact}"

    try:
        response = _get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text.strip())
    except json.JSONDecodeError as e:
        logger.error("IA retornou JSON inválido: %s", e)
        return _FALLBACK.copy()
    except Exception as e:
        logger.error("Erro na análise da IA: %s", e)
        return _FALLBACK.copy()


async def suggest_action(ticket) -> dict:
    prompt = (
        f"Chamado #{ticket.ticket_number}\n"
        f"Título: {ticket.title}\n"
        f"Descrição: {ticket.description}\n"
        f"Status: {ticket.status}\n"
        f"Prioridade: {ticket.priority}\n"
        f"Nível: {ticket.level}\n"
        f"SLA consumido: {ticket.sla_percentage}%"
    )
    try:
        response = _get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=(
                "Você é um especialista em suporte de TI. "
                "Sugira a próxima ação para resolver este chamado. "
                "Responda em português, de forma objetiva, máximo 50 palavras."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        return {"suggestion": response.content[0].text.strip()}
    except Exception as e:
        logger.error("Erro na sugestão da IA: %s", e)
        return {"suggestion": "Não foi possível gerar sugestão no momento."}
