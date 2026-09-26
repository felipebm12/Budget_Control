import logging
import os
from functools import wraps
from pathlib import Path
from datetime import date, datetime
from flask import Flask, render_template, jsonify, request, send_file, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import database
import report

# ── Pastas do projeto ────────────────────────────────────────────────────────
_DIR_SCRIPT = Path(__file__).resolve().parent
_DIR_PROJETO = _DIR_SCRIPT.parent
PASTA_EXPORTACOES = _DIR_PROJETO / "Exportações"
PASTA_EXPORTACOES.mkdir(exist_ok=True)
PASTA_LOGS = _DIR_PROJETO / "Logs"
PASTA_LOGS.mkdir(exist_ok=True)
PASTA_ASSET = _DIR_SCRIPT / "asset"
PASTA_FONTES = _DIR_SCRIPT / "fonts"

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(32))

# ── Flask-Login ───────────────────────────────────────────────────────────────

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar o sistema."


class Usuario(UserMixin):
    """Representa o usuário autenticado na sessão Flask."""
    def __init__(self, data: dict):
        self.id = str(data["id"])
        self.username = data["username"]
        self.nome_completo = data["nome_completo"]
        self.tipo = data["tipo"]


@login_manager.user_loader
def load_user(user_id: str):
    """Callback do flask-login: recarrega o usuário pelo ID da sessão."""
    try:
        usuario = database.buscar_usuario_por_username_por_id(int(user_id))
        if usuario:
            return Usuario(usuario)
    except Exception:
        pass
    return None


# ── Rotas de Autenticação ────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    """Exibe e processa o formulário de login."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    erro = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        senha = request.form.get("senha") or ""

        usuario_data = database.buscar_usuario_por_username(username)
        if usuario_data and database.verificar_senha(senha, usuario_data["senha_hash"]):
            usuario_obj = Usuario(usuario_data)
            login_user(usuario_obj, remember=False)
            database.atualizar_ultimo_acesso(usuario_data["id"])
            log.info(f"Login bem-sucedido: {username}")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            erro = "Usuário ou senha incorretos."
            log.warning(f"Tentativa de login falhou para: '{username}'")

    return render_template("login.html", erro=erro)


@app.route("/logout")
@login_required
def logout():
    """Encerra a sessão do usuário."""
    log.info(f"Logout: {current_user.username}")
    logout_user()
    return redirect(url_for("login"))


@app.route("/api/trocar-senha", methods=["POST"])
@login_required
def api_trocar_senha():
    """Troca a senha do usuário autenticado."""
    data = request.get_json() or {}
    senha_atual = data.get("senha_atual") or ""
    nova_senha = data.get("nova_senha") or ""
    confirmar = data.get("confirmar") or ""

    if not senha_atual or not nova_senha:
        return jsonify({"erro": "Preencha todos os campos."}), 400
    if nova_senha != confirmar:
        return jsonify({"erro": "A nova senha e a confirmação não conferem."}), 400
    if len(nova_senha) < 8:
        return jsonify({"erro": "A nova senha deve ter pelo menos 8 caracteres."}), 400

    usuario_data = database.buscar_usuario_por_username(current_user.username)
    if not usuario_data or not database.verificar_senha(senha_atual, usuario_data["senha_hash"]):
        return jsonify({"erro": "Senha atual incorreta."}), 403

    try:
        database.trocar_senha(int(current_user.id), nova_senha)
        log.info(f"Senha alterada: {current_user.username}")
        return jsonify({"sucesso": True, "mensagem": "Senha alterada com sucesso!"})
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        log.error(f"Erro ao trocar senha: {e}")
        return jsonify({"erro": "Erro interno ao alterar senha."}), 500


def admin_required(f):
    """Garante que apenas usuários do tipo 'admin' acessem o recurso."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.tipo != "admin":
            return jsonify({"erro": "Acesso negado. Apenas administradores podem executar esta ação."}), 403
        return f(*args, **kwargs)
    return decorated_function


# ── Gestão de Usuários (Administrador) ───────────────────────────────────────

@app.route("/api/usuarios", methods=["GET"])
@login_required
@admin_required
def api_buscar_usuarios():
    """Retorna lista de todos os usuários cadastrados."""
    try:
        usuarios = database.buscar_usuarios()
        return jsonify(usuarios)
    except Exception as e:
        log.error(f"Erro ao listar usuários: {e}")
        return jsonify({"erro": "Falha ao consultar usuários."}), 500


@app.route("/api/usuarios", methods=["POST"])
@login_required
@admin_required
def api_cadastrar_usuario():
    """Cadastra um novo usuário no sistema."""
    dados = request.get_json() or {}
    username = dados.get("username", "")
    senha = dados.get("senha", "")
    nome_completo = dados.get("nome_completo", "")
    tipo = dados.get("tipo", "usuario")

    try:
        novo = database.cadastrar_usuario(username, senha, nome_completo, tipo)
        log.info(f"Usuário criado por {current_user.username}: {novo['username']} ({novo['tipo']})")
        return jsonify({"sucesso": True, "usuario": novo, "mensagem": f"Usuário '{novo['username']}' cadastrado com sucesso!"}), 201
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        log.error(f"Erro ao cadastrar usuário: {e}")
        return jsonify({"erro": "Falha interna ao cadastrar usuário."}), 500


@app.route("/api/usuarios/<int:user_id>", methods=["PUT"])
@login_required
@admin_required
def api_atualizar_usuario(user_id: int):
    """Atualiza dados do usuário (nome, perfil e status ativo/inativo)."""
    dados = request.get_json() or {}
    nome_completo = dados.get("nome_completo", "")
    tipo = dados.get("tipo", "usuario")
    ativo = bool(dados.get("ativo", True))

    try:
        atualizado = database.atualizar_usuario(user_id, nome_completo, tipo, ativo, int(current_user.id))
        log.info(f"Usuário ID={user_id} atualizado por {current_user.username}: {atualizado['username']}")
        return jsonify({"sucesso": True, "usuario": atualizado, "mensagem": "Usuário atualizado com sucesso!"})
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        log.error(f"Erro ao atualizar usuário ID={user_id}: {e}")
        return jsonify({"erro": "Falha interna ao atualizar usuário."}), 500


@app.route("/api/usuarios/<int:user_id>/senha", methods=["PUT"])
@login_required
@admin_required
def api_redefinir_senha_usuario(user_id: int):
    """Redefine a senha de um usuário pelo administrador."""
    dados = request.get_json() or {}
    nova_senha = dados.get("nova_senha", "")
    confirmar = dados.get("confirmar", "")

    if not nova_senha:
        return jsonify({"erro": "Informe a nova senha."}), 400
    if nova_senha != confirmar:
        return jsonify({"erro": "A nova senha e a confirmação não conferem."}), 400
    if len(nova_senha) < 8:
        return jsonify({"erro": "A nova senha deve ter pelo menos 8 caracteres."}), 400

    try:
        resultado = database.redefinir_senha_usuario_por_id(user_id, nova_senha)
        log.info(f"Senha do usuário {resultado['username']} redefinida por {current_user.username}")
        return jsonify({"sucesso": True, "mensagem": f"Senha de '{resultado['username']}' redefinida com sucesso!"})
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        log.error(f"Erro ao redefinir senha do usuário ID={user_id}: {e}")
        return jsonify({"erro": "Falha interna ao redefinir senha."}), 500


@app.route("/api/usuarios/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def api_excluir_usuario(user_id: int):
    """Exclui um usuário do sistema."""
    try:
        resultado = database.excluir_usuario(user_id, int(current_user.id))
        log.info(f"Usuário {resultado['username']} excluído por {current_user.username}")
        return jsonify({"sucesso": True, "mensagem": f"Usuário '{resultado['username']}' excluído com sucesso!"})
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        log.error(f"Erro ao excluir usuário ID={user_id}: {e}")
        return jsonify({"erro": "Falha interna ao excluir usuário."}), 500


# ── Rotas de Páginas ─────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    """Renderiza o Dashboard principal."""
    return render_template("index.html", usuario=current_user)


@app.route("/favicon.ico")
def favicon():
    """Serve o ícone da aba a partir de asset/favicon.png."""
    return send_from_directory(PASTA_ASSET, "favicon.png", mimetype="image/png")


@app.route("/fonts/<path:nome_arquivo>")
def fonte(nome_arquivo: str):
    """Serve as fontes locais utilizadas pela interface."""
    return send_from_directory(PASTA_FONTES, nome_arquivo)


# ── Setores (Departamentos / Centros de Custo) ────────────────────────────────

@app.route("/api/setores", methods=["GET", "POST"])
@login_required
def api_setores():
    """GET: Lista todos os setores. POST: Cadastra novo setor."""
    if request.method == "POST":
        data = request.get_json() or {}
        nome = (data.get("nome") or "").strip()
        descricao = (data.get("descricao") or "").strip()

        if not nome:
            return jsonify({"erro": "O nome do setor é obrigatório."}), 400

        try:
            setor = database.cadastrar_setor(nome, descricao)
            return jsonify({"sucesso": True, "setor": setor}), 201
        except Exception as e:
            log.error(f"Erro ao cadastrar setor: {e}")
            return jsonify({"erro": str(e)}), 400

    try:
        setores = database.buscar_setores()
        return jsonify({"setores": setores})
    except Exception as e:
        log.error(f"Erro ao buscar setores: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/api/setores/<int:setor_id>", methods=["PUT", "DELETE"])
@login_required
def api_setor_item(setor_id: int):
    """PUT: Atualiza setor. DELETE: Exclui setor (se desimpedido)."""
    if request.method == "PUT":
        data = request.get_json() or {}
        nome = (data.get("nome") or "").strip()
        descricao = (data.get("descricao") or "").strip()

        if not nome:
            return jsonify({"erro": "O nome do setor é obrigatório."}), 400

        try:
            setor = database.atualizar_setor(setor_id, nome, descricao)
            return jsonify({"sucesso": True, "setor": setor})
        except Exception as e:
            log.error(f"Erro ao atualizar setor: {e}")
            return jsonify({"erro": str(e)}), 400

    # DELETE
    try:
        resultado = database.excluir_setor(setor_id)
        return jsonify({"sucesso": True, "mensagem": f"Setor '{resultado['nome']}' excluído com sucesso."})
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        log.error(f"Erro ao excluir setor: {e}")
        return jsonify({"erro": str(e)}), 500


# ── Fornecedores (Onde foi gasto o dinheiro) ──────────────────────────────────

@app.route("/api/fornecedores", methods=["GET", "POST"])
@login_required
def api_fornecedores():
    """GET: Lista todos os fornecedores. POST: Cadastra novo fornecedor."""
    if request.method == "POST":
        data = request.get_json() or {}
        nome = (data.get("nome") or "").strip()
        descricao = (data.get("descricao") or "").strip()

        if not nome:
            return jsonify({"erro": "O nome do fornecedor é obrigatório."}), 400

        try:
            fornecedor = database.cadastrar_fornecedor(nome, descricao)
            return jsonify({"sucesso": True, "fornecedor": fornecedor}), 201
        except Exception as e:
            log.error(f"Erro ao cadastrar fornecedor: {e}")
            return jsonify({"erro": str(e)}), 400

    try:
        fornecedores = database.buscar_fornecedores()
        return jsonify({"fornecedores": fornecedores})
    except Exception as e:
        log.error(f"Erro ao buscar fornecedores: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/api/fornecedores/<int:fornecedor_id>", methods=["PUT", "DELETE"])
@login_required
def api_fornecedor_item(fornecedor_id: int):
    """PUT: Atualiza fornecedor. DELETE: Exclui fornecedor (se desimpedido)."""
    if request.method == "PUT":
        data = request.get_json() or {}
        nome = (data.get("nome") or "").strip()
        descricao = (data.get("descricao") or "").strip()

        if not nome:
            return jsonify({"erro": "O nome do fornecedor é obrigatório."}), 400

        try:
            fornecedor = database.atualizar_fornecedor(fornecedor_id, nome, descricao)
            return jsonify({"sucesso": True, "fornecedor": fornecedor})
        except Exception as e:
            log.error(f"Erro ao atualizar fornecedor: {e}")
            return jsonify({"erro": str(e)}), 400

    # DELETE
    try:
        resultado = database.excluir_fornecedor(fornecedor_id)
        return jsonify({"sucesso": True, "mensagem": f"Fornecedor '{resultado['nome']}' excluído com sucesso."})
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        log.error(f"Erro ao excluir fornecedor: {e}")
        return jsonify({"erro": str(e)}), 500


# ── Categorias (Rubricas) ────────────────────────────────────────────────────

@app.route("/api/categorias", methods=["GET", "POST"])
@app.route("/api/rubricas", methods=["GET", "POST"])
@login_required
def api_categorias():
    """GET: Retorna lista de categorias cadastradas. POST: Cadastra nova categoria."""
    if request.method == "POST":
        data = request.get_json() or {}
        nome = (data.get("nome") or "").strip()
        descricao = (data.get("descricao") or "").strip()

        if not nome:
            return jsonify({"erro": "O nome da categoria é obrigatório."}), 400

        try:
            categoria = database.cadastrar_categoria(nome, descricao)
            return jsonify({"sucesso": True, "categoria": categoria}), 201
        except Exception as e:
            log.error(f"Erro ao cadastrar categoria: {e}")
            return jsonify({"erro": str(e)}), 400

    try:
        categorias = database.buscar_categorias()
        return jsonify({"categorias": categorias, "destinos": categorias, "rubricas": categorias})
    except Exception as e:
        log.error(f"Erro em /api/categorias: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/api/categorias/<int:categoria_id>", methods=["PUT", "DELETE"])
@login_required
def api_categoria_item(categoria_id: int):
    """PUT: Atualiza categoria. DELETE: Exclui categoria (se desimpedida)."""
    if request.method == "PUT":
        data = request.get_json() or {}
        nome = (data.get("nome") or "").strip()
        descricao = (data.get("descricao") or "").strip()

        if not nome:
            return jsonify({"erro": "O nome da categoria é obrigatório."}), 400

        try:
            categoria = database.atualizar_categoria(categoria_id, nome, descricao)
            return jsonify({"sucesso": True, "categoria": categoria})
        except Exception as e:
            log.error(f"Erro ao atualizar categoria: {e}")
            return jsonify({"erro": str(e)}), 400

    # DELETE
    try:
        resultado = database.excluir_categoria(categoria_id)
        return jsonify({"sucesso": True, "mensagem": f"Categoria '{resultado['nome']}' excluída com sucesso."})
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        log.error(f"Erro ao excluir categoria: {e}")
        return jsonify({"erro": str(e)}), 500


# ── Despesas ─────────────────────────────────────────────────────────────────

@app.route("/api/despesas", methods=["GET", "POST"])
@login_required
def api_despesas():
    """GET: Lista despesas filtradas. POST: Cadastra nova despesa empresarial."""
    if request.method == "POST":
        data = request.get_json() or {}
        descricao = (data.get("descricao") or "").strip()
        data_compra = (data.get("data_compra") or "").strip()
        setor_id = data.get("setor_id")
        fornecedor_id = data.get("fornecedor_id")
        categoria_id = data.get("categoria_id") or data.get("rubrica_id")
        destino = (data.get("destino") or "").strip()

        try:
            valor = float(data.get("valor", 0))
        except (ValueError, TypeError):
            return jsonify({"erro": "Valor numérico inválido."}), 400

        if not descricao:
            return jsonify({"erro": "A descrição da despesa é obrigatória."}), 400
        if valor <= 0:
            return jsonify({"erro": "O valor da despesa deve ser maior que zero."}), 400
        if not data_compra:
            return jsonify({"erro": "A data da compra é obrigatória."}), 400
        if not setor_id:
            return jsonify({"erro": "Selecione o setor responsável."}), 400
        if not fornecedor_id:
            return jsonify({"erro": "Selecione o fornecedor."}), 400
        if not categoria_id:
            return jsonify({"erro": "Selecione a categoria da despesa."}), 400

        try:
            despesa = database.cadastrar_despesa(
                descricao=descricao,
                valor=valor,
                data_compra=data_compra,
                setor_id=int(setor_id),
                fornecedor_id=int(fornecedor_id),
                categoria_id=int(categoria_id),
                destino=destino
            )
            return jsonify({"sucesso": True, "despesa": despesa}), 201
        except Exception as e:
            log.error(f"Erro ao cadastrar despesa: {e}")
            return jsonify({"erro": str(e)}), 400

    # GET - Filtro dinâmico entre datas e parâmetros opcionais
    ano_atual = datetime.now().year
    data_inicio = request.args.get("data_inicio") or f"{ano_atual}-01-01"
    data_fim = request.args.get("data_fim") or f"{ano_atual}-12-31"

    setor_id = request.args.get("setor_id", type=int) or None
    fornecedor_id = request.args.get("fornecedor_id", type=int) or None
    categoria_id = request.args.get("categoria_id", type=int) or None

    try:
        despesas = database.buscar_despesas_periodo(
            data_inicio=data_inicio,
            data_fim=data_fim,
            setor_id=setor_id,
            fornecedor_id=fornecedor_id,
            categoria_id=categoria_id
        )
        total_gasto = sum(d["valor"] for d in despesas)
        return jsonify({
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "setor_id": setor_id,
            "fornecedor_id": fornecedor_id,
            "categoria_id": categoria_id,
            "despesas": despesas,
            "total_gasto": total_gasto,
            "total_gasto_fmt": database._fmt_moeda(total_gasto),
            "quantidade": len(despesas)
        })
    except Exception as e:
        log.error(f"Erro ao buscar despesas: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/api/despesas/<int:despesa_id>", methods=["PUT", "DELETE"])
@login_required
def api_despesa_item(despesa_id: int):
    """PUT: Atualiza lançamento de despesa. DELETE: Exclui despesa pelo ID."""
    if request.method == "PUT":
        data = request.get_json() or {}
        descricao = (data.get("descricao") or "").strip()
        data_compra = (data.get("data_compra") or "").strip()
        setor_id = data.get("setor_id")
        fornecedor_id = data.get("fornecedor_id")
        categoria_id = data.get("categoria_id") or data.get("rubrica_id")
        destino = (data.get("destino") or "").strip()

        try:
            valor = float(data.get("valor", 0))
        except (ValueError, TypeError):
            return jsonify({"erro": "Valor numérico inválido."}), 400

        if not descricao:
            return jsonify({"erro": "A descrição da despesa é obrigatória."}), 400
        if valor <= 0:
            return jsonify({"erro": "O valor da despesa deve ser maior que zero."}), 400
        if not data_compra:
            return jsonify({"erro": "A data da compra é obrigatória."}), 400
        if not setor_id:
            return jsonify({"erro": "Selecione o setor responsável."}), 400
        if not fornecedor_id:
            return jsonify({"erro": "Selecione o fornecedor."}), 400
        if not categoria_id:
            return jsonify({"erro": "Selecione a categoria da despesa."}), 400

        try:
            despesa = database.atualizar_despesa(
                despesa_id=despesa_id,
                descricao=descricao,
                valor=valor,
                data_compra=data_compra,
                setor_id=int(setor_id),
                fornecedor_id=int(fornecedor_id),
                categoria_id=int(categoria_id),
                destino=destino,
            )
            return jsonify({"sucesso": True, "despesa": despesa})
        except ValueError as ve:
            return jsonify({"erro": str(ve)}), 400
        except Exception as e:
            log.error(f"Erro ao atualizar despesa {despesa_id}: {e}")
            return jsonify({"erro": str(e)}), 500

    # DELETE
    try:
        resultado = database.excluir_despesa(despesa_id)
        return jsonify({
            "sucesso": True,
            "mensagem": f"Despesa '{resultado['descricao']}' ({database._fmt_moeda(resultado['valor'])}) excluída com sucesso."
        })
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 404
    except Exception as e:
        log.error(f"Erro ao excluir despesa {despesa_id}: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/api/despesas/limpar-todas", methods=["DELETE", "POST"])
@login_required
def api_despesas_limpar_todas():
    """Remove todas as despesas cadastradas no sistema."""
    try:
        total = database.limpar_todas_despesas()
        return jsonify({
            "sucesso": True,
            "total_removido": total,
            "mensagem": f"Todas as {total} despesas foram excluídas com sucesso."
        })
    except Exception as e:
        log.error(f"Erro ao limpar todas as despesas: {e}")
        return jsonify({"erro": str(e)}), 500


# ── Orçamentos por Setor ──────────────────────────────────────────────────────

@app.route("/api/orcamentos-setor", methods=["GET", "POST"])
@login_required
def api_orcamentos_setor():
    """
    GET  /api/orcamentos-setor?setor_id=X&ano=YYYY
         Retorna os 12 meses do ano com orçamento e gasto real por setor.
    POST /api/orcamentos-setor
         Body: { setor_id, ano, mes, valor }
         Upsert do orçamento de um mês específico de um setor.
    """
    if request.method == "POST":
        data = request.get_json() or {}
        setor_id = data.get("setor_id")
        ano = data.get("ano")
        mes = data.get("mes")
        aplicar_todos = data.get("aplicar_todos", False)
        valor_raw = data.get("valor")

        if not setor_id:
            return jsonify({"erro": "setor_id é obrigatório."}), 400
        if not ano:
            return jsonify({"erro": "ano é obrigatório."}), 400
        if not aplicar_todos and not mes:
            return jsonify({"erro": "mes é obrigatório quando não aplicar para todos."}), 400

        try:
            valor = float(valor_raw or 0)
        except (ValueError, TypeError):
            return jsonify({"erro": "Valor numérico inválido."}), 400

        try:
            if aplicar_todos or str(mes).lower() == "todos":
                resultado = database.salvar_orcamento_setor_todos(
                    setor_id=int(setor_id),
                    ano=int(ano),
                    valor=valor
                )
                return jsonify({"sucesso": True, "todos": True, "orcamentos": resultado}), 200
            else:
                resultado = database.salvar_orcamento_setor(
                    setor_id=int(setor_id),
                    ano=int(ano),
                    mes=int(mes),
                    valor=valor
                )
                return jsonify({"sucesso": True, "orcamento": resultado}), 200
        except ValueError as ve:
            return jsonify({"erro": str(ve)}), 400
        except Exception as e:
            log.error(f"Erro ao salvar orcamento do setor: {e}")
            return jsonify({"erro": str(e)}), 500

    # GET
    setor_id = request.args.get("setor_id", type=int)
    ano = request.args.get("ano", type=int) or datetime.now().year

    if not setor_id:
        return jsonify({"erro": "setor_id é obrigatório."}), 400

    try:
        meses = database.buscar_orcamentos_setor(setor_id=setor_id, ano=ano)
        total_orcado = sum(m["valor_orcado"] for m in meses)
        total_gasto = sum(m["gasto_real"] for m in meses)
        return jsonify({
            "setor_id": setor_id,
            "ano": ano,
            "meses": meses,
            "total_orcado": total_orcado,
            "total_orcado_fmt": database._fmt_moeda(total_orcado),
            "total_gasto": total_gasto,
            "total_gasto_fmt": database._fmt_moeda(total_gasto),
        })
    except Exception as e:
        log.error(f"Erro ao buscar orcamentos do setor: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/api/orcamentos-setor/resumo", methods=["GET"])
@login_required
def api_orcamentos_setor_resumo():
    """
    GET /api/orcamentos-setor/resumo?ano=YYYY
    Retorna resumo anual de orçamento × gasto real para todos os setores.
    """
    ano = request.args.get("ano", type=int) or datetime.now().year
    try:
        resumo = database.buscar_resumo_orcamentos_setores(ano=ano)
        return jsonify({"ano": ano, "setores": resumo})
    except Exception as e:
        log.error(f"Erro ao buscar resumo de orcamentos por setor: {e}")
        return jsonify({"erro": str(e)}), 500


# ── Dados Consolidados (Visão Resumida) ──────────────────────────────────────

@app.route("/api/dados")
@login_required
def api_dados():
    """Retorna dados consolidados mês a mês no intervalo de datas."""
    ano_atual = datetime.now().year
    data_inicio = request.args.get("data_inicio") or f"{ano_atual}-01-01"
    data_fim = request.args.get("data_fim") or f"{ano_atual}-12-31"

    setor_id = request.args.get("setor_id", type=int) or None
    fornecedor_id = request.args.get("fornecedor_id", type=int) or None
    categoria_id = request.args.get("categoria_id", type=int) or None

    try:
        meses = database.buscar_dados_periodo(
            data_inicio=data_inicio,
            data_fim=data_fim,
            setor_id=setor_id,
            fornecedor_id=fornecedor_id,
            categoria_id=categoria_id
        )
        total_orcado = sum(m["orcado"] for m in meses)
        total_gasto = sum(m["gasto"] for m in meses)
        saldo = total_orcado - total_gasto
        pct_geral = round((total_gasto / total_orcado * 100), 2) if total_orcado > 0 else 0

        return jsonify({
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "meses": meses,
            "total_orcado": total_orcado,
            "total_gasto": total_gasto,
            "saldo": saldo,
            "pct_geral": pct_geral,
        })
    except Exception as e:
        log.error(f"Erro em /api/dados: {e}")
        return jsonify({"erro": str(e)}), 500


# ── Rota de Exportação de PDF ────────────────────────────────────────────────

@app.route("/api/exportar-pdf")
@login_required
def api_exportar_pdf():
    """Gera e faz o download do arquivo PDF conforme o intervalo dinâmico de datas."""
    ano_atual = datetime.now().year
    data_inicio = request.args.get("data_inicio") or f"{ano_atual}-01-01"
    data_fim = request.args.get("data_fim") or f"{ano_atual}-12-31"
    visao = request.args.get("visao", "resumida").strip().lower()

    setor_id = request.args.get("setor_id", type=int) or None
    fornecedor_id = request.args.get("fornecedor_id", type=int) or None
    categoria_id = request.args.get("categoria_id", type=int) or None

    try:
        dt_ini_fmt = datetime.strptime(data_inicio, "%Y-%m-%d").strftime("%d/%m/%Y")
        dt_fim_fmt = datetime.strptime(data_fim, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        dt_ini_fmt = data_inicio
        dt_fim_fmt = data_fim

    periodo_texto = f"{dt_ini_fmt} a {dt_fim_fmt}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        if visao == "detalhada":
            despesas = database.buscar_despesas_periodo(
                data_inicio=data_inicio,
                data_fim=data_fim,
                setor_id=setor_id,
                fornecedor_id=fornecedor_id,
                categoria_id=categoria_id
            )
            total_gasto_num = sum(d["valor"] for d in despesas)
            total_gasto_fmt = database._fmt_moeda(total_gasto_num)

            nome_arquivo = f"Despesas_Empresariais_{timestamp}.pdf"
            caminho_pdf = str(PASTA_EXPORTACOES / nome_arquivo)

            report.gerar_pdf_detalhado(
                despesas=despesas,
                periodo_texto=periodo_texto,
                total_gasto=total_gasto_fmt,
                arquivo_destino=caminho_pdf
            )
        else:
            meses = database.buscar_dados_periodo(
                data_inicio=data_inicio,
                data_fim=data_fim,
                setor_id=setor_id,
                fornecedor_id=fornecedor_id,
                categoria_id=categoria_id
            )
            dados_tabela = [
                [m["mes"], m["orcado_fmt"], m["gasto_fmt"], m["percentual_fmt"], m["status"]]
                for m in meses
            ]

            nome_arquivo = f"Orcamento_Resumo_{timestamp}.pdf"
            caminho_pdf = str(PASTA_EXPORTACOES / nome_arquivo)

            report.gerar_pdf_resumo(
                dados=dados_tabela,
                periodo_texto=periodo_texto,
                arquivo_destino=caminho_pdf
            )

        return send_file(
            caminho_pdf,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype="application/pdf"
        )
    except Exception as e:
        log.error(f"Erro ao exportar PDF: {e}")
        return jsonify({"erro": f"Falha ao gerar PDF: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
