import os
import sys
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

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

# ── Configurações de Filtro do Relatório ─────────────────────────────────────
# Estes valores podem ser sobrescritos via argumentos de linha de comando (CLI).

ANO_FILTRO = 2026

ARQUIVO_PDF = "Orcamento.pdf"  # Sobrescrito em main.py com data dinâmica

# ── Configurações Visuais da Tabela ──────────────────────────────────────────

CABECALHO = [
    "Mês", "Orçado (R$)", "Gasto (R$)", "% Utilizado", "Status"
]

COL_WIDTHS = [60, 100, 100, 90, 180]