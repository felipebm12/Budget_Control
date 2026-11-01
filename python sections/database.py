import calendar
from contextlib import contextmanager
import json
import logging
import math
import threading
import time
from datetime import datetime, date
from decimal import Decimal
import psycopg2
from psycopg2 import pool
import bcrypt
import config


log = logging.getLogger(__name__)

# ── Pool de Conexões e Cache Leve de Sessão ──────────────────────────────────
_db_pool: pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()

_user_cache: dict[int, tuple[float, dict]] = {}
_user_cache_lock = threading.Lock()
_USER_CACHE_TTL = 30.0  # segundos

# Hash constante para mitigar enumeração de usuários via Timing Attack no login
_DUMMY_BCRYPT_HASH = "$2b$12$TSRXe0YOedg7P3hEyYPT..opCzIbv2A8d1ahBhCXwJ1kK.3bDLihS"


def _obter_pool() -> pool.ThreadedConnectionPool:
    """Inicializa sob demanda (lazy) e retorna o pool thread-safe de conexões PostgreSQL."""
    global _db_pool
    if _db_pool is None:
        with _pool_lock:
            if _db_pool is None:
                _db_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=15,
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    dbname=config.DB_NAME,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    sslmode="require",
                    connect_timeout=30,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5,
                )
    return _db_pool


def invalidar_cache_usuario(user_id: int | None = None) -> None:
    """Remove um usuário específico (ou todos) do cache em memória do user_loader."""
    with _user_cache_lock:
        if user_id is None:
            _user_cache.clear()
        else:
            _user_cache.pop(int(user_id), None)


def _validar_valor_monetario(valor: float, permitir_zero: bool = False) -> float:
    """Garante que o valor numérico seja finito (não NaN/Inf) e dentro de limites válidos."""
    try:
        num = float(valor)
    except (ValueError, TypeError):
        raise ValueError("Valor numérico inválido.")
    if not math.isfinite(num):
        raise ValueError("Valor numérico inválido.")
    if permitir_zero:
        if num < 0:
            raise ValueError("O valor não pode ser negativo.")
    else:
        if num <= 0:
            raise ValueError("O valor deve ser maior que zero.")
    if num > 999_999_999.99:
        raise ValueError("O valor informado excede o limite máximo permitido.")
    return round(num, 2)


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
        return "Perto do orçamento"
    return "Dentro do orçamento"


@contextmanager
def get_db_connection():
    """Obtém uma conexão do pool PostgreSQL/Supabase e a devolve automaticamente ao final do bloco."""
    db_pool = _obter_pool()
    conn = db_pool.getconn()
    try:
        if conn.closed:
            db_pool.putconn(conn, close=True)
            conn = db_pool.getconn()
        yield conn
        if not conn.closed:
            conn.commit()
    except Exception:
        if not conn.closed:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn is not None:
            db_pool.putconn(conn, close=bool(conn.closed))


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


def buscar_listas_auxiliares() -> dict:
    """
    Carrega setores, fornecedores e categorias utilizando uma única conexão do pool,
    evitando 3 round-trips independentes de conexão quando o dashboard inicializa.
    """
    q_setores = """
        SELECT s.id, s.nome, COALESCE(s.descricao, '') AS descricao,
               COUNT(d.id) AS total_despesas, COALESCE(SUM(d.valor), 0) AS total_gasto
        FROM setores s
        LEFT JOIN despesas d ON d.setor_id = s.id
        GROUP BY s.id, s.nome, s.descricao
        ORDER BY s.nome ASC;
    """
    q_fornecedores = """
        SELECT f.id, f.nome, COALESCE(f.descricao, '') AS descricao,
               COUNT(d.id) AS total_despesas, COALESCE(SUM(d.valor), 0) AS total_gasto
        FROM fornecedores f
        LEFT JOIN despesas d ON d.fornecedor_id = f.id
        GROUP BY f.id, f.nome, f.descricao
        ORDER BY f.nome ASC;
    """
    q_categorias = """
        SELECT r.id, r.nome, COALESCE(r.descricao, '') AS descricao,
               COUNT(d.id) AS total_despesas, COALESCE(SUM(d.valor), 0) AS total_gasto
        FROM rubricas r
        LEFT JOIN despesas d ON d.rubrica_id = r.id
        GROUP BY r.id, r.nome, r.descricao
        ORDER BY r.nome ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(q_setores)
                setores = [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "descricao": r[2],
                        "total_despesas": r[3],
                        "total_gasto": float(r[4]),
                        "total_gasto_fmt": _fmt_moeda(r[4]),
                    }
                    for r in cur.fetchall()
                ]

                cur.execute(q_fornecedores)
                fornecedores = [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "descricao": r[2],
                        "total_despesas": r[3],
                        "total_gasto": float(r[4]),
                        "total_gasto_fmt": _fmt_moeda(r[4]),
                    }
                    for r in cur.fetchall()
                ]

                cur.execute(q_categorias)
                categorias = [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "descricao": r[2],
                        "total_despesas": r[3],
                        "total_gasto": float(r[4]),
                        "total_gasto_fmt": _fmt_moeda(r[4]),
                    }
                    for r in cur.fetchall()
                ]

                return {
                    "setores": setores,
                    "fornecedores": fornecedores,
                    "categorias": categorias,
                }
    except Exception as e:
        log.error(f"Erro ao buscar listas auxiliares consolidadas: {e}")
        return {"setores": [], "fornecedores": [], "categorias": []}


# ── Orçamentos por Setor (orcamentos_setores) ─────────────────────────────────

def buscar_orcamentos_setor(setor_id: int, ano: int) -> list[dict]:
    """
    Retorna os 12 meses do ano para o setor informado, incluindo valor orçado
    e total gasto real para comparação. Meses sem registro retornam valor=0.
    Usa intervalo SARGable de datas para aproveitar idx_despesas_setor_data.
    """
    query = """
        WITH meses AS (
            SELECT generate_series(1, 12) AS mes
        ),
        gastos_mes AS (
            SELECT
                EXTRACT(MONTH FROM d.data_compra)::integer AS mes,
                COALESCE(SUM(d.valor), 0) AS gasto_real
            FROM despesas d
            WHERE d.setor_id = %s
              AND d.data_compra >= make_date(%s, 1, 1)
              AND d.data_compra <= make_date(%s, 12, 31)
            GROUP BY EXTRACT(MONTH FROM d.data_compra)::integer
        )
        SELECT
            m.mes,
            COALESCE(os.valor, 0) AS valor_orcado,
            COALESCE(gm.gasto_real, 0) AS gasto_real,
            os.id AS orcamento_id
        FROM meses m
        LEFT JOIN orcamentos_setores os
            ON os.setor_id = %s AND os.ano = %s AND os.mes = m.mes
        LEFT JOIN gastos_mes gm
            ON gm.mes = m.mes
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
    valor = _validar_valor_monetario(valor, permitir_zero=True)
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
    valor = _validar_valor_monetario(valor, permitir_zero=True)

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
    Usa CTEs pré-agregadas para evitar produto cartesiano entre orcamentos_setores e despesas.
    """
    query = """
        WITH orc_ano AS (
            SELECT setor_id, COALESCE(SUM(valor), 0) AS total_orcado
            FROM orcamentos_setores
            WHERE ano = %s
            GROUP BY setor_id
        ),
        desp_ano AS (
            SELECT setor_id, COALESCE(SUM(valor), 0) AS total_gasto
            FROM despesas
            WHERE data_compra >= make_date(%s, 1, 1)
              AND data_compra <= make_date(%s, 12, 31)
            GROUP BY setor_id
        )
        SELECT
            s.id AS setor_id,
            s.nome AS setor_nome,
            COALESCE(o.total_orcado, 0) AS total_orcado,
            COALESCE(d.total_gasto, 0) AS total_gasto
        FROM setores s
        LEFT JOIN orc_ano o ON o.setor_id = s.id
        LEFT JOIN desp_ano d ON d.setor_id = s.id
        ORDER BY s.nome ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (ano, ano, ano))
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
    com suporte a filtros por setor, fornecedor e categoria, usando CTEs pré-agregadas.
    """
    query = """
        WITH meses_periodo AS (
            SELECT generate_series(
                date_trunc('month', %s::date),
                date_trunc('month', %s::date),
                interval '1 month'
            )::date AS inicio_mes
        ),
        orcamento_por_mes AS (
            SELECT
                os.ano,
                os.mes,
                COALESCE(SUM(os.valor), 0) AS valor_orcado
            FROM orcamentos_setores os
            WHERE (%s::integer IS NULL OR os.setor_id = %s::integer)
            GROUP BY os.ano, os.mes
        ),
        gasto_por_mes AS (
            SELECT
                date_trunc('month', d.data_compra)::date AS inicio_mes,
                COALESCE(SUM(d.valor), 0) AS gasto_mensal
            FROM despesas d
            WHERE d.data_compra >= %s::date
              AND d.data_compra <= %s::date
              AND (%s::integer IS NULL OR d.setor_id = %s::integer)
              AND (%s::integer IS NULL OR d.fornecedor_id = %s::integer)
              AND (%s::integer IS NULL OR d.rubrica_id = %s::integer)
            GROUP BY date_trunc('month', d.data_compra)::date
        ),
        alerta_por_ano AS (
            SELECT ano, MAX(percentual_alerta) AS percentual_alerta
            FROM orcamentos_anuais
            GROUP BY ano
        )
        SELECT
            EXTRACT(YEAR FROM m.inicio_mes)::integer AS ano,
            EXTRACT(MONTH FROM m.inicio_mes)::integer AS mes,
            COALESCE(oc.valor_orcado, 0) AS orcado_mensal,
            COALESCE(gm.gasto_mensal, 0) AS gasto_mensal,
            COALESCE(ROUND((COALESCE(gm.gasto_mensal, 0) / NULLIF(COALESCE(oc.valor_orcado, 0), 0)) * 100, 2), 0) AS percentual_utilizado,
            CASE
                WHEN COALESCE(oc.valor_orcado, 0) = 0 AND COALESCE(gm.gasto_mensal, 0) > 0 THEN 'Acima do orçamento'
                WHEN (COALESCE(gm.gasto_mensal, 0) / NULLIF(COALESCE(oc.valor_orcado, 0), 0)) * 100 >= 100 THEN 'Acima do orçamento'
                WHEN (COALESCE(gm.gasto_mensal, 0) / NULLIF(COALESCE(oc.valor_orcado, 0), 0)) * 100 >= 80 THEN 'Perto do orçamento'
                ELSE 'Dentro do orçamento'
            END AS status,
            COALESCE(oa.percentual_alerta, 80) AS pct_alerta
        FROM meses_periodo m
        LEFT JOIN orcamento_por_mes oc
            ON oc.ano = EXTRACT(YEAR FROM m.inicio_mes)::integer
           AND oc.mes = EXTRACT(MONTH FROM m.inicio_mes)::integer
        LEFT JOIN gasto_por_mes gm
            ON gm.inicio_mes = m.inicio_mes
        LEFT JOIN alerta_por_ano oa
            ON oa.ano = EXTRACT(YEAR FROM m.inicio_mes)::integer
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
    filtro_ano = int(ano or config.ANO_FILTRO)
    if mes and 1 <= int(mes) <= 12:
        mes_int = int(mes)
        ultimo_dia = calendar.monthrange(filtro_ano, mes_int)[1]
        dt_inicio = f"{filtro_ano}-{mes_int:02d}-01"
        dt_fim = f"{filtro_ano}-{mes_int:02d}-{ultimo_dia:02d}"
    else:
        dt_inicio = f"{filtro_ano}-01-01"
        dt_fim = f"{filtro_ano}-12-31"

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
               EXTRACT(MONTH FROM d.data_compra)::integer AS mes,
               EXTRACT(YEAR FROM d.data_compra)::integer AS ano_compra,
               d.setor_id,
               d.fornecedor_id,
               d.rubrica_id AS categoria_id
        FROM despesas d
        LEFT JOIN setores s ON s.id = d.setor_id
        LEFT JOIN fornecedores f ON f.id = d.fornecedor_id
        LEFT JOIN rubricas r ON r.id = d.rubrica_id
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
    filtro_ano = int(ano or config.ANO_FILTRO)
    if mes and 1 <= int(mes) <= 12:
        mes_int = int(mes)
        ultimo_dia = calendar.monthrange(filtro_ano, mes_int)[1]
        dt_inicio = f"{filtro_ano}-{mes_int:02d}-01"
        dt_fim = f"{filtro_ano}-{mes_int:02d}-{ultimo_dia:02d}"
    else:
        dt_inicio = f"{filtro_ano}-01-01"
        dt_fim = f"{filtro_ano}-12-31"
    return buscar_despesas_periodo(dt_inicio, dt_fim)


def _obter_ou_criar_orcamento_mensal_id(cur, ano: int, mes: int) -> int:
    """Obtém ou cria o orcamento_mensal_id para (ano, mes) de forma otimizada."""
    cur.execute(
        """
        SELECT om.id, oa.id
        FROM orcamentos_anuais oa
        LEFT JOIN orcamentos_mensais om
               ON om.orcamento_anual_id = oa.id AND om.mes = %s
        WHERE oa.ano = %s
        ORDER BY oa.id ASC
        LIMIT 1;
        """,
        (mes, ano),
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        return row[0]

    if row and row[1] is not None:
        oa_id = row[1]
    else:
        cur.execute(
            "INSERT INTO orcamentos_anuais (ano, valor_orcado, percentual_alerta, descricao) "
            "VALUES (%s, 0, 80, %s) RETURNING id;",
            (ano, f"Orçamento {ano}"),
        )
        oa_id = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO orcamentos_mensais (orcamento_anual_id, mes, valor)
        VALUES (%s, %s, 0)
        ON CONFLICT (orcamento_anual_id, mes) DO UPDATE SET valor = orcamentos_mensais.valor
        RETURNING id;
        """,
        (oa_id, mes),
    )
    return cur.fetchone()[0]


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
    valor = _validar_valor_monetario(valor, permitir_zero=False)
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
            om_id = _obter_ou_criar_orcamento_mensal_id(cur, ano, mes)

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
    valor = _validar_valor_monetario(valor, permitir_zero=False)
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
            om_id = _obter_ou_criar_orcamento_mensal_id(cur, ano, mes)

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
    """Remove todas as despesas cadastradas no sistema em uma única operação. Retorna a quantidade apagada."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM despesas;")
            total = cur.rowcount or 0
            conn.commit()
            return total


# ── Autenticação e Permissões de Usuários ────────────────────────────────────

# Catálogo de permissões granulares para usuários do tipo 'usuario'
# Administradores ('admin') possuem automaticamente todas as permissões = True.
PERMISSOES_PADRAO_USUARIO: dict[str, bool] = {
    "despesas_criar": True,
    "despesas_editar": True,
    "despesas_excluir": True,
    "setores_gerenciar": False,
    "fornecedores_gerenciar": False,
    "categorias_gerenciar": False,
    "orcamentos_editar": False,
    "relatorios_exportar": True,
}

_schema_permissoes_ok = False
_schema_permissoes_lock = threading.Lock()


def normalizar_permissoes(permissoes_raw: dict | str | None, tipo: str = "usuario") -> dict[str, bool]:
    """
    Normaliza o dicionário de permissões garantindo todas as chaves conhecidas.
    Para perfil 'admin', todas as permissões são sempre True.
    """
    if (tipo or "").strip().lower() == "admin":
        return {k: True for k in PERMISSOES_PADRAO_USUARIO}

    parsed: dict = {}
    if isinstance(permissoes_raw, str) and permissoes_raw.strip():
        try:
            obj = json.loads(permissoes_raw)
            if isinstance(obj, dict):
                parsed = obj
        except Exception:
            parsed = {}
    elif isinstance(permissoes_raw, dict):
        parsed = permissoes_raw

    resultado: dict[str, bool] = {}
    for chave, valor_padrao in PERMISSOES_PADRAO_USUARIO.items():
        if chave in parsed:
            resultado[chave] = bool(parsed[chave])
        else:
            resultado[chave] = bool(valor_padrao)
    return resultado


def _garantir_coluna_permissoes() -> None:
    """Garante de forma transparente e idempotente que a coluna 'permissoes' exista na tabela 'usuarios'."""
    global _schema_permissoes_ok
    if _schema_permissoes_ok:
        return
    with _schema_permissoes_lock:
        if _schema_permissoes_ok:
            return
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS permissoes jsonb NOT NULL DEFAULT '{}'::jsonb;"
                    )
                    conn.commit()
            _schema_permissoes_ok = True
        except Exception as e:
            log.warning(f"Não foi possível verificar/criar coluna 'permissoes' em usuarios: {e}")


def buscar_usuario_por_username(username: str) -> dict | None:
    """Retorna o dict do usuário pelo username, ou None se não encontrado / inativo."""
    _garantir_coluna_permissoes()
    query = """
        SELECT id, username, senha_hash, nome_completo, tipo, ativo, COALESCE(permissoes, '{}'::jsonb)
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
                tipo = row[4]
                return {
                    "id": row[0],
                    "username": row[1],
                    "senha_hash": row[2],
                    "nome_completo": row[3],
                    "tipo": tipo,
                    "ativo": row[5],
                    "permissoes": normalizar_permissoes(row[6], tipo),
                }
    except Exception as e:
        log.error(f"Erro ao buscar usuário '{username}': {e}")
        return None


def buscar_usuario_por_username_por_id(user_id: int) -> dict | None:
    """
    Retorna o dict do usuário pelo ID (usado pelo user_loader do flask-login).
    Utiliza cache em memória de curta duração (TTL=30s) invalidado imediatamente em edições/exclusões,
    evitando consultas repetidas ao banco em cada requisição de página/API.
    """
    uid = int(user_id)
    agora = time.monotonic()
    with _user_cache_lock:
        cached = _user_cache.get(uid)
        if cached and (agora - cached[0]) < _USER_CACHE_TTL:
            copia = dict(cached[1])
            copia["permissoes"] = dict(cached[1].get("permissoes", {}))
            return copia

    _garantir_coluna_permissoes()
    query = """
        SELECT id, username, senha_hash, nome_completo, tipo, ativo, COALESCE(permissoes, '{}'::jsonb)
        FROM usuarios
        WHERE id = %s AND ativo = true
        LIMIT 1;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (uid,))
                row = cur.fetchone()
                if not row:
                    invalidar_cache_usuario(uid)
                    return None
                tipo = row[4]
                dados = {
                    "id": row[0],
                    "username": row[1],
                    "senha_hash": row[2],
                    "nome_completo": row[3],
                    "tipo": tipo,
                    "ativo": row[5],
                    "permissoes": normalizar_permissoes(row[6], tipo),
                }
                with _user_cache_lock:
                    _user_cache[uid] = (time.monotonic(), dados)
                copia = dict(dados)
                copia["permissoes"] = dict(dados["permissoes"])
                return copia
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


def verificar_senha_dummy(senha_plain: str) -> None:
    """Executa bcrypt.checkpw contra um hash constante para evitar enumeração por Timing Attack."""
    try:
        bcrypt.checkpw((senha_plain or "").encode("utf-8"), _DUMMY_BCRYPT_HASH.encode("utf-8"))
    except Exception:
        pass


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
        invalidar_cache_usuario(user_id)
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
                invalidar_cache_usuario(row[0])
                return {"id": row[0], "username": row[1], "tipo": row[2]}
    except ValueError:
        raise
    except Exception as e:
        log.error(f"Erro ao redefinir senha do usuário '{username}': {e}")
        raise


def buscar_usuarios() -> list[dict]:
    """Retorna a lista de usuários cadastrados (sem o hash de senha), incluindo suas permissões."""
    _garantir_coluna_permissoes()
    query = """
        SELECT id, username, nome_completo, tipo, ativo, criado_em, ultimo_acesso, COALESCE(permissoes, '{}'::jsonb)
        FROM usuarios
        ORDER BY nome_completo ASC, username ASC;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "username": r[1],
                        "nome_completo": r[2],
                        "tipo": r[3],
                        "ativo": r[4],
                        "criado_em": r[5].strftime("%d/%m/%Y %H:%M") if r[5] else "",
                        "ultimo_acesso": r[6].strftime("%d/%m/%Y %H:%M") if r[6] else "Nunca acessou",
                        "permissoes": normalizar_permissoes(r[7], r[3]),
                    }
                    for r in rows
                ]
    except Exception as e:
        log.error(f"Erro ao buscar usuários: {e}")
        return []


def cadastrar_usuario(
    username: str,
    senha_plain: str,
    nome_completo: str,
    tipo: str = "usuario",
    permissoes: dict | None = None,
) -> dict:
    """Cadastra um novo usuário no banco com senha criptografada via bcrypt e permissões granulares."""
    import re
    _garantir_coluna_permissoes()
    username = (username or "").strip().lower()
    nome_completo = (nome_completo or "").strip()
    tipo = (tipo or "usuario").strip().lower()

    if not username or len(username) < 3:
        raise ValueError("O login deve ter pelo menos 3 caracteres.")
    if not re.match(r"^[a-z0-9]+$", username):
        raise ValueError("O login deve conter apenas letras e números (sem símbolos ou espaços).")
    if not nome_completo:
        raise ValueError("O nome completo é obrigatório.")
    if tipo not in ("admin", "usuario"):
        raise ValueError("O perfil deve ser 'admin' ou 'usuario'.")

    novo_hash = _hash_senha(senha_plain)
    perms_norm = normalizar_permissoes(permissoes, tipo)

    query = """
        INSERT INTO usuarios (username, senha_hash, nome_completo, tipo, ativo, permissoes)
        VALUES (%s, %s, %s, %s, true, %s::jsonb)
        RETURNING id, username, nome_completo, tipo, ativo, criado_em, COALESCE(permissoes, '{}'::jsonb);
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (username, novo_hash, nome_completo, tipo, json.dumps(perms_norm)))
                r = cur.fetchone()
                conn.commit()
                return {
                    "id": r[0],
                    "username": r[1],
                    "nome_completo": r[2],
                    "tipo": r[3],
                    "ativo": r[4],
                    "criado_em": r[5].strftime("%d/%m/%Y %H:%M") if r[5] else "",
                    "ultimo_acesso": "Nunca acessou",
                    "permissoes": normalizar_permissoes(r[6], r[3]),
                }
    except psycopg2.IntegrityError:
        raise ValueError(f"O nome de usuário '{username}' já está em uso.")
    except Exception as e:
        log.error(f"Erro ao cadastrar usuário: {e}")
        raise


def atualizar_usuario(
    user_id: int,
    nome_completo: str,
    tipo: str,
    ativo: bool,
    current_user_id: int,
    permissoes: dict | None = None,
) -> dict:
    """Atualiza dados do usuário (nome, perfil, status ativo/inativo e opcionalmente permissões)."""
    _garantir_coluna_permissoes()
    nome_completo = (nome_completo or "").strip()
    tipo = (tipo or "usuario").strip().lower()

    if not nome_completo:
        raise ValueError("O nome completo é obrigatório.")
    if tipo not in ("admin", "usuario"):
        raise ValueError("Perfil inválido. Escolha 'admin' ou 'usuario'.")

    # Proteção: usuário logado não pode desativar a si mesmo nem remover seu perfil admin
    if user_id == current_user_id:
        if not ativo:
            raise ValueError("Você não pode desativar seu próprio usuário enquanto estiver conectado.")
        if tipo != "admin":
            raise ValueError("Você não pode remover seu próprio perfil de administrador.")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tipo, ativo, COALESCE(permissoes, '{}'::jsonb) FROM usuarios WHERE id = %s;",
                    (user_id,),
                )
                user_atual = cur.fetchone()
                if not user_atual:
                    raise ValueError("Usuário não encontrado.")

                # Se estiver desativando ou rebaixando um admin, garantir que ainda haja pelo menos 1 admin ativo
                if (not ativo or tipo != "admin") and user_atual[0] == "admin" and user_atual[1]:
                    cur.execute(
                        "SELECT COUNT(*) FROM usuarios WHERE tipo = 'admin' AND ativo = true AND id != %s;",
                        (user_id,),
                    )
                    outros_admins = cur.fetchone()[0]
                    if outros_admins == 0:
                        raise ValueError(
                            "Não é possível alterar este usuário: o sistema deve possuir pelo menos um administrador ativo."
                        )

                perms_base = permissoes if permissoes is not None else user_atual[2]
                perms_norm = normalizar_permissoes(perms_base, tipo)

                cur.execute(
                    """
                    UPDATE usuarios
                    SET nome_completo = %s,
                        tipo = %s,
                        ativo = %s,
                        permissoes = %s::jsonb
                    WHERE id = %s
                    RETURNING id, username, nome_completo, tipo, ativo, COALESCE(permissoes, '{}'::jsonb);
                    """,
                    (nome_completo, tipo, ativo, json.dumps(perms_norm), user_id),
                )
                r = cur.fetchone()
                conn.commit()
                invalidar_cache_usuario(user_id)
                return {
                    "id": r[0],
                    "username": r[1],
                    "nome_completo": r[2],
                    "tipo": r[3],
                    "ativo": r[4],
                    "permissoes": normalizar_permissoes(r[5], r[3]),
                }
    except ValueError:
        raise
    except Exception as e:
        log.error(f"Erro ao atualizar usuário ID={user_id}: {e}")
        raise


def atualizar_permissoes_usuario(user_id: int, permissoes: dict) -> dict:
    """Atualiza exclusivamente o conjunto de permissões granulares de um usuário."""
    _garantir_coluna_permissoes()
    if not isinstance(permissoes, dict):
        raise ValueError("Formato de permissões inválido.")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, tipo FROM usuarios WHERE id = %s;", (user_id,))
                u = cur.fetchone()
                if not u:
                    raise ValueError("Usuário não encontrado.")
                _, username, tipo = u[0], u[1], u[2]
                if tipo == "admin":
                    raise ValueError("Administradores possuem acesso total a todas as funcionalidades do sistema.")

                perms_norm = normalizar_permissoes(permissoes, tipo)
                cur.execute(
                    """
                    UPDATE usuarios
                    SET permissoes = %s::jsonb
                    WHERE id = %s
                    RETURNING id, username, nome_completo, tipo, ativo, COALESCE(permissoes, '{}'::jsonb);
                    """,
                    (json.dumps(perms_norm), user_id),
                )
                r = cur.fetchone()
                conn.commit()
                invalidar_cache_usuario(user_id)
                return {
                    "id": r[0],
                    "username": r[1],
                    "nome_completo": r[2],
                    "tipo": r[3],
                    "ativo": r[4],
                    "permissoes": normalizar_permissoes(r[5], r[3]),
                }
    except ValueError:
        raise
    except Exception as e:
        log.error(f"Erro ao atualizar permissões do usuário ID={user_id}: {e}")
        raise


def redefinir_senha_usuario_por_id(user_id: int, nova_senha: str) -> dict:
    """Redefine a senha de um usuário pelo seu ID."""
    novo_hash = _hash_senha(nova_senha)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE usuarios SET senha_hash = %s WHERE id = %s RETURNING id, username, tipo;",
                    (novo_hash, user_id)
                )
                r = cur.fetchone()
                if not r:
                    raise ValueError("Usuário não encontrado.")
                conn.commit()
                invalidar_cache_usuario(user_id)
                return {"id": r[0], "username": r[1], "tipo": r[2]}
    except ValueError:
        raise
    except Exception as e:
        log.error(f"Erro ao redefinir senha do usuário ID={user_id}: {e}")
        raise


def excluir_usuario(user_id: int, current_user_id: int) -> dict:
    """Exclui um usuário do sistema (com proteções de integridade)."""
    if user_id == current_user_id:
        raise ValueError("Você não pode excluir sua própria conta enquanto estiver conectado.")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, tipo FROM usuarios WHERE id = %s;", (user_id,))
            u = cur.fetchone()
            if not u:
                raise ValueError("Usuário não encontrado.")
            username, tipo = u[0], u[1]

            if tipo == "admin":
                cur.execute(
                    "SELECT COUNT(*) FROM usuarios WHERE tipo = 'admin' AND ativo = true AND id != %s;",
                    (user_id,)
                )
                outros = cur.fetchone()[0]
                if outros == 0:
                    raise ValueError("Não é possível excluir o único administrador ativo do sistema.")

            cur.execute("DELETE FROM usuarios WHERE id = %s;", (user_id,))
            conn.commit()
            invalidar_cache_usuario(user_id)
            return {"id": user_id, "username": username}