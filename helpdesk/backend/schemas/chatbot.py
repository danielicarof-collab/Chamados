from pydantic import BaseModel
from typing import Optional, Literal


ChatbotState = Literal[
    "greeting",
    "collecting_description",
    "collecting_impact",
    "collecting_equipment",
    "confirming",
    "done",
    "error",
]

ChatbotChannel = Literal["web", "teams", "email"]


class ChatbotMessageIn(BaseModel):
    session_id: str                        # UUID gerado pelo cliente
    message: str                           # Texto enviado pelo usuário
    channel: ChatbotChannel = "web"
    # Usuário já autenticado no portal — preenchido pelo middleware
    user_email: Optional[str] = None
    user_name: Optional[str] = None


class ChatbotMessageOut(BaseModel):
    session_id: str
    response: str                          # Texto de resposta do bot
    state: ChatbotState
    ticket_number: Optional[str] = None   # Preenchido quando chamado é criado
    quick_replies: Optional[list[str]] = None  # Botões de resposta rápida
