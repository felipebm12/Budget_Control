"""Registro da família Google Sans (OFL) para PDFs do ReportLab."""
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont

PASTA_FONTES = Path(__file__).resolve().parent / "fonts"
ARQUIVO_REGULAR = PASTA_FONTES / "GoogleSans-Regular.ttf"
ARQUIVO_BOLD = PASTA_FONTES / "GoogleSans-Bold.ttf"

FONT = "GoogleSans"
FONT_BOLD = "GoogleSans-Bold"

_registrado = False


def garantir_fontes() -> tuple[str, str]:
    """Registra Regular e Bold uma vez e devolve os nomes internos do ReportLab."""
    global _registrado
    if _registrado:
        return FONT, FONT_BOLD

    if not ARQUIVO_REGULAR.exists() or not ARQUIVO_BOLD.exists():
        raise FileNotFoundError(
            "Arquivos do Google Sans não encontrados em python sections/fonts/. "
            "São necessários GoogleSans-Regular.ttf e GoogleSans-Bold.ttf."
        )

    pdfmetrics.registerFont(TTFont(FONT, str(ARQUIVO_REGULAR)))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(ARQUIVO_BOLD)))
    registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD)
    _registrado = True
    return FONT, FONT_BOLD
