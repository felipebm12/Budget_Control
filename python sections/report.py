import logging
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import config

log = logging.getLogger(__name__)

# ── Paleta de cores ───────────────────────────────────────────────────────────
COR_PRIMARIA    = colors.HexColor("#DB7E04")  # Laranja corporativo
COR_PRIMARIA_E  = colors.HexColor("#B5670A")  # Laranja escuro
COR_ZEBRA       = colors.HexColor("#FFF8EE")  # Bege claro
COR_GRADE       = colors.HexColor("#E2E8F0")
COR_TEXTO       = colors.HexColor("#1A1A1A")
COR_TEXTO_MEDIO = colors.HexColor("#444444")
COR_ALERTA      = colors.HexColor("#FEE2E2")  # Vermelho claro (fundo de alerta)
COR_PERTO       = colors.HexColor("#FEF3C7")  # Amarelo claro (fundo de perto do orçamento)
COR_OK          = colors.HexColor("#DCFCE7")  # Verde claro (fundo de OK)
COR_TOTAL_BG    = colors.HexColor("#FEF3E2")  # Fundo para linha de totais


def _estilos() -> dict:
    """Cria e retorna todos os ParagraphStyles usados no PDF."""
    base = getSampleStyleSheet()

    return {
        "titulo": ParagraphStyle(
            "Titulo", parent=base["Heading1"],
            fontSize=15, textColor=COR_TEXTO,
            spaceAfter=3, alignment=1, fontName="Helvetica-Bold",
        ),
        "subtitulo": ParagraphStyle(
            "Subtitulo", parent=base["Normal"],
            fontSize=8.5, textColor=COR_TEXTO_MEDIO,
            spaceAfter=3, alignment=1,
        ),
        "data_geracao": ParagraphStyle(
            "DataGeracao", parent=base["Normal"],
            fontSize=7, textColor=COR_TEXTO_MEDIO,
            spaceAfter=12, alignment=1,
        ),
        "celula": ParagraphStyle(
            "Celula", parent=base["Normal"],
            fontSize=7.5, leading=9, textColor=COR_TEXTO,
        ),
        "celula_centro": ParagraphStyle(
            "CelulaCentro", parent=base["Normal"],
            fontSize=7.5, leading=9, textColor=COR_TEXTO, alignment=1,
        ),
        "celula_bold": ParagraphStyle(
            "CelulaBold", parent=base["Normal"],
            fontSize=7.5, leading=9, textColor=COR_TEXTO, fontName="Helvetica-Bold",
        ),
        "celula_alerta": ParagraphStyle(
            "CelulaAlerta", parent=base["Normal"],
            fontSize=8, leading=10,
            textColor=colors.HexColor("#991B1B"), fontName="Helvetica-Bold",
        ),
        "celula_perto": ParagraphStyle(
            "CelulaPerto", parent=base["Normal"],
            fontSize=8, leading=10,
            textColor=colors.HexColor("#B45309"), fontName="Helvetica-Bold",
        ),
        "celula_ok": ParagraphStyle(
            "CelulaOK", parent=base["Normal"],
            fontSize=8, leading=10,
            textColor=colors.HexColor("#166534"), fontName="Helvetica-Bold",
        ),
        "cabecalho": ParagraphStyle(
            "Cabecalho", parent=base["Normal"],
            fontSize=8, leading=10,
            textColor=colors.white, fontName="Helvetica-Bold",
        ),
        "cabecalho_centro": ParagraphStyle(
            "CabecalhoCentro", parent=base["Normal"],
            fontSize=8, leading=10,
            textColor=colors.white, fontName="Helvetica-Bold", alignment=1,
        ),
    }


def gerar_pdf_resumo(dados: list, periodo_texto: str = "Geral", arquivo_destino: str = None) -> str:
    """
    Gera o PDF com a visão resumida mensal de orçamentos e gastos no intervalo de datas.
    dados: [ [mes_nome, orcado_fmt, gasto_fmt, pct_fmt, status], ... ]
    """
    caminho = arquivo_destino or config.ARQUIVO_PDF
    doc = SimpleDocTemplate(
        caminho,
        pagesize=landscape(letter),
        rightMargin=25, leftMargin=25,
        topMargin=25,   bottomMargin=25,
    )

    estilos = _estilos()
    s = estilos
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    story = []

    story.append(Paragraph("Controle Orçamentário Empresarial — Visão Resumida", s["titulo"]))
    story.append(Paragraph(f"<b>Período:</b> {periodo_texto}", s["subtitulo"]))
    story.append(Paragraph(f"Gerado em: {agora} &nbsp;|&nbsp; Total de períodos: <b>{len(dados)}</b>", s["data_geracao"]))

    if not dados:
        story.append(Spacer(1, 20))
        story.append(Paragraph("Nenhum dado encontrado para o período selecionado.", s["celula"]))
        doc.build(story)
        return caminho

    cabecalhos = ["Mês / Período", "Orçado (R$)", "Gasto (R$)", "% Utilizado", "Status"]
    table_data = [[
        Paragraph(cabecalhos[0], s["cabecalho"]),
        Paragraph(cabecalhos[1], s["cabecalho_centro"]),
        Paragraph(cabecalhos[2], s["cabecalho_centro"]),
        Paragraph(cabecalhos[3], s["cabecalho_centro"]),
        Paragraph(cabecalhos[4], s["cabecalho"]),
    ]]

    for linha in dados:
        status_texto = str(linha[4])
        st_up = status_texto.upper()
        if "ACIMA" in st_up or "ALERTA" in st_up:
            estilo_status = s["celula_alerta"]
        elif "PERTO" in st_up:
            estilo_status = s["celula_perto"]
        else:
            estilo_status = s["celula_ok"]

        table_data.append([
            Paragraph(str(linha[0]), s["celula_bold"]),
            Paragraph(str(linha[1]), s["celula_centro"]),
            Paragraph(str(linha[2]), s["celula_centro"]),
            Paragraph(str(linha[3]), s["celula_centro"]),
            Paragraph(status_texto, estilo_status),
        ])

    comandos = [
        ("BACKGROUND",    (0, 0), (-1, 0),  COR_PRIMARIA),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.5, COR_GRADE),
    ]

    for i, linha in enumerate(dados, start=1):
        st_up = str(linha[4]).upper()
        if "ACIMA" in st_up or "ALERTA" in st_up:
            comandos.append(("BACKGROUND", (0, i), (-1, i), COR_ALERTA))
        elif "PERTO" in st_up:
            comandos.append(("BACKGROUND", (0, i), (-1, i), COR_PERTO))
        elif i % 2 == 0:
            comandos.append(("BACKGROUND", (0, i), (-1, i), COR_ZEBRA))

    tabela = Table(table_data, colWidths=[120, 130, 130, 100, 190])
    tabela.setStyle(TableStyle(comandos))

    story.append(Spacer(1, 6))
    story.append(tabela)
    doc.build(story)
    log.info(f"PDF Resumo '{caminho}' gerado com sucesso.")
    return caminho


def gerar_pdf_detalhado(despesas: list, periodo_texto: str = "Geral", total_gasto: str = "R$ 0,00", arquivo_destino: str = None) -> str:
    """
    Gera o PDF com a visão detalhada de despesas individuais da empresa,
    discriminando Setor, Fornecedor, Categoria e Destino.
    """
    caminho = arquivo_destino or config.ARQUIVO_PDF
    doc = SimpleDocTemplate(
        caminho,
        pagesize=landscape(letter),
        rightMargin=20, leftMargin=20,
        topMargin=22,   bottomMargin=22,
    )

    estilos = _estilos()
    s = estilos
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    story = []

    story.append(Paragraph("Controle de Despesas Empresarial — Relatório Detalhado", s["titulo"]))
    story.append(Paragraph(
        f"<b>Período:</b> {periodo_texto} &nbsp;|&nbsp; <b>Total Gasto:</b> {total_gasto}",
        s["subtitulo"]
    ))
    story.append(Paragraph(
        f"Gerado em: {agora} &nbsp;|&nbsp; Total de lançamentos: <b>{len(despesas)}</b>",
        s["data_geracao"]
    ))

    if not despesas:
        story.append(Spacer(1, 20))
        story.append(Paragraph("Nenhuma despesa encontrada para o período selecionado.", s["celula"]))
        doc.build(story)
        return caminho

    cabecalhos = ["Data", "Descrição", "Setor", "Fornecedor", "Categoria", "Destino", "Valor (R$)"]
    table_data = [[
        Paragraph(cabecalhos[0], s["cabecalho_centro"]),
        Paragraph(cabecalhos[1], s["cabecalho"]),
        Paragraph(cabecalhos[2], s["cabecalho"]),
        Paragraph(cabecalhos[3], s["cabecalho"]),
        Paragraph(cabecalhos[4], s["cabecalho"]),
        Paragraph(cabecalhos[5], s["cabecalho"]),
        Paragraph(cabecalhos[6], s["cabecalho_centro"]),
    ]]

    for d in despesas:
        table_data.append([
            Paragraph(str(d.get("data", "")), s["celula_centro"]),
            Paragraph(str(d.get("descricao", "")), s["celula"]),
            Paragraph(str(d.get("setor", "-")), s["celula"]),
            Paragraph(str(d.get("fornecedor", "-")), s["celula"]),
            Paragraph(str(d.get("categoria", "-")), s["celula"]),
            Paragraph(str(d.get("destino", "-")), s["celula"]),
            Paragraph(str(d.get("valor_fmt", "")), s["celula_bold"]),
        ])

    # Linha de total
    table_data.append([
        Paragraph("TOTAL", s["celula_bold"]),
        Paragraph(f"{len(despesas)} despesa(s)", s["celula_bold"]),
        Paragraph("", s["celula"]),
        Paragraph("", s["celula"]),
        Paragraph("", s["celula"]),
        Paragraph("", s["celula"]),
        Paragraph(total_gasto, s["celula_bold"]),
    ])

    comandos = [
        ("BACKGROUND",    (0, 0), (-1, 0),  COR_PRIMARIA),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.5, COR_GRADE),
        ("BACKGROUND",    (0, -1), (-1, -1), COR_TOTAL_BG),
        ("LINEABOVE",     (0, -1), (-1, -1), 1.2, COR_PRIMARIA_E),
    ]

    for i in range(1, len(despesas) + 1):
        if i % 2 == 0:
            comandos.append(("BACKGROUND", (0, i), (-1, i), COR_ZEBRA))

    tabela = Table(table_data, colWidths=[58, 175, 95, 110, 95, 95, 84])
    tabela.setStyle(TableStyle(comandos))

    story.append(Spacer(1, 4))
    story.append(tabela)
    doc.build(story)
    log.info(f"PDF Detalhado '{caminho}' gerado com sucesso.")
    return caminho


def criar_pdf(dados: list) -> None:
    """Compatibilidade reversa com o main.py antigo."""
    gerar_pdf_resumo(dados, periodo_texto=f"Ano {config.ANO_FILTRO}")