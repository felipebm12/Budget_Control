# 💰 BudgetControl SaaS v1.53

Sistema corporativo completo de **Controle Orçamentário e Gestão de Despesas Empresariais** com backend em Python (PostgreSQL / Supabase), geração de relatórios em PDF com ReportLab, interface web responsiva com Flask e CLI via terminal.

---

## 📋 Funcionalidades

- 🌐 **Dashboard Web Interativo e Responsivo**:
  - Interface moderna com paleta corporativa, cards de KPIs dinâmicos e tabelas responsivas.
  - Alternância instantânea entre **Visão Resumida** (consolidado mês a mês) e **Visão Detalhada** (lançamentos individuais com ações).
  - Estrutura de frontend desacoplada com folha de estilos externa em `static/css/style.css`.
- 🧭 **Menu Suspenso do Sistema (Ações Rápidas)**:
  - Header limpo e organizado com menu suspenso em dropdown categorizado:
    - **Lançamentos & Cadastros**: *Nova Despesa*, *Setores*, *Fornecedores*, *Categorias* e *Orçamento por Setor*.
    - **Relatórios & Manutenção**: *Exportar PDF* e *Limpar Despesas*.
    - Fechamento inteligente ao clicar fora, selecionar um item ou pressionar `Esc`.
- 📅 **Filtro Dinâmico por Intervalo de Datas**:
  - Seleção livre do período desejado nos campos **De** e **Até**.
  - **Atalhos rápidos de navegação**:
    - `Este Mês` *(selecionado por padrão)*
    - `Mês Anterior`
    - `Este Ano`
    - `Ano Anterior`
    - `Todo o Período`
  - **Gaveta Retrátil de Filtros Avançados**:
    - Filtros por **Setor**, **Fornecedor** e **Categoria** recolhidos em um painel expansível com botão intuitivo `Filtros`.
    - Badge dinâmico informando a quantidade de filtros ativos (ex: `1`, `2`, `3`), mantendo a barra visualmente limpa e objetiva sem perder a visibilidade dos critérios aplicados.
    - Botão dedicado **Limpar Filtros** para resetar os critérios com 1 clique.
  - Busca textual instantânea na tabela detalhada (filtra em tempo real por descrição, setor, fornecedor, categoria, destino ou data).
- 📊 **Orçamento por Setor**:
  - Tabela dedicada `orcamentos_setores` com tetos definidos por setor, ano e mês.
  - **Carregamento Automático**: ao selecionar o setor ou alterar o ano no dropdown, a grade de 12 meses é carregada instantaneamente, sem necessidade de cliques adicionais.
  - **Grade de 12 Meses**: edição rápida com salvamento automático ao sair do campo (`blur`) ou pressionar `Enter`.
  - **Opção "Aplicar para todos os meses"**:
    - Replica valores para todos os outros 11 meses em tempo real enquanto você digita.
    - Executa persistência atômica em lote no banco de dados.
  - **Resumo Comparativo por Setor**: aba visual com cards mostrando orçamento, gasto executado, saldo e status de alerta por setor.
  - **Cálculo Real na Visão Resumida**: os valores da coluna "Orçado" refletem fielmente os orçamentos cadastrados por setor (meses não definidos exibem R$ 0,00).
- 🏢 **Gestão Completa de Setores, Fornecedores & Categorias**:
  - **Setores (Departamentos / Centros de Custo)**: CRUD completo com contagem de lançamentos e montante total gasto.
  - **Fornecedores (Parceiros Comerciais)**: CRUD completo com busca instantânea e proteção contra exclusão de entidades com lançamentos vinculados.
  - **Categorias (Rubricas & Classificações)**: CRUD completo acessível pelo Menu do Sistema, com busca instantânea, badges de contagem de despesas, total financeiro executado e validação de exclusão.
  - Modais interativos com feedback visual e confirmações via **SweetAlert2**.
- ➕ **Cadastro & Edição de Despesas Empresariais**:
  - **Campos Limpos por Padrão**: ao abrir a tela de nova despesa (pelo menu ou pelo atalho na tabela), todos os campos (descrição, valor, setor, fornecedor, categoria e destino) iniciam completamente vazios, com a data de compra definida para o dia atual.
  - **Edição de Lançamentos**: botão dedicado de edição na coluna **Ações** da Visão Detalhada que abre o modal pré-populado com os dados do lançamento para atualização imediata (`PUT /api/despesas/<id>`).
  - Registro discriminando: *Descrição*, *Valor*, *Data da Compra*, *Setor Responsável*, *Fornecedor*, *Categoria* e *Destino/Finalidade*.
  - Sincronização automática imediata com a grade do dashboard e o resumo orçamentário.
- 📈 **Cards Inteligentes na Visão Detalhada**:
  - **Categoria Mais Custosa**: substituiu o gasto médio geral, identificando automaticamente a rubrica que acumulou o maior montante no período e filtros vigentes, com o total financeiro discriminado no subtítulo.
- 🔀 **Ordenação Multicoluna da Grade**:
  - Botão dedicado **Crescente / Decrescente** com alternador de direção na barra de ferramentas.
  - Dropdown dinâmico de seleção de coluna adaptado à visão ativa (Mês, Orçado, Gasto, Saldo, % na Resumida; Data, Valor, Descrição, Setor, Fornecedor, Categoria, Destino na Detalhada).
  - Cabeçalhos de coluna clicáveis (`<th>`) com indicadores visuais `▲` e `▼` e sincronização bidirecional.
- 🗑️ **Exclusão e Limpeza de Despesas**:
  - Exclusão individual com confirmação visual via SweetAlert2.
  - Botão de **Limpar Despesas** para remoção em massa com dupla confirmação preventiva.
- 📥 **Exportação em PDF**:
  - Geração de relatório com 1 clique respeitando exatamente os filtros ativos (datas, setor, fornecedor, categoria e visão selecionada).
  - Arquivos salvos automaticamente na pasta `Exportações/` com timestamp.
- 🚨 **Status e Alertas Orçamentários**:
  - Indicadores visuais dinâmicos em 3 faixas percentuais com badges e barras de progresso:
    - 🟢 **Dentro do orçamento**: consumo abaixo de 80% do teto definido.
    - 🟡 **Perto do orçamento**: consumo entre 80% e 99%, sinalizando atenção preventiva.
    - 🔴 **Acima do orçamento**: consumo em 100% ou superior, com alerta visual de estouro orçamentário.
- 🔐 **Autenticação, Recuperação de Senha por E-mail & Controle de Acesso**:
  - Sistema completo de login baseado em sessões seguras com `Flask-Login`, proteção de rotas (`@login_required`), rate limiting em memória contra força bruta e senhas criptografadas com `bcrypt` (cost 12).
  - **Recuperação de Senha via Magic Link por E-mail (`/esqueci-senha` e `/redefinir-senha/<token>`)**:
    - Geração de token criptográfico temporário (`secrets.token_urlsafe(32)`) com validade configurável (padrão: 30 minutos) e **uso único**.
    - Armazenamento seguro: apenas o hash **SHA-256** do token é gravado na tabela `tokens_recuperacao_senha`, invalidando tokens anteriores automaticamente.
    - Proteção contra enumeração de usuários e envio assíncrono via **SMTP** (`STARTTLS`/`SSL`) com fallback automático no console em ambiente de desenvolvimento.
  - Header interativo com avatar do usuário autenticado, identificação de perfil (`admin`/`usuario`) e botão de logout.
  - Modal interativo para **Troca de Senha** com validação de complexidade mínima (8 caracteres) e confirmação visual instantânea.
  - Script CLI `reset_senha.py` para redefinição emergencial de senhas diretamente pelo terminal.
- 👥 **Gestão de Usuários e Permissões Granulares (Painel do Administrador)**:
  - Painel modal de gerenciamento acessível pelo Menu do Sistema (exclusivo para perfil `admin`).
  - Busca e filtragem em tempo real de usuários cadastrados por login, nome completo ou **e-mail**.
  - Cadastro e edição de operadores com **e-mail obrigatório e único**, validações de login, senha segura, seleção de perfil (`admin` ou `usuario`) e configuração de **permissões granulares** (`jsonb`).
  - Redefinição de senha individual de qualquer operador diretamente pelo administrador: opção de **disparar Magic Link por e-mail com 1 clique** ou definir senha manualmente.
  - Travas automáticas de integridade e segurança (proteção contra auto-exclusão, auto-bloqueio e garantia de ao menos um administrador ativo).
  - Rotas de API protegidas com o decorator `@admin_required`.
- 💻 **CLI via Terminal**:
  - Script autônomo `main.py` para geração de relatórios diretos pelo console.

---

## 📁 Estrutura do Projeto

```
Budget_Control/
├── DB scripts/
│   ├── add_usuarios.sql           # Migração de usuários, e-mail, permissões e tokens de recuperação
│   ├── inserts.sql
│   ├── migrationwithupdates.sql   # Tabelas base, constraints e triggers
│   ├── rollbacksec.sql            # Script de reversão
│   └── teste.sql
├── Documentation/
│   ├── BudgetControl_Documentacao_Sistema_v1.00.docx
│   └── BudgetControl_Documentacao_Sistema_v1.00.pdf
├── Exportações/                   # PDFs gerados pelo sistema
├── Logs/                          # Arquivos de log
├── README.md                      # Documentação completa
└── python sections/
    ├── .env                       # Credenciais do banco e SMTP (ignorado no Git)
    ├── config.py                  # Leitura de variáveis de ambiente (Banco, Flask e SMTP)
    ├── database.py                # Camada de dados, consultas SQL, usuários e tokens (psycopg2)
    ├── gerar_documentacao.py      # Gerador automatizado de documentação (PDF e DOCX)
    ├── pdf_fonts.py               # Registro de fontes Google Sans para ReportLab
    ├── report.py                  # Geração de PDFs com ReportLab (resumido, detalhado e setores)
    ├── app.py                     # Servidor Web, Autenticação, SMTP e API REST (Flask)
    ├── main.py                    # Script CLI para terminal
    ├── reset_senha.py             # CLI para redefinição emergencial de senhas
    ├── requirements.txt           # Dependências Python
    ├── static/
    │   ├── css/
    │   │   └── style.css          # Estilos desacoplados do dashboard
    │   └── js/                    # Bibliotecas locais (SweetAlert2, html2canvas)
    └── templates/
        ├── index.html             # Interface Web do Dashboard
        ├── login.html             # Tela de Login Responsiva
        └── redefinir_senha.html   # Fluxo de Solicitação e Redefinição de Senha por Token
```

---

## 🗄️ Modelo de Dados (PostgreSQL / Supabase)

```
┌────────────────────────┐         ┌────────────────────────┐         ┌────────────────────────┐
│   orcamentos_anuais    │         │   orcamentos_mensais   │         │        despesas        │
├────────────────────────┤         ├────────────────────────┤         ├────────────────────────┤
│ id (PK, SERIAL)        │───1:N──▶│ id (PK, SERIAL)        │───1:N──▶│ id (PK, SERIAL)        │
│ ano                    │         │ orcamento_anual_id(FK) │         │ orcamento_mensal_id(FK)│
│ valor_orcado           │         │ mes (1 a 12)           │         │ setor_id (FK setores)  │
│ percentual_alerta      │         │ valor                  │         │ setor_destino_id (FK)  │
│ descricao              │         └────────────────────────┘         │ fornecedor_id (FK forn)│
└────────────────────────┘                                            │ rubrica_id (FK categ)  │
                                                                      │ destino / descricao    │
┌────────────────────────┐         ┌────────────────────────┐         │ valor / data_compra    │
│        setores         │         │      fornecedores      │         └────────────────────────┘
├────────────────────────┤         ├────────────────────────┤                     │
│ id (PK, SERIAL)        │         │ id (PK, SERIAL)        │                     ▼
│ nome / descricao       │         │ nome / descricao       │         ┌────────────────────────┐
│ realiza_compras (BOOL) │         └────────────────────────┘         │   despesas_auditoria   │
└────────────────────────┘                                            ├────────────────────────┤
            │                                                         │ id (PK, SERIAL)        │
            ▼                                                         │ despesa_id / acao      │
┌────────────────────────┐         ┌────────────────────────┐         │ dados_anteriores (JSON)│
│   orcamentos_setores   │         │        rubricas        │         │ dados_novos (JSON)     │
├────────────────────────┤         ├────────────────────────┤         │ usuario / data_alter.  │
│ id (PK, SERIAL)        │         │ id (PK, SERIAL)        │         └────────────────────────┘
│ setor_id (FK setores)  │         │ nome (Categoria)       │
│ ano / mes (1 a 12)     │         │ descricao              │         ┌────────────────────────┐
│ valor                  │         └────────────────────────┘         │        usuarios        │
│ UNIQUE(setor, ano, mes)│                                            ├────────────────────────┤
└────────────────────────┘         ┌────────────────────────┐         │ id (PK, IDENTITY)      │
                                   │tokens_recuperacao_senha│         │ username (UNIQUE)      │
                                   ├────────────────────────┤         │ email (UNIQUE)         │
                                   │ id (PK, IDENTITY)      │◀──1:N───│ senha_hash (bcrypt)    │
                                   │ usuario_id (FK usuario)│         │ nome_completo / tipo   │
                                   │ token_hash (SHA-256)   │         │ ativo (BOOL)           │
                                   │ expira_em / usado_em   │         │ permissoes (JSONB)     │
                                   │ ip_solicitante         │         │ criado_em/ultimo_acesso│
                                   └────────────────────────┘         └────────────────────────┘
```

---

## ⚙️ Pré-requisitos

- **Python** 3.10 ou superior
- Instância PostgreSQL no **[Supabase](https://supabase.com)** (ou servidor local)
- Dependências instaladas via `requirements.txt`

---

## 🚀 Instalação e Execução

### 1. Clonar o repositório
```bash
git clone https://github.com/felipebm12/Budget_Control.git
cd "Budget_Control/python sections"
```

### 2. Criar e ativar o ambiente virtual
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar `.env`
Crie o arquivo `python sections/.env`:
```env
# Banco de Dados (Obrigatório)
DB_HOST=aws-1-sa-east-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.seu_projeto
DB_PASSWORD=sua_senha_aqui

# Servidor SMTP para Recuperação de Senha por E-mail (Opcional em Dev: exibe link no log)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-de-app
SMTP_FROM=Controle de Despesas <seu-email@gmail.com>
SMTP_USE_TLS=1
SMTP_USE_SSL=0
APP_BASE_URL=http://127.0.0.1:5000
RESET_TOKEN_EXPIRA_MINUTOS=30
```

### 5. Iniciar a Aplicação Web
```bash
python app.py
```
Acesse no navegador:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔌 Rotas & API REST (Endpoints)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Dashboard principal |
| `GET/POST` | `/login` | Autenticação de usuários |
| `GET/POST` | `/logout` | Encerramento da sessão autenticada |
| `GET/POST` | `/esqueci-senha` | Solicitação de link temporário de recuperação de senha por e-mail |
| `GET/POST` | `/redefinir-senha/<token>` | Validação do token de uso único e cadastro da nova senha |
| `POST` | `/api/trocar-senha` | Troca de senha pelo próprio usuário autenticado |
| `GET/POST` | `/api/usuarios` | Listagem e cadastro de usuários com e-mail obrigatório (`@admin_required`) |
| `PUT/DELETE` | `/api/usuarios/<id>` | Edição de dados/e-mail/status e exclusão de usuário (`@admin_required`) |
| `PUT` | `/api/usuarios/<id>/permissoes` | Atualização de permissões granulares de um usuário (`@admin_required`) |
| `PUT` | `/api/usuarios/<id>/senha` | Redefinição manual de senha pelo administrador (`@admin_required`) |
| `POST` | `/api/usuarios/<id>/enviar-link-reset` | Disparo de Magic Link de redefinição para o e-mail do usuário (`@admin_required`) |
| `GET` | `/api/dados` | Dados consolidados por mês com orçamentos e gastos |
| `GET/POST` | `/api/despesas` | Listagem filtrada e cadastro de nova despesa empresarial |
| `PUT/DELETE` | `/api/despesas/<id>` | Edição e exclusão de despesa individual |
| `DELETE/POST` | `/api/despesas/limpar-todas` | Limpeza de todas as despesas |
| `GET/POST` | `/api/setores` | Listagem e cadastro de setores |
| `PUT/DELETE` | `/api/setores/<id>` | Edição e exclusão de setor (protegida contra vínculos) |
| `GET/POST` | `/api/fornecedores` | Listagem e cadastro de fornecedores |
| `PUT/DELETE` | `/api/fornecedores/<id>` | Edição e exclusão de fornecedor (protegida contra vínculos) |
| `GET/POST` | `/api/categorias` | Listagem e cadastro de categorias (rubricas) |
| `PUT/DELETE` | `/api/categorias/<id>` | Edição e exclusão de categoria (protegida contra vínculos) |
| `GET` | `/api/orcamentos-setor?setor_id=X&ano=YYYY` | 12 meses de orçamento e gasto de um setor |
| `POST` | `/api/orcamentos-setor` | Salvar orçamento mensal (`aplicar_todos: true` para lote) |
| `GET` | `/api/orcamentos-setor/resumo?ano=YYYY` | Resumo anual comparativo de todos os setores |
| `GET` | `/api/orcamentos-setor/resumo/exportar-pdf` | Exportação em PDF do resumo anual por setor |
| `GET` | `/api/orcamentos-setor/resumo/exportar-csv` | Exportação em CSV do resumo anual por setor |
| `GET` | `/api/exportar-pdf` | Geração e download do relatório principal em PDF |
| `GET` | `/api/exportar-csv` | Geração e download dos lançamentos filtrados em CSV |

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologias |
|---|---|
| **Linguagem** | Python 3.10+ |
| **Backend Web & Auth** | Flask, Flask-Login, Bcrypt, SMTP (`smtplib` / `ssl`) |
| **Banco de Dados** | PostgreSQL (Supabase) via `psycopg2` (ThreadedConnectionPool) |
| **Relatórios PDF & Docs** | ReportLab, python-docx |
| **Frontend** | HTML5 semântico, CSS3 Modular (`style.css`), JavaScript Vanilla |
| **Alertas & Capturas** | SweetAlert2, html2canvas |
