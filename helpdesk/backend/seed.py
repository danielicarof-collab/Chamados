"""
Dados iniciais: SLA, categorias, departamentos, analistas, usuários e chamados de exemplo.
Execução: python seed.py (a partir do diretório backend/)
"""
import sys
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext

from database import SessionLocal, engine
from models import (
    Department, User, Analyst, Category,
    SLARule, Ticket, TicketTimeline, TicketSurvey, ChatbotSession,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed():
    # Cria todas as tabelas (equivalente ao alembic upgrade head em dev)
    from database import Base
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_sla(db)
        _seed_departments(db)
        _seed_categories(db)
        _seed_analysts(db)
        _seed_users(db)
        _seed_tickets(db)
        db.commit()
        print("✅ Seed concluído com sucesso!")
    except Exception as e:
        db.rollback()
        print(f"❌ Erro no seed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def _seed_sla(db):
    if db.query(SLARule).count():
        print("  SLA rules já existem, pulando...")
        return
    # Referência: ITIL 4 + ISO/IEC 20000 — metas típicas de mercado
    rules = [
        # Crítica (P1): sistema/negócio parado — resposta em 1h, resolução em 4h
        SLARule(priority="Crítica", response_hours=1,  resolution_hours=4,  escalation_n1_hours=1,  escalation_n2_hours=2,  color="#ef4444"),
        # Alta (P2): impacto alto sem workaround — resposta em 2h, resolução em 8h
        SLARule(priority="Alta",    response_hours=2,  resolution_hours=8,  escalation_n1_hours=4,  escalation_n2_hours=7,  color="#f97316"),
        # Média (P3): impacto moderado com workaround — resposta em 4h, resolução em 24h
        SLARule(priority="Média",   response_hours=4,  resolution_hours=24, escalation_n1_hours=20, escalation_n2_hours=23, color="#eab308"),
        # Baixa (P4): melhoria/sem urgência — resposta em 8h, resolução em 72h
        SLARule(priority="Baixa",   response_hours=8,  resolution_hours=72, escalation_n1_hours=68, escalation_n2_hours=71, color="#22c55e"),
    ]
    db.add_all(rules)
    db.flush()
    print("  SLA rules criadas (ITIL 4)")


def _seed_departments(db):
    if db.query(Department).count():
        print("  Departamentos já existem, pulando...")
        return
    depts = [
        Department(name="TI",          description="Tecnologia da Informação"),
        Department(name="Financeiro",   description="Departamento Financeiro"),
        Department(name="RH",           description="Recursos Humanos"),
        Department(name="Operações",    description="Departamento de Operações"),
        Department(name="Comercial",    description="Departamento Comercial"),
        Department(name="Jurídico",     description="Departamento Jurídico"),
    ]
    db.add_all(depts)
    db.flush()
    print("  Departamentos criados")


def _seed_categories(db):
    if db.query(Category).count():
        print("  Categorias já existem, pulando...")
        return
    categories = [
        Category(name="Hardware",         default_sla="Média",   default_level="N1"),
        Category(name="Software",         default_sla="Média",   default_level="N1"),
        Category(name="Rede / VPN",       default_sla="Alta",    default_level="N2"),
        Category(name="Acesso / Login",   default_sla="Alta",    default_level="N2"),
        Category(name="E-mail",           default_sla="Média",   default_level="N1"),
        Category(name="Impressora",       default_sla="Baixa",   default_level="N1"),
        Category(name="Banco de Dados",   default_sla="Crítica", default_level="N3"),
        Category(name="Servidor",         default_sla="Crítica", default_level="N3"),
        Category(name="Microsoft 365",    default_sla="Média",   default_level="N1"),
        Category(name="ERP / SAP",        default_sla="Alta",    default_level="N2"),
        Category(name="Outros",           default_sla="Baixa",   default_level="N1"),
    ]
    db.add_all(categories)
    db.flush()
    print("  Categorias criadas")


def _seed_analysts(db):
    if db.query(Analyst).count():
        print("  Analistas já existem, pulando...")
        return

    # Hierarquia: N1 (suporte básico) → N2 (suporte avançado) → N3 (especialista)
    # Roles:  analyst < coordinator < manager < admin
    analysts = [
        Analyst(
            name="Administrador",
            email="admin@empresa.com",
            password=pwd_context.hash("Admin@123"),
            level="N3",
            role="admin",
        ),
        Analyst(
            name="João Silva",
            email="joao@empresa.com",
            password=pwd_context.hash("Senha@123"),
            level="N1",
            role="analyst",
        ),
        Analyst(
            name="Maria Santos",
            email="maria@empresa.com",
            password=pwd_context.hash("Senha@123"),
            level="N2",
            role="analyst",
        ),
        Analyst(
            name="Carlos Oliveira",
            email="carlos.ti@empresa.com",
            password=pwd_context.hash("Senha@123"),
            level="N2",
            role="coordinator",   # coordenador da equipe N1/N2
        ),
        Analyst(
            name="Pedro Costa",
            email="pedro@empresa.com",
            password=pwd_context.hash("Senha@123"),
            level="N3",
            role="manager",
        ),
    ]
    db.add_all(analysts)
    db.flush()
    print("  Analistas criados (incluindo coordenador)")
    print("  Login admin: admin@empresa.com / Admin@123")


def _seed_users(db):
    if db.query(User).count():
        print("  Usuários já existem, pulando...")
        return

    dept_ti  = db.query(Department).filter(Department.name == "TI").first()
    dept_fin = db.query(Department).filter(Department.name == "Financeiro").first()
    dept_rh  = db.query(Department).filter(Department.name == "RH").first()
    dept_op  = db.query(Department).filter(Department.name == "Operações").first()

    # Usuários com senha para acessar o portal self-service
    users = [
        User(
            name="Ana Lima",
            email="ana@empresa.com",
            phone="11999001",
            department_id=dept_fin.id if dept_fin else None,
            password=pwd_context.hash("Senha@123"),
        ),
        User(
            name="Fernando Rocha",
            email="fernanda@empresa.com",
            phone="11999003",
            department_id=dept_ti.id if dept_ti else None,
            password=pwd_context.hash("Senha@123"),
        ),
        User(
            name="Rafael Mendes",
            email="rafael@empresa.com",
            phone="11999004",
            department_id=dept_rh.id if dept_rh else None,
            password=pwd_context.hash("Senha@123"),
        ),
        User(
            name="Beatriz Souza",
            email="beatriz@empresa.com",
            phone="11999005",
            department_id=dept_op.id if dept_op else None,
            password=pwd_context.hash("Senha@123"),
        ),
    ]
    db.add_all(users)
    db.flush()
    print("  Usuários criados com senha de portal (Senha@123)")


def _seed_tickets(db):
    if db.query(Ticket).count():
        print("  Chamados já existem, pulando...")
        return

    user      = db.query(User).first()
    analyst_n1 = db.query(Analyst).filter(Analyst.level == "N1", Analyst.role == "analyst").first()
    analyst_n2 = db.query(Analyst).filter(Analyst.level == "N2", Analyst.role == "analyst").first()
    analyst_n3 = db.query(Analyst).filter(Analyst.level == "N3").first()
    cat_rede  = db.query(Category).filter(Category.name == "Rede / VPN").first()
    cat_hw    = db.query(Category).filter(Category.name == "Hardware").first()
    cat_sw    = db.query(Category).filter(Category.name == "Software").first()
    cat_srv   = db.query(Category).filter(Category.name == "Servidor").first()

    now      = datetime.now(timezone.utc)
    dept_ti  = db.query(Department).filter(Department.name == "TI").first()

    tickets_data = [
        Ticket(
            ticket_number="TI-0001",
            title="VPN não conecta após atualização do Windows",
            description="Após atualização do Windows 11 a VPN corporativa parou de funcionar. Não consigo acessar sistemas internos.",
            category_id=cat_rede.id if cat_rede else None,
            priority="Alta",
            priority_source="ai",
            status="Em andamento",
            level="N2",
            impact="Alto",
            user_id=user.id if user else None,
            analyst_id=analyst_n2.id if analyst_n2 else None,
            department_id=dept_ti.id if dept_ti else None,
            ai_analysis={"priority": "Alta", "level": "N2", "justification": "VPN corporativa fora afeta acesso remoto a sistemas essenciais", "tags": ["vpn", "rede", "windows"], "confidence": 0.91},
            sla_deadline=now + timedelta(hours=6),
            sla_response_deadline=now + timedelta(hours=2),
            sla_responded_at=now - timedelta(hours=1),
            sla_percentage=42,
        ),
        Ticket(
            ticket_number="TI-0002",
            title="Monitor do computador sem sinal",
            description="O monitor do meu computador não está recebendo sinal. Já verifiquei o cabo e está conectado corretamente.",
            category_id=cat_hw.id if cat_hw else None,
            priority="Baixa",
            priority_source="ai",
            status="Aberto",
            level="N1",
            impact="Baixo",
            user_id=user.id if user else None,
            analyst_id=analyst_n1.id if analyst_n1 else None,
            department_id=dept_ti.id if dept_ti else None,
            ai_analysis={"priority": "Baixa", "level": "N1", "justification": "Problema de hardware simples, sem impacto em processos críticos", "tags": ["monitor", "hardware"], "confidence": 0.87},
            sla_deadline=now + timedelta(hours=60),
            sla_response_deadline=now + timedelta(hours=20),
            sla_percentage=15,
        ),
        Ticket(
            ticket_number="TI-0003",
            title="Excel travando ao abrir planilhas grandes",
            description="O Microsoft Excel trava e fecha inesperadamente ao tentar abrir planilhas com mais de 10.000 linhas. Acontece em todos os arquivos xlsx.",
            category_id=cat_sw.id if cat_sw else None,
            priority="Média",
            priority_source="manual",
            status="Aberto",
            level="N1",
            impact="Médio",
            user_id=user.id if user else None,
            department_id=dept_ti.id if dept_ti else None,
            ai_analysis={"priority": "Alta", "level": "N1", "justification": "Problema afeta produtividade com planilhas essenciais para o negócio", "tags": ["excel", "office", "software"], "confidence": 0.78},
            sla_deadline=now + timedelta(hours=18),
            sla_response_deadline=now + timedelta(hours=6),
            sla_percentage=28,
        ),
        Ticket(
            ticket_number="TI-0004",
            title="Servidor de arquivos fora do ar",
            description="O servidor de arquivos compartilhado (\\\\fileserver) está inacessível desde as 08h. Toda a equipe está sem acesso aos arquivos de trabalho.",
            category_id=cat_srv.id if cat_srv else None,
            priority="Crítica",
            priority_source="ai",
            status="Em andamento",
            level="N3",
            impact="Alto",
            user_id=user.id if user else None,
            analyst_id=analyst_n3.id if analyst_n3 else None,
            department_id=dept_ti.id if dept_ti else None,
            ai_analysis={"priority": "Crítica", "level": "N3", "justification": "Servidor de arquivos indisponível paralisa a operação de toda a empresa", "tags": ["servidor", "fileserver", "infraestrutura"], "confidence": 0.97},
            sla_deadline=now + timedelta(hours=2),
            sla_response_deadline=now + timedelta(minutes=30),
            sla_responded_at=now - timedelta(minutes=10),
            sla_percentage=75,
        ),
    ]

    db.add_all(tickets_data)
    db.flush()

    for ticket in tickets_data:
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            type="open",
            action=f"Chamado {ticket.ticket_number} aberto",
            by_analyst=analyst_n1.id if analyst_n1 else None,
            by_name=analyst_n1.name if analyst_n1 else "Admin",
            icon="ticket",
            icon_color="blue",
        ))
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            type="ai",
            action=f"Prioridade '{ticket.priority}' definida pela IA",
            note=ticket.ai_analysis.get("justification", "") if ticket.ai_analysis else "",
            by_name="IA",
            icon="robot",
            icon_color="purple",
        ))

    print("  Chamados de exemplo criados")


if __name__ == "__main__":
    seed()
