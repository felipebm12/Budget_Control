import hashlib
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (CWD ou diretório de config.py)
load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env")

# ── Validação de variáveis obrigatórias ──────────────────────────────────────

def _obrigatorio(chave: str) -> str:
    """Retorna o valor da variável de ambiente ou encerra com mensagem clara."""
    valor = os.getenv(chave)
    if not valor:
        print(f"[ERRO FATAL] Variável de ambiente obrigatória não encontrada: '{chave}'")
        print("  → Verifique se o arquivo .env existe e está preenchido corretamente.")
        sys.exit(1)
    return valor

# ── Credenciais do Banco de Dados (PostgreSQL / Supabase) ────────────────────

DB_HOST     = _obrigatorio("DB_HOST")       # Ex: db.xxxxx.supabase.co
DB_PORT     = os.getenv("DB_PORT", "5432")   # Padrão PostgreSQL
DB_NAME     = _obrigatorio("DB_NAME")       # Ex: postgres
DB_USER     = _obrigatorio("DB_USER")       # Ex: postgres.xxxxx
DB_PASSWORD = _obrigatorio("DB_PASSWORD")

# ── Configurações de Segurança e Servidor Flask ──────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY") or hashlib.sha256(
    f"budgetcontrol-v1:{DB_HOST}:{DB_USER}:{DB_PASSWORD}".encode("utf-8")
).hexdigest()

FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes")
FLASK_PORT  = int(os.getenv("FLASK_PORT", "5000"))

# ── Configurações de E-mail (SMTP) e Recuperação de Senha ────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", "").strip() or SMTP_USER or "no-reply@budgetcontrol.local"
SMTP_USE_TLS  = os.getenv("SMTP_USE_TLS", "1").strip().lower() in ("1", "true", "yes")
SMTP_USE_SSL  = os.getenv("SMTP_USE_SSL", "0").strip().lower() in ("1", "true", "yes")
APP_BASE_URL  = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
RESET_TOKEN_EXPIRA_MINUTOS = int(os.getenv("RESET_TOKEN_EXPIRA_MINUTOS", "30"))


# ── Configurações de Filtro do Relatório ─────────────────────────────────────
# Estes valores podem ser sobrescritos via argumentos de linha de comando (CLI).

ANO_FILTRO = 2026

ARQUIVO_PDF = "Orcamento.pdf"  # Sobrescrito em main.py com data dinâmica

# ── Configurações Visuais da Tabela ──────────────────────────────────────────

CABECALHO = [
    "Mês", "Orçado (R$)", "Gasto (R$)", "% Utilizado", "Status"
]

COL_WIDTHS = [60, 100, 100, 90, 180]