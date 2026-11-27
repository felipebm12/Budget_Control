# Instruções para Agentes de IA — BudgetControl SaaS

> Este documento define o contrato operacional para agentes de IA que contribuem neste repositório. Leia-o integralmente antes de propor ou aplicar alterações.

---

## 1. Contexto do Projeto

- **Produto:** BudgetControl SaaS (v1.53) — Sistema corporativo de Controle Orçamentário e Gestão de Despesas Empresariais.
- **Stack:** Python 3.10+ (Flask, Flask-Login, Gunicorn, `psycopg2-binary`, `bcrypt`, ReportLab) + PostgreSQL/Supabase + Frontend HTML5/CSS3/Vanilla JS (`SweetAlert2` e `html2canvas`).
- **Atenção ao caminho de código:** todo o código-fonte Python, templates e assets estáticos residem na pasta **`python sections/`** (com espaço no nome — sempre coloque entre aspas em comandos shell, ex.: `"python sections/app.py"`).
- **Idioma padrão:** português brasileiro (`pt-BR`) para textos de interface, mensagens de erro, nomes de funções/variáveis de domínio, commits e documentação.

---

## 2. Fonte da Verdade (Hierarquia)

Em caso de dúvida sobre o comportamento atual ou esperado do sistema, consulte nesta ordem de prioridade:

1. **Código-fonte e Scripts SQL** (`python sections/*.py`, `python sections/static/css/style.css`, `python sections/templates/*.html`, `DB scripts/*.sql`) — verdade absoluta do que roda em produção.
2. **[`ARCHITECTURE.md`](./ARCHITECTURE.md)** — limites de camadas, ciclo de requisições, modelo de dados e controles de segurança.
3. **[`Product Requirements.md`](./Product%20Requirements.md)** — regras de negócio, escopo MVP vs. pós-MVP e critérios de aceite.
4. **[`DESIGN-SYSTEM.md`](./DESIGN-SYSTEM.md)** — tokens visuais ativos, tipografia, componentes e acessibilidade.
5. **[`README.md`](./README.md)** — visão geral, instruções de instalação e catálogo de endpoints.

> Sempre que uma alteração de código mudar rotas, regras de negócio, tokens visuais ou schema de banco, **atualize o documento correspondente na mesma entrega**.

---

## 3. Fluxo de Trabalho Obrigatório

1. **Explorar antes de editar:** leia os arquivos relevantes e verifique como o padrão já está implementado no repositório (ex.: como rotas validam permissões ou como modais são estilizados).
2. **Planejar com escopo mínimo:** altere apenas o necessário para atender o pedido. Não refatore código não relacionado nem remova comentários existentes sem solicitação explícita.
3. **Respeitar as fronteiras de arquitetura:**
   - Queries SQL e lógica de persistência → `python sections/database.py` (e migração em `DB scripts/` quando aplicável).
   - Rotas HTTP, validação de entrada, auth/permissões e serialização → `python sections/app.py`.
   - Geração de PDF → `python sections/report.py` e `python sections/pdf_fonts.py`.
   - Estilos → `python sections/static/css/style.css` (respeitando o bloco de refinamento visual no final do arquivo).
   - Interface → `python sections/templates/*.html`.
4. **Validar:** execute o checklist da Seção 5 antes de finalizar.
5. **Reportar com clareza:** resuma o que mudou, quais arquivos foram tocados, o que foi validado e eventuais pré-requisitos (como rodar um script SQL ou configurar uma variável no `.env`).

---

## 4. Regras: O que FAZER vs. O que EVITAR

### ✅ O que FAZER
- **SQL 100% parametrizado:** use sempre placeholders `%s` do `psycopg2` em `database.py`.
- **Usar `get_db_connection()`:** sempre obtenha conexões pelo context manager do pool fork-safe em `database.py`.
- **Proteger todas as novas rotas:** aplique `@login_required`, `@admin_required` ou verificação `current_user.tem_permissao("<chave>")` conforme o nível de acesso exigido.
- **Validar entrada no backend:** nunca confie apenas em validação do frontend; valide tipos, limites monetários (`_validar_valor_monetario`), tamanhos de string e chaves estrangeiras no servidor.
- **Sanitizar saídas sensíveis:** use `_sanitizar_celula_csv` em novos campos CSV, `_esc` em novos campos de PDF ReportLab e `html.escape` em templates de e-mail.
- **Usar tokens CSS ativos:** utilize as variáveis definidas no bloco `Refinamento visual: painel operacional` de `style.css` (`--primaria`, `--verde`, `--vermelho`, `--azul`, `--roxo`, `--ambar`, `--cinza-*`, `--radius`, `--sombra-*`).
- **Invalidar cache de usuário:** ao alterar dados, status ou permissões em `usuarios`, chame `invalidar_cache_usuario(user_id)`.
- **Preservar compatibilidade Gunicorn/Render:** mantenha inicialização lazy/fork-safe do pool de banco e sem estado mutável global não sincronizado (use `threading.Lock` se necessário).

### ❌ O que EVITAR
- **Nunca** escrever SQL diretamente em `app.py`, `report.py` ou templates.
- **Nunca** importar `app.py` dentro de `database.py`, `report.py` ou `config.py` (evitar dependência circular).
- **Nunca** expor stack traces, credenciais, tokens ou conteúdo de `.env` em respostas HTTP, logs ou commits.
- **Nunca** introduzir frameworks pesados de frontend (React, Tailwind, Bootstrap, jQuery) ou novas dependências Python sem aprovação explícita — o projeto é intencionalmente enxuto em Vanilla JS e CSS modular.
- **Nunca** desabilitar ou enfraquecer proteções existentes (CSRF `before_request`, rate limiting, `bcrypt`, `sslmode="require"`, headers de segurança, travas do último admin).
- **Nunca** editar apenas o `:root` das linhas 4–32 de `style.css` esperando alterar cores em produção, pois o bloco `:root` da linha 1316 sobrescreve esses valores.
- **Nunca** retornar mensagens que revelem se um usuário/e-mail existe em fluxos públicos (`/login`, `/esqueci-senha`).

---

## 5. Checklist de Validação

Antes de considerar uma tarefa concluída, verifique todos os itens aplicáveis:

- [ ] **Sintaxe Python válida:** executar `python3 -m py_compile "python sections"/*.py` sem erros.
- [ ] **Sem imports quebrados ou circulares:** respeita o grafo de dependências de `ARCHITECTURE.md`.
- [ ] **Segurança e RBAC:** novas rotas possuem autenticação, checagem de permissão, validação de payload e não burlam CSRF.
- [ ] **Banco de dados seguro:** queries parametrizadas, sem quebra de integridade referencial e migração SQL documentada/idempotente se houve alteração de schema.
- [ ] **UI e Design System:** usa tokens ativos do `DESIGN-SYSTEM.md`, mantém `tabular-nums` em valores financeiros, funciona em desktop e mobile (`≤ 768px` e `≤ 480px`) e inclui `aria-label` em botões de ícone.
- [ ] **Exportações preservadas:** se alterou campos de despesa ou orçamento, verificar impacto em PDF (`report.py`), CSV (`/api/exportar-csv`) e PNG (`index.html`).
- [ ] **Higiene de Git:** nenhum arquivo `.env`, log temporário ou PDF de teste foi incluído acidentalmente (`git status` limpo de artefatos indesejados).
- [ ] **Documentação sincronizada:** `README.md`, `Product Requirements.md`, `DESIGN-SYSTEM.md` ou `ARCHITECTURE.md` atualizados se houve mudança estrutural.

---

## 6. Tratamento de Conflitos e Ambiguidades

1. **Conflito entre documentação e código:** o código em produção prevalece para entender o comportamento atual; reporte a divergência ao usuário e proponha alinhar a documentação (ou corrigir o código, se for um bug evidente).
2. **Conflito no `style.css` (tokens antigos vs. refinamento operacional):** considere sempre o bloco final (`/* ── Refinamento visual: painel operacional ── */`) como padrão oficial.
3. **Requisitos subespecificados:** se uma solicitação envolver mudança destrutiva de banco, nova permissão granular, alteração de regra de negócio financeira ou nova dependência externa, **pergunte antes de assumir**.
4. **Alterações de schema em produção:** prefira sempre migrações retrocompatíveis e idempotentes (`IF NOT EXISTS`, valores `DEFAULT`) para evitar downtime entre deploy de código e execução do SQL no Supabase.

---

## 7. Definição de Pronto (Definition of Done — DoD)

Uma tarefa só está **Pronta** quando:
1. Todos os requisitos funcionais e critérios de aceite da solicitação foram atendidos.
2. O código segue os padrões de arquitetura, segurança e design system deste repositório.
3. As validações aplicáveis (compilação/sintaxe, revisão de diff, checagem de segurança e regressão) foram executadas e passaram.
4. Nenhum arquivo sensível ou temporário foi deixado no workspace.
5. A documentação relevante foi atualizada e a entrega foi comunicada de forma clara e objetiva.
