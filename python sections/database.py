import logging
from datetime import datetime, date
from decimal import Decimal
import psycopg2
import bcrypt
import config


log = logging.getLogger(__name__)

MESES_PT = {
    1: "Janeiro",   2: "Fevereiro",  3: "Março",
    4: "Abril",     5: "Maio",       6: "Junho",
    7: "Julho",     8: "Agosto",     9: "Setembro",
    10: "Outubro",  11: "Novembro",  12: "Dezembro",
}


def _fmt_moeda(valor) -> str:
    """Formata um valor numérico como moeda brasileira (R$ 1.234,56)."""
    if valor is None:
        return "R$ 0,00"
    num = float(valor)
    inteiro = int(abs(num))
    centavos = round((abs(num) - inteiro) * 100)
    parte_inteira = f"{inteiro:,}".replace(",", ".")
    sinal = "-" if num < 0 else ""
    return f"{sinal}R$ {parte_inteira},{centavos:02d}"


def _fmt_percentual(valor) -> str:
    """Formata um valor numérico como percentual com vírgula (ex: 75,30%)."""
    if valor is None:
        return "0,00%"
    texto = f"{float(valor):.2f}".replace(".", ",")
    return f"{texto}%"


def calcular_status_orcamento(pct: float, orcado: float = 0, gasto: float = 0) -> str:
    """
    Retorna o status baseado no percentual do orçamento:
    - Abaixo de 80%: "Dentro do orçamento"
    - Entre 80% e 99%: "Perto do orçamento"
    - 100% ou mais: "Acima do orçamento"
    """
    pct_val = float(pct or 0)
    orc_val = float(orcado or 0)
    gst_val = float(gasto or 0)

    if orc_val <= 0 and gst_val > 0:
        return "Acima do orçamento"
    if pct_val >= 100:
        return "Acima do orçamento"
    if pct_val >= 80:
        return "Perto de atingir o orçamento"
    return "Dentro do orçamento"


def get_db_connection():
    """Retorna uma conexão aberta com o banco PostgreSQL / Supabase."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        sslmode="require",
        connect_timeout=30,
    )


def buscar_anos() -> list[int]:
    """Retorna a lista de anos disponíveis no banco ordenados de forma decrescente."""
    query = """
        SELECT DISTINCT ano FROM (
            SELECT ano FROM orcamentos_anuais
            UNION
            SELECT EXTRACT(YEAR FROM data_compra)::integer AS ano FROM despesas WHERE data_compra IS NOT NULL
        ) AS anos_unificados
        WHERE ano IS NOT NULL
        ORDER BY ano DESC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return [int(row[0]) for row in cur.fetchall()]
    except Exception as e:
        log.error(f"Erro ao buscar anos: {e}")
        return [2026, 2025]


# ── Setores (Departamentos / Centros de Custo da Empresa) ─────────────────────

def buscar_setores() -> list[dict]:
    """Retorna lista de setores com estatísticas de despesas."""
    query = """
        SELECT s.id,
               s.nome,
               COALESCE(s.descricao, '') AS descricao,
               COUNT(d.id) AS total_despesas,
               COALESCE(SUM(d.valor), 0) AS total_gasto
        FROM setores s
        LEFT JOIN despesas d ON d.setor_id = s.id
        GROUP BY s.id, s.nome, s.descricao
        ORDER BY s.nome ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "descricao": r[2],
                        "total_despesas": r[3],
                        "total_gasto": float(r[4]),
                        "total_gasto_fmt": _fmt_moeda(r[4]),
                    }
                    for r in rows
                ]
    except Exception as e:
        log.error(f"Erro ao buscar setores: {e}")
        return []


def cadastrar_setor(nome: str, descricao: str = "") -> dict:
    """Insere um novo setor no banco de dados."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome do setor é obrigatório.")

    query = """
        INSERT INTO setores (nome, descricao)
        VALUES (%s, %s)
        RETURNING id, nome, descricao;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (nome, descricao.strip()))
                r = cur.fetchone()
                conn.commit()
                return {"id": r[0], "nome": r[1], "descricao": r[2], "total_despesas": 0, "total_gasto": 0, "total_gasto_fmt": "R$ 0,00"}
    except Exception as e:
        log.error(f"Erro ao cadastrar setor: {e}")
        raise


def atualizar_setor(setor_id: int, nome: str, descricao: str = "") -> dict:
    """Atualiza um setor existente."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome do setor é obrigatório.")

    query = """
        UPDATE setores
        SET nome = %s, descricao = %s
        WHERE id = %s
        RETURNING id, nome, descricao;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (nome, descricao.strip(), setor_id))
                r = cur.fetchone()
                if not r:
                    raise ValueError("Setor não encontrado.")
                conn.commit()
                return {"id": r[0], "nome": r[1], "descricao": r[2]}
    except Exception as e:
        log.error(f"Erro ao atualizar setor: {e}")
        raise


def excluir_setor(setor_id: int) -> dict:
    """Exclui um setor caso não haja despesas vinculadas a ele."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM despesas WHERE setor_id = %s;", (setor_id,))
            qtd = cur.fetchone()[0]
            if qtd > 0:
                raise ValueError(
                    f"Não é possível excluir o setor pois existem {qtd} despesa(s) vinculada(s) a ele. "
                    "Exclua ou reatribua as despesas primeiro."
                )

            cur.execute("DELETE FROM setores WHERE id = %s RETURNING id, nome;", (setor_id,))
            r = cur.fetchone()
            if not r:
                raise ValueError("Setor não encontrado.")
            conn.commit()
            return {"id": r[0], "nome": r[1]}


# ── Fornecedores (Onde foi gasto o dinheiro) ──────────────────────────────────

def buscar_fornecedores() -> list[dict]:
    """Retorna lista de fornecedores com estatísticas de despesas."""
    query = """
        SELECT f.id,
               f.nome,
               COALESCE(f.descricao, '') AS descricao,
               COUNT(d.id) AS total_despesas,
               COALESCE(SUM(d.valor), 0) AS total_gasto
        FROM fornecedores f
        LEFT JOIN despesas d ON d.fornecedor_id = f.id
        GROUP BY f.id, f.nome, f.descricao
        ORDER BY f.nome ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "descricao": r[2],
                        "total_despesas": r[3],
                        "total_gasto": float(r[4]),
                        "total_gasto_fmt": _fmt_moeda(r[4]),
                    }
                    for r in rows
                ]
    except Exception as e:
        log.error(f"Erro ao buscar fornecedores: {e}")
        return []


def cadastrar_fornecedor(nome: str, descricao: str = "") -> dict:
    """Insere um novo fornecedor."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome do fornecedor é obrigatório.")

    query = """
        INSERT INTO fornecedores (nome, descricao)
        VALUES (%s, %s)
        RETURNING id, nome, descricao;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (nome, descricao.strip()))
                r = cur.fetchone()
                conn.commit()
                return {"id": r[0], "nome": r[1], "descricao": r[2], "total_despesas": 0, "total_gasto": 0, "total_gasto_fmt": "R$ 0,00"}
    except Exception as e:
        log.error(f"Erro ao cadastrar fornecedor: {e}")
        raise


def atualizar_fornecedor(fornecedor_id: int, nome: str, descricao: str = "") -> dict:
    """Atualiza dados de um fornecedor."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome do fornecedor é obrigatório.")

    query = """
        UPDATE fornecedores
        SET nome = %s, descricao = %s
        WHERE id = %s
        RETURNING id, nome, descricao;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (nome, descricao.strip(), fornecedor_id))
                r = cur.fetchone()
                if not r:
                    raise ValueError("Fornecedor não encontrado.")
                conn.commit()
                return {"id": r[0], "nome": r[1], "descricao": r[2]}
    except Exception as e:
        log.error(f"Erro ao atualizar fornecedor: {e}")
        raise


def excluir_fornecedor(fornecedor_id: int) -> dict:
    """Exclui um fornecedor caso não haja despesas vinculadas."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM despesas WHERE fornecedor_id = %s;", (fornecedor_id,))
            qtd = cur.fetchone()[0]
            if qtd > 0:
                raise ValueError(
                    f"Não é possível excluir este fornecedor pois existem {qtd} despesa(s) vinculada(s) a ele. "
                    "Exclua ou reatribua as despesas primeiro."
                )

            cur.execute("DELETE FROM fornecedores WHERE id = %s RETURNING id, nome;", (fornecedor_id,))
            r = cur.fetchone()
            if not r:
                raise ValueError("Fornecedor não encontrado.")
            conn.commit()
            return {"id": r[0], "nome": r[1]}


# ── Categorias (Tabela rubricas) ──────────────────────────────────────────────

def buscar_categorias() -> list[dict]:
    """Retorna lista de categorias de despesas (armazenadas em rubricas) com estatísticas."""
    query = """
        SELECT r.id,
               r.nome,
               COALESCE(r.descricao, '') AS descricao,
               COUNT(d.id) AS total_despesas,
               COALESCE(SUM(d.valor), 0) AS total_gasto
        FROM rubricas r
        LEFT JOIN despesas d ON d.rubrica_id = r.id
        GROUP BY r.id, r.nome, r.descricao
        ORDER BY r.nome ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "descricao": r[2],
                        "total_despesas": r[3],
                        "total_gasto": float(r[4]),
                        "total_gasto_fmt": _fmt_moeda(r[4]),
                    }
                    for r in rows
                ]
    except Exception as e:
        log.error(f"Erro ao buscar categorias: {e}")
        return []


def cadastrar_categoria(nome: str, descricao: str = "") -> dict:
    """Insere uma nova categoria (rubrica)."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome da categoria é obrigatório.")

    query = """
        INSERT INTO rubricas (nome, descricao)
        VALUES (%s, %s)
        RETURNING id, nome, descricao;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (nome, descricao.strip()))
                r = cur.fetchone()
                conn.commit()
                return {"id": r[0], "nome": r[1], "descricao": r[2], "total_despesas": 0, "total_gasto": 0, "total_gasto_fmt": "R$ 0,00"}
    except Exception as e:
        log.error(f"Erro ao cadastrar categoria: {e}")
        raise


def atualizar_categoria(categoria_id: int, nome: str, descricao: str = "") -> dict:
    """Atualiza dados de uma categoria."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome da categoria é obrigatório.")

    query = """
        UPDATE rubricas
        SET nome = %s, descricao = %s
        WHERE id = %s
        RETURNING id, nome, descricao;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (nome, descricao.strip(), categoria_id))
                r = cur.fetchone()
                if not r:
                    raise ValueError("Categoria não encontrada.")
                conn.commit()
                return {"id": r[0], "nome": r[1], "descricao": r[2]}
    except Exception as e:
        log.error(f"Erro ao atualizar categoria: {e}")
        raise


def excluir_categoria(categoria_id: int) -> dict:
    """Exclui uma categoria caso não haja despesas vinculadas a ela."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM despesas WHERE rubrica_id = %s;", (categoria_id,))
            qtd = cur.fetchone()[0]
            if qtd > 0:
                raise ValueError(
                    f"Não é possível excluir esta categoria pois existem {qtd} despesa(s) vinculada(s) a ela. "
                    "Exclua ou reatribua as despesas primeiro."
                )

            cur.execute("DELETE FROM rubricas WHERE id = %s RETURNING id, nome;", (categoria_id,))
            r = cur.fetchone()
            if not r:
                raise ValueError("Categoria não encontrada.")
            conn.commit()
            return {"id": r[0], "nome": r[1]}


buscar_rubricas = buscar_categorias
buscar_destinos = buscar_categorias


# ── Orçamentos por Setor (orcamentos_setores) ─────────────────────────────────

def buscar_orcamentos_setor(setor_id: int, ano: int) -> list[dict]:
    """
    Retorna os 12 meses do ano para o setor informado, incluindo valor orçado
    e total gasto real para comparação. Meses sem registro retornam valor=0.
    """
    query = """
        WITH meses AS (
            SELECT generate_series(1, 12) AS mes
        )
        SELECT
            m.mes,
            COALESCE(os.valor, 0) AS valor_orcado,
            COALESCE(SUM(d.valor), 0) AS gasto_real,
            os.id AS orcamento_id
        FROM meses m
        LEFT JOIN orcamentos_setores os
            ON os.setor_id = %s AND os.ano = %s AND os.mes = m.mes
        LEFT JOIN orcamentos_mensais om
            ON om.mes = m.mes
            AND om.orcamento_anual_id IN (
                SELECT id FROM orcamentos_anuais WHERE ano = %s
            )
        LEFT JOIN despesas d
            ON d.orcamento_mensal_id = om.id
            AND d.setor_id = %s
            AND EXTRACT(YEAR FROM d.data_compra) = %s
            AND EXTRACT(MONTH FROM d.data_compra) = m.mes
        GROUP BY m.mes, os.valor, os.id
        ORDER BY m.mes ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (setor_id, ano, ano, setor_id, ano))
                rows = cur.fetchall()
                result = []
                for r in rows:
                    mes_num, orcado, gasto, orc_id = r
                    orcado = float(orcado or 0)
                    gasto = float(gasto or 0)
                    saldo = orcado - gasto
                    pct = round((gasto / orcado * 100), 2) if orcado > 0 else 0
                    result.append({
                        "mes": mes_num,
                        "mes_nome": MESES_PT.get(mes_num, f"Mês {mes_num}"),
                        "orcamento_id": orc_id,
                        "valor_orcado": orcado,
                        "valor_orcado_fmt": _fmt_moeda(orcado),
                        "gasto_real": gasto,
                        "gasto_real_fmt": _fmt_moeda(gasto),
                        "saldo": saldo,
                        "saldo_fmt": _fmt_moeda(saldo),
                        "percentual": pct,
                        "percentual_fmt": _fmt_percentual(pct),
                        "status": calcular_status_orcamento(pct, orcado, gasto),
                    })
                return result
    except Exception as e:
        log.error(f"Erro ao buscar orcamentos do setor {setor_id} ano {ano}: {e}")
        raise


def salvar_orcamento_setor(setor_id: int, ano: int, mes: int, valor: float) -> dict:
    """
    Insere ou atualiza (upsert) o orçamento mensal de um setor.
    Retorna o registro persistido.
    """
    if valor < 0:
        raise ValueError("O valor do orçamento não pode ser negativo.")
    if not (1 <= mes <= 12):
        raise ValueError("Mês inválido.")

    query = """
        INSERT INTO orcamentos_setores (setor_id, ano, mes, valor)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (setor_id, ano, mes) DO UPDATE SET valor = EXCLUDED.valor
        RETURNING id, setor_id, ano, mes, valor;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (setor_id, ano, mes, valor))
                r = cur.fetchone()
                conn.commit()
                return {
                    "id": r[0],
                    "setor_id": r[1],
                    "ano": r[2],
                    "mes": r[3],
                    "valor": float(r[4]),
                    "valor_fmt": _fmt_moeda(float(r[4])),
                }
    except Exception as e:
        log.error(f"Erro ao salvar orcamento do setor {setor_id}: {e}")
        raise


def salvar_orcamento_setor_todos(setor_id: int, ano: int, valor: float) -> list[dict]:
    """
    Define o mesmo valor de orçamento para todos os 12 meses do ano para o setor informado.
    Realiza upsert atômico para os meses de 1 a 12.
    """
    if valor < 0:
        raise ValueError("O valor do orçamento não pode ser negativo.")

    query = """
        INSERT INTO orcamentos_setores (setor_id, ano, mes, valor)
        SELECT %s, %s, m, %s
        FROM generate_series(1, 12) AS m
        ON CONFLICT (setor_id, ano, mes) DO UPDATE SET valor = EXCLUDED.valor
        RETURNING id, setor_id, ano, mes, valor;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (setor_id, ano, valor))
                rows = cur.fetchall()
                conn.commit()
                return [
                    {
                        "id": r[0],
                        "setor_id": r[1],
                        "ano": r[2],
                        "mes": r[3],
                        "valor": float(r[4]),
                        "valor_fmt": _fmt_moeda(float(r[4])),
                    }
                    for r in rows
                ]
    except Exception as e:
        log.error(f"Erro ao salvar orcamento para todos os meses do setor {setor_id}: {e}")
        raise


def buscar_resumo_orcamentos_setores(ano: int) -> list[dict]:
    """
    Retorna resumo anual de orçamento × gasto real para todos os setores.
    Útil para dashboards comparativos entre setores.
    """
    query = """
        SELECT
            s.id AS setor_id,
            s.nome AS setor_nome,
            COALESCE(SUM(os.valor), 0) AS total_orcado,
            COALESCE(SUM(d.valor), 0) AS total_gasto
        FROM setores s
        LEFT JOIN orcamentos_setores os ON os.setor_id = s.id AND os.ano = %s
        LEFT JOIN despesas d
            ON d.setor_id = s.id
            AND EXTRACT(YEAR FROM d.data_compra) = %s
        GROUP BY s.id, s.nome
        ORDER BY s.nome ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (ano, ano))
                rows = cur.fetchall()
                result = []
                for r in rows:
                    s_id, s_nome, orcado, gasto = r
                    orcado = float(orcado or 0)
                    gasto = float(gasto or 0)
                    saldo = orcado - gasto
                    pct = round((gasto / orcado * 100), 2) if orcado > 0 else 0
                    result.append({
                        "setor_id": s_id,
                        "setor_nome": s_nome,
                        "total_orcado": orcado,
                        "total_orcado_fmt": _fmt_moeda(orcado),
                        "total_gasto": gasto,
                        "total_gasto_fmt": _fmt_moeda(gasto),
                        "saldo": saldo,
                        "saldo_fmt": _fmt_moeda(saldo),
                        "percentual": pct,
                        "percentual_fmt": _fmt_percentual(pct),
                        "status": calcular_status_orcamento(pct, orcado, gasto),
                    })
                return result
    except Exception as e:
        log.error(f"Erro ao buscar resumo de orcamentos por setor: {e}")
        raise


# ── Consulta Resumida por Intervalo de Datas ─────────────────────────────────

def buscar_dados_periodo(data_inicio: str, data_fim: str, setor_id: int = None, fornecedor_id: int = None, categoria_id: int = None) -> list[dict]:
    """
    Calcula os orçamentos e gastos mês a mês dentro do intervalo [data_inicio, data_fim],
    com suporte a filtros por setor, fornecedor e categoria.
    """
    query = """
        WITH meses_periodo AS (
            SELECT generate_series(
                date_trunc('month', %s::date),
                date_trunc('month', %s::date),
                interval '1 month'
            )::date AS inicio_mes
        ),
        orcamento_calculado AS (
            SELECT
                m.inicio_mes,
                COALESCE(
                    CASE
                        WHEN %s::integer IS NOT NULL THEN (
                            SELECT os.valor
                            FROM orcamentos_setores os
                            WHERE os.setor_id = %s::integer
                              AND os.ano = EXTRACT(YEAR FROM m.inicio_mes)
                              AND os.mes = EXTRACT(MONTH FROM m.inicio_mes)
                        )
                        ELSE (
                            SELECT SUM(os.valor)
                            FROM orcamentos_setores os
                            WHERE os.ano = EXTRACT(YEAR FROM m.inicio_mes)
                              AND os.mes = EXTRACT(MONTH FROM m.inicio_mes)
                        )
                    END,
                    0
                ) AS valor_orcado
            FROM meses_periodo m
        )
        SELECT
            EXTRACT(YEAR FROM m.inicio_mes)::integer AS ano,
            EXTRACT(MONTH FROM m.inicio_mes)::integer AS mes,
            oc.valor_orcado AS orcado_mensal,
            COALESCE(SUM(d.valor), 0) AS gasto_mensal,
            ROUND((COALESCE(SUM(d.valor), 0) / NULLIF(oc.valor_orcado, 0)) * 100, 2) AS percentual_utilizado,
            CASE
                WHEN oc.valor_orcado = 0 AND COALESCE(SUM(d.valor), 0) > 0 THEN 'Acima do orçamento'
                WHEN (COALESCE(SUM(d.valor), 0) / NULLIF(oc.valor_orcado, 0)) * 100 >= 100 THEN 'Acima do orçamento'
                WHEN (COALESCE(SUM(d.valor), 0) / NULLIF(oc.valor_orcado, 0)) * 100 >= 80 THEN 'Perto do orçamento'
                ELSE 'Dentro do orçamento'
            END AS status,
            COALESCE(oa.percentual_alerta, 80) AS pct_alerta
        FROM meses_periodo m
        JOIN orcamento_calculado oc ON oc.inicio_mes = m.inicio_mes
        LEFT JOIN orcamentos_anuais oa
            ON oa.ano = EXTRACT(YEAR FROM m.inicio_mes)
        LEFT JOIN orcamentos_mensais om
            ON om.orcamento_anual_id = oa.id AND om.mes = EXTRACT(MONTH FROM m.inicio_mes)
        LEFT JOIN despesas d
            ON d.orcamento_mensal_id = om.id
           AND d.data_compra >= %s
           AND d.data_compra <= %s
           AND (%s IS NULL OR d.setor_id = %s)
           AND (%s IS NULL OR d.fornecedor_id = %s)
           AND (%s IS NULL OR d.rubrica_id = %s)
        GROUP BY m.inicio_mes, oc.valor_orcado, oa.percentual_alerta
        ORDER BY m.inicio_mes ASC;
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    data_inicio, data_fim,
                    setor_id, setor_id,
                    data_inicio, data_fim,
                    setor_id, setor_id,
                    fornecedor_id, fornecedor_id,
                    categoria_id, categoria_id
                ))
                rows = cur.fetchall()
    except Exception as e:
        log.error(f"Erro ao buscar dados consolidados: {e}")
        raise

    meses = []
    for r in rows:
        ano_num, mes_num, orcado, gasto, pct, status_sql, pct_alerta = r
        orcado = float(orcado or 0)
        gasto = float(gasto or 0)
        pct = float(pct or 0)
        nome_mes = MESES_PT.get(mes_num, f"Mês {mes_num}")

        meses.append({
            "ano": ano_num,
            "mes_num": mes_num,
            "mes": f"{nome_mes}/{ano_num}",
            "mes_puro": nome_mes,
            "orcado": orcado,
            "orcado_fmt": _fmt_moeda(orcado),
            "gasto": gasto,
            "gasto_fmt": _fmt_moeda(gasto),
            "saldo": orcado - gasto,
            "saldo_fmt": _fmt_moeda(orcado - gasto),
            "percentual": round(pct, 2),
            "percentual_fmt": _fmt_percentual(pct),
            "status": calcular_status_orcamento(pct, orcado, gasto),
            "pct_alerta": float(pct_alerta or 80),
        })

    return meses


def buscar_dados(ano: int = None, mes: int = None) -> list[list[str]]:
    """Função legada para compatibilidade com main.py CLI."""
    filtro_ano = ano or config.ANO_FILTRO
    dt_inicio = f"{filtro_ano}-01-01" if not mes else f"{filtro_ano}-{str(mes).zfill(2)}-01"
    dt_fim = f"{filtro_ano}-12-31" if not mes else f"{filtro_ano}-{str(mes).zfill(2)}-28"

    registros = buscar_dados_periodo(dt_inicio, dt_fim)
    dados = []
    for m in registros:
        dados.append([
            m["mes_puro"],
            m["orcado_fmt"],
            m["gasto_fmt"],
            m["percentual_fmt"],
            m["status"]
        ])
    return dados


# ── Consulta Detalhada por Intervalo de Datas ────────────────────────────────

def buscar_despesas_periodo(data_inicio: str, data_fim: str, setor_id: int = None, fornecedor_id: int = None, categoria_id: int = None) -> list[dict]:
    """
    Retorna despesas detalhadas no período contemplando Setor, Fornecedor, Categoria e Destino.
    """
    query = """
        SELECT d.id,
               d.descricao,
               d.valor,
               TO_CHAR(d.data_compra, 'DD/MM/YYYY') AS data_formatada,
               d.data_compra,
               COALESCE(s.nome, 'Sem Setor') AS setor,
               COALESCE(f.nome, 'Sem Fornecedor') AS fornecedor,
               COALESCE(r.nome, 'Sem Categoria') AS categoria,
               COALESCE(d.destino, 'Geral') AS destino,
               om.mes,
               EXTRACT(YEAR FROM d.data_compra)::integer AS ano_compra,
               d.setor_id,
               d.fornecedor_id,
               d.rubrica_id AS categoria_id
        FROM despesas d
        LEFT JOIN setores s ON s.id = d.setor_id
        LEFT JOIN fornecedores f ON f.id = d.fornecedor_id
        LEFT JOIN rubricas r ON r.id = d.rubrica_id
        LEFT JOIN orcamentos_mensais om ON om.id = d.orcamento_mensal_id
        WHERE d.data_compra >= %s AND d.data_compra <= %s
          AND (%s IS NULL OR d.setor_id = %s)
          AND (%s IS NULL OR d.fornecedor_id = %s)
          AND (%s IS NULL OR d.rubrica_id = %s)
        ORDER BY d.data_compra DESC, d.id DESC;
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    data_inicio, data_fim,
                    setor_id, setor_id,
                    fornecedor_id, fornecedor_id,
                    categoria_id, categoria_id
                ))
                rows = cur.fetchall()
    except Exception as e:
        log.error(f"Erro ao buscar despesas do período: {e}")
        raise

    despesas = []
    for row in rows:
        d_id, desc, val, dt_fmt, dt_raw, setor, fornecedor, categoria, destino, m_num, ano_c, s_id, f_id, c_id = row
        val_float = float(val or 0)
        m_nome = MESES_PT.get(m_num, f"Mês {m_num}" if m_num else "-")

        despesas.append({
            "id": d_id,
            "descricao": desc,
            "valor": val_float,
            "valor_fmt": _fmt_moeda(val_float),
            "data": dt_fmt or (dt_raw.strftime("%d/%m/%Y") if dt_raw else ""),
            "data_raw": dt_raw.strftime("%Y-%m-%d") if dt_raw else "",
            "setor": setor,
            "setor_id": s_id,
            "fornecedor": fornecedor,
            "fornecedor_id": f_id,
            "categoria": categoria,
            "categoria_id": c_id,
            "destino": destino,
            "mes_num": m_num,
            "mes_nome": f"{m_nome}/{ano_c}" if ano_c else m_nome,
        })

    return despesas


def buscar_despesas(ano: int = None, mes: int = None) -> list[dict]:
    """Alias legado."""
    filtro_ano = ano or config.ANO_FILTRO
    dt_inicio = f"{filtro_ano}-{str(mes).zfill(2)}-01" if (mes and 1 <= mes <= 12) else f"{filtro_ano}-01-01"
    dt_fim = f"{filtro_ano}-{str(mes).zfill(2)}-28" if (mes and 1 <= mes <= 12) else f"{filtro_ano}-12-31"
    return buscar_despesas_periodo(dt_inicio, dt_fim)


# ── Cadastro, Exclusão e Limpeza de Despesas ─────────────────────────────────

def cadastrar_despesa(descricao: str, valor: float, data_compra: str, setor_id: int, fornecedor_id: int, categoria_id: int, destino: str = "") -> dict:
    """
    Cadastra uma nova despesa empresarial contemplando:
    Setor, Fornecedor, Categoria, Destino, Descrição, Valor e Data.
    """
    descricao = (descricao or "").strip()
    destino = (destino or "").strip() or "Sede / Uso Geral"

    if not descricao:
        raise ValueError("A descrição da despesa é obrigatória.")
    if valor <= 0:
        raise ValueError("O valor da despesa deve ser maior que zero.")
    if not data_compra:
        raise ValueError("A data da compra é obrigatória.")
    if not setor_id:
        raise ValueError("O setor é obrigatório.")
    if not fornecedor_id:
        raise ValueError("O fornecedor é obrigatório.")
    if not categoria_id:
        raise ValueError("A categoria é obrigatória.")

    dt = datetime.strptime(data_compra, "%Y-%m-%d").date()
    ano = dt.year
    mes = dt.month

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Obter ou criar orcamento_anual
            cur.execute("SELECT id FROM orcamentos_anuais WHERE ano = %s;", (ano,))
            oa = cur.fetchone()
            if oa:
                oa_id = oa[0]
            else:
                cur.execute(
                    "INSERT INTO orcamentos_anuais (ano, valor_orcado, percentual_alerta, descricao) "
                    "VALUES (%s, 0, 80, %s) RETURNING id;",
                    (ano, f"Orçamento {ano}")
                )
                oa_id = cur.fetchone()[0]

            # 2. Obter ou criar orcamento_mensal
            cur.execute(
                "SELECT id FROM orcamentos_mensais WHERE orcamento_anual_id = %s AND mes = %s;",
                (oa_id, mes)
            )
            om = cur.fetchone()
            if om:
                om_id = om[0]
            else:
                cur.execute(
                    "INSERT INTO orcamentos_mensais (orcamento_anual_id, mes, valor) "
                    "VALUES (%s, %s, 0) RETURNING id;",
                    (oa_id, mes)
                )
                om_id = cur.fetchone()[0]

            # 3. Inserir despesa completa
            cur.execute(
                """
                INSERT INTO despesas (descricao, valor, data_compra, setor_id, fornecedor_id, rubrica_id, destino, orcamento_mensal_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, descricao, valor, data_compra, setor_id, fornecedor_id, rubrica_id, destino;
                """,
                (descricao, valor, dt, setor_id, fornecedor_id, categoria_id, destino, om_id)
            )
            row = cur.fetchone()
            conn.commit()

            return {
                "id": row[0],
                "descricao": row[1],
                "valor": float(row[2]),
                "data_compra": row[3].strftime("%Y-%m-%d"),
                "setor_id": row[4],
                "fornecedor_id": row[5],
                "categoria_id": row[6],
                "destino": row[7],
                "orcamento_mensal_id": om_id,
            }


def atualizar_despesa(despesa_id: int, descricao: str, valor: float, data_compra: str, setor_id: int, fornecedor_id: int, categoria_id: int, destino: str = "") -> dict:
    """
    Atualiza um lançamento de despesa existente.
    """
    descricao = (descricao or "").strip()
    destino = (destino or "").strip() or "Sede / Uso Geral"

    if not despesa_id:
        raise ValueError("ID da despesa inválido.")
    if not descricao:
        raise ValueError("A descrição da despesa é obrigatória.")
    if valor <= 0:
        raise ValueError("O valor da despesa deve ser maior que zero.")
    if not data_compra:
        raise ValueError("A data da compra é obrigatória.")
    if not setor_id:
        raise ValueError("O setor é obrigatório.")
    if not fornecedor_id:
        raise ValueError("O fornecedor é obrigatório.")
    if not categoria_id:
        raise ValueError("A categoria é obrigatória.")

    dt = datetime.strptime(data_compra, "%Y-%m-%d").date()
    ano = dt.year
    mes = dt.month

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Obter ou criar orcamento_anual
            cur.execute("SELECT id FROM orcamentos_anuais WHERE ano = %s;", (ano,))
            oa = cur.fetchone()
            if oa:
                oa_id = oa[0]
            else:
                cur.execute(
                    "INSERT INTO orcamentos_anuais (ano, valor_orcado, percentual_alerta, descricao) "
                    "VALUES (%s, 0, 80, %s) RETURNING id;",
                    (ano, f"Orçamento {ano}")
                )
                oa_id = cur.fetchone()[0]

            # 2. Obter ou criar orcamento_mensal
            cur.execute(
                "SELECT id FROM orcamentos_mensais WHERE orcamento_anual_id = %s AND mes = %s;",
                (oa_id, mes)
            )
            om = cur.fetchone()
            if om:
                om_id = om[0]
            else:
                cur.execute(
                    "INSERT INTO orcamentos_mensais (orcamento_anual_id, mes, valor) "
                    "VALUES (%s, %s, 0) RETURNING id;",
                    (oa_id, mes)
                )
                om_id = cur.fetchone()[0]

            # 3. Atualizar despesa
            cur.execute(
                """
                UPDATE despesas
                SET descricao = %s,
                    valor = %s,
                    data_compra = %s,
                    setor_id = %s,
                    fornecedor_id = %s,
                    rubrica_id = %s,
                    destino = %s,
                    orcamento_mensal_id = %s
                WHERE id = %s
                RETURNING id, descricao, valor, data_compra, setor_id, fornecedor_id, rubrica_id, destino;
                """,
                (descricao, valor, dt, setor_id, fornecedor_id, categoria_id, destino, om_id, despesa_id)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Despesa não encontrada para atualização.")
            conn.commit()

            return {
                "id": row[0],
                "descricao": row[1],
                "valor": float(row[2]),
                "data_compra": row[3].strftime("%Y-%m-%d"),
                "setor_id": row[4],
                "fornecedor_id": row[5],
                "categoria_id": row[6],
                "destino": row[7],
                "orcamento_mensal_id": om_id,
            }


def excluir_despesa(despesa_id: int) -> dict:
    """Exclui uma única despesa pelo ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM despesas WHERE id = %s RETURNING id, descricao, valor;", (despesa_id,))
            r = cur.fetchone()
            if not r:
                raise ValueError("Despesa não encontrada.")
            conn.commit()
            return {"id": r[0], "descricao": r[1], "valor": float(r[2])}


def limpar_todas_despesas() -> int:
    """Remove todas as despesas cadastradas no sistema. Retorna a quantidade de registros apagados."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM despesas;")
            total = cur.fetchone()[0]

            cur.execute("DELETE FROM despesas;")
            conn.commit()
            return total


# ── Autenticação de Usuários ──────────────────────────────────────────────────

def buscar_usuario_por_username(username: str) -> dict | None:
    """Retorna o dict do usuário pelo username, ou None se não encontrado / inativo."""
    query = """
        SELECT id, username, senha_hash, nome_completo, tipo, ativo
        FROM usuarios
        WHERE username = %s AND ativo = true
        LIMIT 1;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (username,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "username": row[1],
                    "senha_hash": row[2],
                    "nome_completo": row[3],
                    "tipo": row[4],
                    "ativo": row[5],
                }
    except Exception as e:
        log.error(f"Erro ao buscar usuário '{username}': {e}")
        return None


def buscar_usuario_por_username_por_id(user_id: int) -> dict | None:
    """Retorna o dict do usuário pelo ID (usado pelo user_loader do flask-login)."""
    query = """
        SELECT id, username, senha_hash, nome_completo, tipo, ativo
        FROM usuarios
        WHERE id = %s AND ativo = true
        LIMIT 1;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "username": row[1],
                    "senha_hash": row[2],
                    "nome_completo": row[3],
                    "tipo": row[4],
                    "ativo": row[5],
                }
    except Exception as e:
        log.error(f"Erro ao buscar usuário ID={user_id}: {e}")
        return None


def verificar_senha(senha_plain: str, senha_hash: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash bcrypt armazenado."""
    try:
        return bcrypt.checkpw(senha_plain.encode("utf-8"), senha_hash.encode("utf-8"))
    except Exception as e:
        log.error(f"Erro ao verificar senha: {e}")
        return False


def _hash_senha(nova_senha: str) -> str:
    """Gera hash bcrypt (cost 12) após validar o tamanho mínimo."""
    if len(nova_senha) < 8:
        raise ValueError("A nova senha deve ter pelo menos 8 caracteres.")
    return bcrypt.hashpw(nova_senha.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def atualizar_ultimo_acesso(user_id: int) -> None:
    """Registra o timestamp do último acesso bem-sucedido do usuário."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE usuarios SET ultimo_acesso = now() WHERE id = %s;",
                    (user_id,)
                )
                conn.commit()
    except Exception as e:
        log.error(f"Erro ao atualizar último acesso (user_id={user_id}): {e}")


def trocar_senha(user_id: int, nova_senha: str) -> None:
    """Gera novo hash bcrypt e atualiza a senha do usuário no banco."""
    novo_hash = _hash_senha(nova_senha)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE usuarios SET senha_hash = %s WHERE id = %s;",
                    (novo_hash, user_id)
                )
                conn.commit()
    except Exception as e:
        log.error(f"Erro ao trocar senha (user_id={user_id}): {e}")
        raise


def redefinir_senha_por_username(username: str, nova_senha: str) -> dict:
    """
    Redefine a senha sem exigir a senha atual (recuperação via CLI).
    Reativa a conta se estiver inativa. Não registra a senha em log.
    """
    username = (username or "").strip()
    if not username:
        raise ValueError("Informe o nome de usuário.")
    novo_hash = _hash_senha(nova_senha)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE usuarios
                       SET senha_hash = %s,
                           ativo = true
                     WHERE username = %s
                 RETURNING id, username, tipo;
                    """,
                    (novo_hash, username),
                )
                row = cur.fetchone()
                conn.commit()
                if not row:
                    raise ValueError(f"Usuário '{username}' não encontrado.")
                return {"id": row[0], "username": row[1], "tipo": row[2]}
    except ValueError:
        raise
    except Exception as e:
        log.error(f"Erro ao redefinir senha do usuário '{username}': {e}")
        raise