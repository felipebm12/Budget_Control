"""Gera a documentação oficial do BudgetControl em PDF e DOCX."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_DIR_PYTHON = Path(__file__).resolve().parent.parent / "python sections"
if str(_DIR_PYTHON) not in sys.path:
    sys.path.insert(0, str(_DIR_PYTHON))
from pdf_fonts import FONT, FONT_BOLD, garantir_fontes

FONTE_DOCX = "Google Sans"

SAIDA_DIR = Path(__file__).resolve().parent
VERSAO = "1.5"
DATA_DOC = date.today().strftime("%d/%m/%Y")

COR_CINZA = colors.HexColor("#A1A1A1")
COR_CABECALHO = colors.HexColor("#1A1A1A")
COR_ZEBRA = colors.HexColor("#FFF8EE")
COR_BORDA = colors.HexColor("#E2E8F0")
COR_TEXTO = colors.HexColor("#1A1A1A")

ENDPOINTS = [
    ["GET", "/", "Dashboard web principal."],
    ["GET", "/api/dados", "Consolidado mês a mês (orçado, gasto, saldo, %)."],
    ["GET", "/api/despesas", "Lançamentos filtrados por período e entidades."],
    ["POST", "/api/despesas", "Cadastro de despesa empresarial."],
    ["PUT", "/api/despesas/<id>", "Atualização de lançamento existente."],
    ["DELETE", "/api/despesas/<id>", "Exclusão individual de despesa."],
    ["DELETE/POST", "/api/despesas/limpar-todas", "Remove todas as despesas."],
    ["GET/POST", "/api/setores", "Lista ou cadastra setores."],
    ["PUT/DELETE", "/api/setores/<id>", "Edita ou exclui setor (bloqueia se houver vínculo)."],
    ["GET/POST", "/api/fornecedores", "Lista ou cadastra fornecedores."],
    ["PUT/DELETE", "/api/fornecedores/<id>", "Edita ou exclui fornecedor (bloqueia se houver vínculo)."],
    ["GET/POST", "/api/categorias", "Lista ou cadastra categorias (rubricas). Alias: /api/rubricas."],
    ["PUT/DELETE", "/api/categorias/<id>", "Edita ou exclui categoria (bloqueia se houver vínculo)."],
    ["GET", "/api/orcamentos-setor", "Grade de 12 meses de um setor (query: setor_id, ano)."],
    ["POST", "/api/orcamentos-setor", "Salva teto mensal; aplicar_todos replica os 12 meses."],
    ["GET", "/api/orcamentos-setor/resumo", "Comparativo anual orçado × gasto por setor."],
    ["GET", "/api/exportar-pdf", "Gera PDF resumido ou detalhado com os filtros ativos."],
]


def _styles_pdf():
    garantir_fontes()
    base = getSampleStyleSheet()
    return {
        "capa_titulo": ParagraphStyle(
            "CapaTitulo", parent=base["Title"], fontName=FONT_BOLD,
            fontSize=22, textColor=COR_CABECALHO, alignment=TA_CENTER, spaceAfter=8,
        ),
        "capa_sub": ParagraphStyle(
            "CapaSub", parent=base["Normal"], fontName=FONT,
            fontSize=12, textColor=COR_CINZA, alignment=TA_CENTER, spaceAfter=6,
        ),
        "capa_meta": ParagraphStyle(
            "CapaMeta", parent=base["Normal"], fontName=FONT, fontSize=9, textColor=colors.HexColor("#555555"),
            alignment=TA_CENTER, leading=13,
        ),
        "h1": ParagraphStyle(
            "H1Doc", parent=base["Heading1"], fontName=FONT_BOLD,
            fontSize=14, textColor=COR_CINZA, spaceBefore=14, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2Doc", parent=base["Heading2"], fontName=FONT_BOLD,
            fontSize=11.5, textColor=COR_CABECALHO, spaceBefore=10, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "BodyDoc", parent=base["Normal"], fontName=FONT,
            fontSize=9.5, leading=13, alignment=TA_JUSTIFY, textColor=COR_TEXTO, spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "BulletDoc", parent=base["Normal"], fontName=FONT,
            fontSize=9.5, leading=13, textColor=COR_TEXTO, leftIndent=8,
        ),
        "cell": ParagraphStyle(
            "CellDoc", parent=base["Normal"], fontName=FONT,
            fontSize=7.5, leading=10, textColor=COR_TEXTO,
        ),
        "cell_h": ParagraphStyle(
            "CellHDoc", parent=base["Normal"], fontName=FONT_BOLD,
            fontSize=8, leading=10, textColor=colors.white,
        ),
        "code": ParagraphStyle(
            "CodeDoc", parent=base["Code"], fontName=FONT,
            fontSize=8, leading=11, textColor=COR_TEXTO, backColor=colors.HexColor("#F8F8F8"),
            leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "FooterDoc", parent=base["Normal"], fontName=FONT, fontSize=8, textColor=colors.HexColor("#666666"),
            alignment=TA_CENTER,
        ),
    }


def _tabela(headers, rows, col_widths, styles):
    data = [[Paragraph(h, styles["cell_h"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), styles["cell"]) for c in row])
    table = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), COR_CABECALHO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, COR_BORDA),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), COR_ZEBRA))
    table.setStyle(TableStyle(cmds))
    return table


def _bullets(itens, styles):
    return ListFlowable(
        [ListItem(Paragraph(item, styles["bullet"]), leftIndent=12, bulletColor=COR_CINZA) for item in itens],
        bulletType="bullet",
        start="•",
        leftIndent=18,
        spaceBefore=2,
        spaceAfter=8,
    )


def _header_footer(canvas, doc):
    garantir_fontes()
    canvas.saveState()
    canvas.setFillColor(COR_CINZA)
    canvas.rect(0, A4[1] - 18, A4[0], 18, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT, 8)
    canvas.drawString(2 * cm, A4[1] - 13, "BudgetControl — Documentação do Sistema")
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 13, f"v{VERSAO}")
    canvas.setFillColor(colors.HexColor("#EEEEEE"))
    canvas.rect(0, 0, A4[0], 16, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.setFont(FONT, 8)
    canvas.drawString(2 * cm, 6, f"Gerado em {DATA_DOC}")
    canvas.drawRightString(A4[0] - 2 * cm, 6, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf(caminho: Path) -> None:
    styles = _styles_pdf()
    doc = SimpleDocTemplate(
        str(caminho),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.4 * cm,
        title="BudgetControl — Documentação do Sistema",
        author="BudgetControl",
    )
    story = []

    story.append(Spacer(1, 4.2 * cm))
    story.append(Paragraph("BudgetControl", styles["capa_titulo"]))
    story.append(Paragraph("Sistema de Controle Orçamentário e Gestão de Despesas Empresariais", styles["capa_sub"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"Documentação funcional e técnica<br/>Versão {VERSAO} &nbsp;|&nbsp; {DATA_DOC}<br/>Python · Flask · PostgreSQL / Supabase",
        styles["capa_meta"],
    ))
    story.append(PageBreak())

    story.append(Paragraph("1. Visão geral", styles["h1"]))
    story.append(Paragraph(
        "O BudgetControl é uma aplicação corporativa para cadastrar, classificar e acompanhar despesas "
        "em relação a tetos orçamentários definidos por setor, ano e mês. O usuário opera um dashboard web "
        "em Flask; os dados ficam no PostgreSQL (Supabase). Relatórios em PDF são gerados com ReportLab. "
        "Há ainda um script de linha de comando para emitir o consolidado anual sem abrir o navegador.",
        styles["body"],
    ))
    story.append(Paragraph("Objetivos do sistema", styles["h2"]))
    story.append(_bullets([
        "Registrar despesas com descrição, valor, data, setor, fornecedor, categoria e destino.",
        "Definir orçamento mensal por setor e comparar com o gasto real.",
        "Filtrar o dashboard por intervalo de datas, setor, fornecedor e categoria.",
        "Sinalizar execução (dentro, perto ou acima do orçamento) com limite padrão de 80%.",
        "Exportar PDF na visão resumida (mês a mês) ou detalhada (lançamentos).",
        "Manter cadastros mestres de setores, fornecedores e categorias, com proteção contra exclusão quando houver lançamentos vinculados.",
    ], styles))

    story.append(Paragraph("2. Público e formas de uso", styles["h1"]))
    story.append(Paragraph(
        "O público-alvo são gestores financeiros, controladoria e responsáveis de centro de custo que "
        "precisam acompanhar execução orçamentária. Existem dois modos de operação:",
        styles["body"],
    ))
    story.append(_bullets([
        "<b>Dashboard web</b> — interface única em <font face='GoogleSans'>http://127.0.0.1:5000</font>, com menu de ações, filtros, KPIs, tabelas e modais de cadastro.",
        "<b>CLI</b> — arquivo <font face='GoogleSans'>main.py</font>: consulta o consolidado do ano (padrão 2026 em config.py, sobrescrevível com <font face='GoogleSans'>--ano</font>) e grava PDF em <font face='GoogleSans'>Exportações/</font>.",
    ], styles))

    story.append(Paragraph("3. Arquitetura", styles["h1"]))
    story.append(Paragraph(
        "A aplicação segue uma arquitetura em camadas, sem framework de frontend: HTML, CSS e JavaScript no template, "
        "API REST no Flask e SQL via psycopg2.",
        styles["body"],
    ))
    story.append(_tabela(
        ["Camada", "Arquivo / pasta", "Responsabilidade"],
        [
            ["Apresentação", "templates/index.html + static/css/style.css", "Dashboard, filtros, modais, SweetAlert2."],
            ["API web", "app.py", "Rotas Flask, validação de payload, download de PDF."],
            ["Domínio / persistência", "database.py", "CRUD, consolidados, formatação de moeda e status."],
            ["Relatórios", "report.py", "PDFs resumido e detalhado (ReportLab)."],
            ["Configuração", "config.py + .env", "Credenciais PostgreSQL e parâmetros do CLI."],
            ["CLI", "main.py", "Geração de relatório anual via terminal."],
            ["Banco", "DB scripts/", "Migrações, índices, auditoria e rollback."],
            ["Saídas", "Exportações/ e Logs/", "PDFs gerados e arquivos de log."],
        ],
        [3.2 * cm, 5.4 * cm, 8.4 * cm],
        styles,
    ))

    story.append(Paragraph("4. Stack tecnológica", styles["h1"]))
    story.append(_tabela(
        ["Item", "Tecnologia"],
        [
            ["Linguagem", "Python 3.10 ou superior"],
            ["Servidor web", "Flask 3+"],
            ["Banco de dados", "PostgreSQL (Supabase), conexão SSL obrigatória"],
            ["Driver", "psycopg2-binary"],
            ["Ambiente", "python-dotenv (.env)"],
            ["PDF", "ReportLab 4+"],
            ["Frontend", "HTML5, CSS3, JavaScript vanilla, SweetAlert2"],
        ],
        [4.5 * cm, 12.5 * cm],
        styles,
    ))

    story.append(Paragraph("5. Modelo de dados", styles["h1"]))
    story.append(Paragraph(
        "O núcleo relacional combina cadastros mestres, tetos orçamentários e lançamentos. "
        "A tabela <font face='GoogleSans'>rubricas</font> é exposta na interface como <b>Categorias</b>.",
        styles["body"],
    ))
    story.append(_tabela(
        ["Tabela", "Função", "Campos principais"],
        [
            ["setores", "Centros de custo / departamentos", "id, nome, descricao"],
            ["fornecedores", "Parceiros comerciais", "id, nome, descricao"],
            ["rubricas", "Categorias de despesa", "id, nome, descricao"],
            ["orcamentos_anuais", "Teto anual global (legado / CLI)", "ano, valor_orcado, percentual_alerta"],
            ["orcamentos_mensais", "Rateio mensal do orçamento anual", "orcamento_anual_id, mes (1–12), valor"],
            ["orcamentos_setores", "Teto por setor, ano e mês (usado no dashboard)", "setor_id, ano, mes, valor; UNIQUE(setor, ano, mes)"],
            ["despesas", "Lançamentos", "descricao, valor, data_compra, setor_id, fornecedor_id, rubrica_id, destino, orcamento_mensal_id"],
            ["despesas_auditoria", "Histórico automático", "despesa_id, acao (INSERT/UPDATE/DELETE), JSON anterior/novo, usuario, data_alteracao"],
        ],
        [3.6 * cm, 5.2 * cm, 8.2 * cm],
        styles,
    ))
    story.append(Paragraph("Regras de integridade (scripts de migração)", styles["h2"]))
    story.append(_bullets([
        "Despesa exige setor e rubrica (NOT NULL).",
        "Valores de despesa e orçamento não podem ser negativos (CHECK).",
        "Unicidade de orçamento mensal por orçamento anual + mês.",
        "Índices em data_compra, setor, rubrica e combinações usadas nos filtros.",
        "Trigger <font face='GoogleSans'>trg_despesas_auditoria</font> grava INSERT, UPDATE e DELETE em <font face='GoogleSans'>despesas_auditoria</font>.",
        "Exclusão de setor, fornecedor ou categoria é recusada pela aplicação se existirem despesas vinculadas.",
    ], styles))

    story.append(Paragraph("6. Regras de negócio", styles["h1"]))
    story.append(Paragraph("6.1 Despesas", styles["h2"]))
    story.append(_bullets([
        "Campos obrigatórios: descrição, valor &gt; 0, data da compra, setor, fornecedor e categoria. Destino é opcional.",
        "Nova despesa abre com campos vazios e data padrão igual ao dia corrente.",
        "Edição usa PUT /api/despesas/&lt;id&gt; com o mesmo conjunto de validações.",
        "Limpar despesas remove todos os lançamentos após dupla confirmação na interface.",
    ], styles))
    story.append(Paragraph("6.2 Orçamento por setor", styles["h2"]))
    story.append(_bullets([
        "A grade de 12 meses carrega ao escolher setor ou ano.",
        "Salvamento automático ao sair do campo (blur) ou pressionar Enter.",
        "“Aplicar para todos os meses” replica o valor e persiste os 12 meses em lote (<font face='GoogleSans'>aplicar_todos: true</font>).",
        "Na visão resumida, a coluna Orçado soma os tetos de <font face='GoogleSans'>orcamentos_setores</font> no período; mês sem cadastro conta como R$ 0,00.",
        "A aba de resumo compara orçado, gasto, saldo e status por setor no ano.",
    ], styles))
    story.append(Paragraph("6.3 Status orçamentário", styles["h2"]))
    story.append(Paragraph(
        "O percentual é gasto ÷ orçado. A função <font face='GoogleSans'>calcular_status_orcamento</font> classifica:",
        styles["body"],
    ))
    story.append(_tabela(
        ["Condição", "Status exibido"],
        [
            ["Há gasto e orçado ≤ 0", "Acima do orçamento"],
            ["Percentual ≥ 100%", "Acima do orçamento"],
            ["Percentual ≥ 80% e &lt; 100%", "Perto de atingir o orçamento"],
            ["Demais casos", "Dentro do orçamento"],
        ],
        [8 * cm, 9 * cm],
        styles,
    ))

    story.append(Paragraph("7. Interface do dashboard", styles["h1"]))
    story.append(Paragraph(
        "A tela inicial concentra KPIs, filtros e a grade. O header traz um menu suspenso de ações rápidas, "
        "fechado ao clicar fora, escolher um item ou pressionar Esc.",
        styles["body"],
    ))
    story.append(Paragraph("Menu do sistema", styles["h2"]))
    story.append(_tabela(
        ["Grupo", "Ações"],
        [
            ["Lançamentos e cadastros", "Nova despesa; Setores; Fornecedores; Categorias; Orçamento por setor."],
            ["Relatórios e manutenção", "Exportar PDF; Limpar despesas."],
        ],
        [4.5 * cm, 12.5 * cm],
        styles,
    ))
    story.append(Paragraph("Visões e filtros", styles["h2"]))
    story.append(_bullets([
        "<b>Visão resumida:</b> consolidado por mês (orçado, gasto, saldo, % e status).",
        "<b>Visão detalhada:</b> lançamentos individuais, busca textual instantânea, edição e exclusão na coluna Ações. Card de categoria mais custosa no período filtrado.",
        "<b>Período:</b> campos De/Até e atalhos Este Mês (padrão), Mês Anterior, Este Ano, Ano Anterior e Todo o Período.",
        "<b>Filtros avançados:</b> gaveta com setor, fornecedor e categoria; badge com quantidade ativa; botão Limpar filtros.",
        "<b>Ordenação:</b> crescente/decrescente, seletor de coluna conforme a visão, e clique nos cabeçalhos da tabela.",
    ], styles))

    story.append(Paragraph("8. API REST", styles["h1"]))
    story.append(Paragraph(
        "Todas as rotas abaixo são servidas pelo processo Flask em <font face='GoogleSans'>app.py</font> (porta 5000 em modo debug).",
        styles["body"],
    ))
    story.append(_tabela(
        ["Método", "Rota", "Descrição"],
        ENDPOINTS,
        [2.8 * cm, 5.6 * cm, 8.6 * cm],
        styles,
    ))
    story.append(Paragraph(
        "Filtros comuns de consulta (query string): <font face='GoogleSans'>data_inicio</font>, <font face='GoogleSans'>data_fim</font> "
        "(AAAA-MM-DD), <font face='GoogleSans'>setor_id</font>, <font face='GoogleSans'>fornecedor_id</font>, "
        "<font face='GoogleSans'>categoria_id</font>. Em /api/exportar-pdf, <font face='GoogleSans'>visao=resumida</font> "
        "ou <font face='GoogleSans'>visao=detalhada</font>.",
        styles["body"],
    ))

    story.append(Paragraph("9. Relatórios PDF", styles["h1"]))
    story.append(_bullets([
        "Arquivos gravados em <font face='GoogleSans'>Exportações/</font> com carimbo de data/hora.",
        "Resumo: <font face='GoogleSans'>Orcamento_Resumo_AAAAMMDD_HHMMSS.pdf</font> — colunas Mês, Orçado, Gasto, % e Status.",
        "Detalhado: <font face='GoogleSans'>Despesas_Empresariais_AAAAMMDD_HHMMSS.pdf</font> — lançamentos do período.",
        "O PDF respeita os mesmos filtros da tela (datas, setor, fornecedor, categoria e visão).",
        "CLI: <font face='GoogleSans'>python main.py --ano 2026 --saida meu_relatorio.pdf</font>.",
    ], styles))

    story.append(Paragraph("10. Instalação e execução", styles["h1"]))
    story.append(Paragraph(
        "Pré-requisitos: Python 3.10+ e uma instância PostgreSQL (Supabase ou local). "
        "No diretório <font face='GoogleSans'>python sections</font>:",
        styles["body"],
    ))
    story.append(Paragraph(
        "python -m venv venv<br/>"
        "venv\\Scripts\\activate &nbsp;&nbsp;(Windows)<br/>"
        "pip install -r requirements.txt<br/>"
        "python app.py",
        styles["code"],
    ))
    story.append(Paragraph(
        "Crie <font face='GoogleSans'>python sections/.env</font> com DB_HOST, DB_PORT, DB_NAME, DB_USER e DB_PASSWORD. "
        "A conexão usa <font face='GoogleSans'>sslmode=require</font>. Não versione o arquivo .env.",
        styles["body"],
    ))

    story.append(Paragraph("11. Estrutura de pastas", styles["h1"]))
    story.append(Paragraph(
        "BudgetControl_v1.00/<br/>"
        "&nbsp;&nbsp;DB scripts/ &nbsp;— inserts, migrationwithupdates.sql, rollbacksec.sql<br/>"
        "&nbsp;&nbsp;Documentation/ &nbsp;— este documento (PDF e DOCX)<br/>"
        "&nbsp;&nbsp;Exportações/ &nbsp;— PDFs gerados pelo sistema<br/>"
        "&nbsp;&nbsp;Logs/ &nbsp;— logs de execução<br/>"
        "&nbsp;&nbsp;python sections/ &nbsp;— app.py, database.py, report.py, main.py, config.py, templates, static",
        styles["code"],
    ))

    story.append(Paragraph("12. Segurança e operação", styles["h1"]))
    story.append(_bullets([
        "Credenciais somente em variáveis de ambiente; o código encerra se faltar qualquer chave obrigatória.",
        "A API não implementa autenticação de usuários nesta versão: o dashboard é adequado a rede confiável / uso local.",
        "Exclusão em massa de despesas é irreversível do ponto de vista da aplicação (há trilha em auditoria enquanto o registro da despesa existir; DELETE dispara a trigger antes da remoção).",
        "Logs em nível DEBUG no servidor web; o CLI grava arquivo diário em Logs/.",
    ], styles))

    story.append(Paragraph("13. Limitações conhecidas desta versão", styles["h1"]))
    story.append(_bullets([
        "Sem login, perfis ou multiempresa.",
        "Orçamento operacional do dashboard é por setor/mês; o par orcamentos_anuais / orcamentos_mensais permanece no modelo e no CLI.",
        "Não há fluxo de aprovação de despesas nem conciliação bancária.",
        "A documentação de API é a lista de rotas deste documento; não há OpenAPI publicado.",
    ], styles))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)


def _set_run_font(run, name=FONTE_DOCX, size=11, bold=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color


def _add_heading(doc: Document, text: str, level: int):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = RGBColor(0xB5, 0x67, 0x0A) if level == 1 else RGBColor(0x1A, 0x1A, 0x1A)


def _add_p(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(text)
    _set_run_font(run)
    return p


def _add_bullets(doc: Document, items: list[str]):
    for item in items:
        p = doc.add_paragraph(item, style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        for run in p.runs:
            _set_run_font(run, size=11)


def _add_table(doc: Document, headers: list[str], rows: list[list[str]]):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for run in p.runs:
                _set_run_font(run, size=9, bold=True, color=RGBColor(255, 255, 255))
        tc_pr = hdr[i]._tc.get_or_add_tcPr()
        tc_pr.append(parse_xml(
            r'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:fill="1A1A1A"/>'
        ))
    for r_idx, row in enumerate(rows):
        cells = table.rows[r_idx + 1].cells
        for c_idx, val in enumerate(row):
            cells[c_idx].text = val
            for p in cells[c_idx].paragraphs:
                for run in p.runs:
                    _set_run_font(run, size=9)
    doc.add_paragraph()


def gerar_docx(caminho: Path) -> None:
    doc = Document()
    for nome_estilo in ("Normal", "Heading 1", "Heading 2", "List Bullet"):
        try:
            estilo = doc.styles[nome_estilo]
            estilo.font.name = FONTE_DOCX
            estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE_DOCX)
        except (KeyError, AttributeError):
            pass
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("BudgetControl")
    _set_run_font(r, size=28, bold=True, color=RGBColor(0x1A, 0x1A, 0x1A))

    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = s.add_run("Sistema de Controle Orçamentário e Gestão de Despesas Empresariais")
    _set_run_font(r, size=13, color=RGBColor(0xB5, 0x67, 0x0A))

    m = doc.add_paragraph()
    m.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = m.add_run(f"Documentação funcional e técnica  ·  Versão {VERSAO}  ·  {DATA_DOC}\nPython · Flask · PostgreSQL / Supabase")
    _set_run_font(r, size=10, color=RGBColor(0x55, 0x55, 0x55))

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run(f"BudgetControl v{VERSAO} — documentação do sistema — gerado em {DATA_DOC}")
    _set_run_font(fr, size=8, color=RGBColor(0x66, 0x66, 0x66))

    _add_heading(doc, "1. Visão geral", 1)
    _add_p(
        doc,
        "O BudgetControl é uma aplicação corporativa para cadastrar, classificar e acompanhar despesas "
        "em relação a tetos orçamentários definidos por setor, ano e mês. O usuário opera um dashboard web "
        "em Flask; os dados ficam no PostgreSQL (Supabase). Relatórios em PDF são gerados com ReportLab. "
        "Há ainda um script de linha de comando para emitir o consolidado anual sem abrir o navegador.",
    )
    _add_heading(doc, "Objetivos do sistema", 2)
    _add_bullets(doc, [
        "Registrar despesas com descrição, valor, data, setor, fornecedor, categoria e destino.",
        "Definir orçamento mensal por setor e comparar com o gasto real.",
        "Filtrar o dashboard por intervalo de datas, setor, fornecedor e categoria.",
        "Sinalizar execução (dentro, perto ou acima do orçamento) com limite padrão de 80%.",
        "Exportar PDF na visão resumida (mês a mês) ou detalhada (lançamentos).",
        "Manter cadastros mestres de setores, fornecedores e categorias, com proteção contra exclusão quando houver lançamentos vinculados.",
    ])

    _add_heading(doc, "2. Público e formas de uso", 1)
    _add_p(
        doc,
        "O público-alvo são gestores financeiros, controladoria e responsáveis de centro de custo. "
        "Existem dois modos: o dashboard web em http://127.0.0.1:5000 e o CLI (main.py) para PDF anual, "
        "com ano padrão 2026 em config.py, sobrescrevível com --ano.",
    )

    _add_heading(doc, "3. Arquitetura", 1)
    _add_p(
        doc,
        "Camadas: apresentação (HTML/CSS/JS), API REST (Flask), persistência (psycopg2) e relatórios (ReportLab).",
    )
    _add_table(
        doc,
        ["Camada", "Arquivo / pasta", "Responsabilidade"],
        [
            ["Apresentação", "templates/index.html + static/css/style.css", "Dashboard, filtros, modais, SweetAlert2."],
            ["API web", "app.py", "Rotas Flask, validação de payload, download de PDF."],
            ["Domínio / persistência", "database.py", "CRUD, consolidados, formatação de moeda e status."],
            ["Relatórios", "report.py", "PDFs resumido e detalhado (ReportLab)."],
            ["Configuração", "config.py + .env", "Credenciais PostgreSQL e parâmetros do CLI."],
            ["CLI", "main.py", "Geração de relatório anual via terminal."],
            ["Banco", "DB scripts/", "Migrações, índices, auditoria e rollback."],
            ["Saídas", "Exportações/ e Logs/", "PDFs gerados e arquivos de log."],
        ],
    )

    _add_heading(doc, "4. Stack tecnológica", 1)
    _add_table(
        doc,
        ["Item", "Tecnologia"],
        [
            ["Linguagem", "Python 3.10 ou superior"],
            ["Servidor web", "Flask 3+"],
            ["Banco de dados", "PostgreSQL (Supabase), conexão SSL obrigatória"],
            ["Driver", "psycopg2-binary"],
            ["Ambiente", "python-dotenv (.env)"],
            ["PDF", "ReportLab 4+"],
            ["Frontend", "HTML5, CSS3, JavaScript vanilla, SweetAlert2"],
        ],
    )

    _add_heading(doc, "5. Modelo de dados", 1)
    _add_p(
        doc,
        "O núcleo relacional combina cadastros mestres, tetos orçamentários e lançamentos. "
        "A tabela rubricas é exposta na interface como Categorias.",
    )
    _add_table(
        doc,
        ["Tabela", "Função", "Campos principais"],
        [
            ["setores", "Centros de custo / departamentos", "id, nome, descricao"],
            ["fornecedores", "Parceiros comerciais", "id, nome, descricao"],
            ["rubricas", "Categorias de despesa", "id, nome, descricao"],
            ["orcamentos_anuais", "Teto anual global (legado / CLI)", "ano, valor_orcado, percentual_alerta"],
            ["orcamentos_mensais", "Rateio mensal do orçamento anual", "orcamento_anual_id, mes (1–12), valor"],
            ["orcamentos_setores", "Teto por setor, ano e mês (dashboard)", "setor_id, ano, mes, valor; UNIQUE(setor, ano, mes)"],
            ["despesas", "Lançamentos", "descricao, valor, data_compra, setor_id, fornecedor_id, rubrica_id, destino"],
            ["despesas_auditoria", "Histórico automático", "acao INSERT/UPDATE/DELETE, JSON, usuario, data_alteracao"],
        ],
    )
    _add_heading(doc, "Regras de integridade", 2)
    _add_bullets(doc, [
        "Despesa exige setor e rubrica (NOT NULL).",
        "Valores de despesa e orçamento não podem ser negativos (CHECK).",
        "Unicidade de orçamento mensal por orçamento anual + mês.",
        "Índices em data_compra, setor, rubrica e combinações usadas nos filtros.",
        "Trigger trg_despesas_auditoria registra alterações em despesas_auditoria.",
        "Exclusão de setor, fornecedor ou categoria é recusada se existirem despesas vinculadas.",
    ])

    _add_heading(doc, "6. Regras de negócio", 1)
    _add_heading(doc, "6.1 Despesas", 2)
    _add_bullets(doc, [
        "Campos obrigatórios: descrição, valor maior que zero, data da compra, setor, fornecedor e categoria. Destino é opcional.",
        "Nova despesa abre com campos vazios e data padrão igual ao dia corrente.",
        "Edição usa PUT /api/despesas/<id> com as mesmas validações.",
        "Limpar despesas remove todos os lançamentos após dupla confirmação na interface.",
    ])
    _add_heading(doc, "6.2 Orçamento por setor", 2)
    _add_bullets(doc, [
        "A grade de 12 meses carrega ao escolher setor ou ano.",
        "Salvamento automático ao sair do campo (blur) ou pressionar Enter.",
        "Aplicar para todos os meses replica o valor e persiste os 12 meses em lote.",
        "Na visão resumida, Orçado soma os tetos de orcamentos_setores; mês sem cadastro conta como R$ 0,00.",
        "A aba de resumo compara orçado, gasto, saldo e status por setor no ano.",
    ])
    _add_heading(doc, "6.3 Status orçamentário", 2)
    _add_p(doc, "O percentual é gasto dividido pelo orçado. A classificação é:")
    _add_table(
        doc,
        ["Condição", "Status exibido"],
        [
            ["Há gasto e orçado ≤ 0", "Acima do orçamento"],
            ["Percentual ≥ 100%", "Acima do orçamento"],
            ["Percentual ≥ 80% e < 100%", "Perto de atingir o orçamento"],
            ["Demais casos", "Dentro do orçamento"],
        ],
    )

    _add_heading(doc, "7. Interface do dashboard", 1)
    _add_p(
        doc,
        "A tela inicial concentra KPIs, filtros e a grade. O header traz um menu suspenso de ações rápidas, "
        "fechado ao clicar fora, escolher um item ou pressionar Esc.",
    )
    _add_table(
        doc,
        ["Grupo", "Ações"],
        [
            ["Lançamentos e cadastros", "Nova despesa; Setores; Fornecedores; Categorias; Orçamento por setor."],
            ["Relatórios e manutenção", "Exportar PDF; Limpar despesas."],
        ],
    )
    _add_heading(doc, "Visões e filtros", 2)
    _add_bullets(doc, [
        "Visão resumida: consolidado por mês (orçado, gasto, saldo, % e status).",
        "Visão detalhada: lançamentos individuais, busca textual, edição e exclusão. Card de categoria mais custosa.",
        "Período: De/Até e atalhos Este Mês (padrão), Mês Anterior, Este Ano, Ano Anterior e Todo o Período.",
        "Filtros avançados: setor, fornecedor e categoria; badge de quantidade ativa; limpar filtros.",
        "Ordenação crescente/decrescente por coluna, também pelos cabeçalhos da tabela.",
    ])

    _add_heading(doc, "8. API REST", 1)
    _add_p(doc, "Rotas servidas por app.py na porta 5000 (modo debug).")
    _add_table(doc, ["Método", "Rota", "Descrição"], ENDPOINTS)
    _add_p(
        doc,
        "Filtros comuns: data_inicio, data_fim (AAAA-MM-DD), setor_id, fornecedor_id, categoria_id. "
        "Em /api/exportar-pdf use visao=resumida ou visao=detalhada.",
    )

    _add_heading(doc, "9. Relatórios PDF", 1)
    _add_bullets(doc, [
        "Arquivos gravados em Exportações/ com carimbo de data/hora.",
        "Resumo: Orcamento_Resumo_AAAAMMDD_HHMMSS.pdf.",
        "Detalhado: Despesas_Empresariais_AAAAMMDD_HHMMSS.pdf.",
        "O PDF respeita os filtros da tela.",
        "CLI: python main.py --ano 2026 --saida meu_relatorio.pdf",
    ])

    _add_heading(doc, "10. Instalação e execução", 1)
    _add_p(
        doc,
        "Pré-requisitos: Python 3.10+ e PostgreSQL (Supabase ou local). No diretório python sections: "
        "criar venv, pip install -r requirements.txt e python app.py. "
        "Crie python sections/.env com DB_HOST, DB_PORT, DB_NAME, DB_USER e DB_PASSWORD. "
        "A conexão usa sslmode=require. Não versione o .env.",
    )

    _add_heading(doc, "11. Estrutura de pastas", 1)
    _add_bullets(doc, [
        "DB scripts/ — inserts, migrationwithupdates.sql, rollbacksec.sql",
        "Documentation/ — este documento (PDF e DOCX)",
        "Exportações/ — PDFs gerados pelo sistema",
        "Logs/ — logs de execução",
        "python sections/ — app.py, database.py, report.py, main.py, config.py, templates, static",
    ])

    _add_heading(doc, "12. Segurança e operação", 1)
    _add_bullets(doc, [
        "Credenciais somente em variáveis de ambiente; o código encerra se faltar chave obrigatória.",
        "Esta versão não tem autenticação de usuários: o dashboard é adequado a rede confiável ou uso local.",
        "Exclusão em massa de despesas é irreversível na interface.",
        "Logs em DEBUG no servidor web; o CLI grava arquivo diário em Logs/.",
    ])

    _add_heading(doc, "13. Limitações conhecidas desta versão", 1)
    _add_bullets(doc, [
        "Sem login, perfis ou multiempresa.",
        "O orçamento operacional do dashboard é por setor/mês; orcamentos_anuais e orcamentos_mensais permanecem no modelo e no CLI.",
        "Não há aprovação de despesas nem conciliação bancária.",
        "Não há especificação OpenAPI publicada.",
    ])

    doc.save(str(caminho))


if __name__ == "__main__":
    SAIDA_DIR.mkdir(exist_ok=True)
    pdf = SAIDA_DIR / "BudgetControl_Documentacao_Sistema_v1.00.pdf"
    docx = SAIDA_DIR / "BudgetControl_Documentacao_Sistema_v1.00.docx"
    gerar_pdf(pdf)
    gerar_docx(docx)
    print(f"PDF:  {pdf}")
    print(f"DOCX: {docx}")
