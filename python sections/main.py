import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

# ── Pasta de exportação (relativa à raiz do projeto) ─────────────────────────

_DIR_SCRIPT = Path(__file__).resolve().parent          # python sections/
_DIR_PROJETO = _DIR_SCRIPT.parent                      # BudgetControl_v1.00/
PASTA_EXPORTACOES = _DIR_PROJETO / "Exportações"
PASTA_EXPORTACOES.mkdir(exist_ok=True)
PASTA_LOGS = _DIR_PROJETO / "Logs"
PASTA_LOGS.mkdir(exist_ok=True)

# ── Logging ──────────────────────────────────────────────────────────────────

def configurar_logging() -> None:
    """Configura handlers de console (INFO) e arquivo (DEBUG)."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    log_file = str(PASTA_LOGS / f"relatorio_{date.today()}.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logging.getLogger(__name__).debug(f"Log de arquivo iniciado em: {log_file}")

# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gerador de PDF de Controle Orçamentário a partir do banco de dados."
    )
    parser.add_argument(
        "--ano",
        type=int,
        help="Sobrescreve o ano padrão definido em config.py (ex: 2026).",
    )
    parser.add_argument(
        "--saida",
        help="Nome do arquivo PDF de saída (ex: relatorio.pdf).",
    )
    return parser.parse_args()

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    configurar_logging()
    log = logging.getLogger(__name__)

    args = parse_args()

    # Importações adiadas para garantir que o logging esteja ativo primeiro
    import config
    from database import buscar_dados
    from report import criar_pdf

    # ── Sobrescrever config via CLI ──
    if args.ano:
        config.ANO_FILTRO = args.ano
        log.info(f"Ano sobrescrito via CLI: {config.ANO_FILTRO}")

    # ── Nome do arquivo dinâmico ──
    hoje_str = date.today().strftime("%Y-%m-%d")
    nome_pdf = args.saida if args.saida else f"Orcamento_{hoje_str}.pdf"
    config.ARQUIVO_PDF = str(PASTA_EXPORTACOES / nome_pdf)

    log.info("=" * 60)
    log.info("  GERADOR DE RELATORIO DE CONTROLE ORCAMENTARIO")
    log.info("=" * 60)
    log.info(f"Ano     : {config.ANO_FILTRO}")
    log.info(f"Saida   : {config.ARQUIVO_PDF}")
    log.info("-" * 60)

    # ── Buscar dados ──
    log.info("Etapa 1/2 -- Consultando o banco de dados...")
    try:
        dados = buscar_dados(config.ANO_FILTRO)
    except Exception as e:
        log.error(f"Falha critica ao acessar o banco: {e}")
        sys.exit(1)

    if not dados:
        log.warning("Nenhum registro encontrado com os filtros aplicados. Abortando.")
        sys.exit(0)

    log.info(f"Dados obtidos: {len(dados)} mes(es) com dados orcamentarios.")

    # ── Gerar PDF ──
    log.info("Etapa 2/2 -- Gerando PDF...")
    criar_pdf(dados)

    log.info("-" * 60)
    log.info("Processo finalizado com sucesso.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()