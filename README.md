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
- 🔐 **Autenticação & Controle de Acesso**:
  - Sistema completo de login baseado em sessões seguras com `Flask-Login` e senhas com hash `bcrypt`.
  - Proteção de todas as rotas e endpoints da API via decorator `@login_required`.
  - Header interativo com avatar do usuário autenticado, identificação de perfil (`admin`/`usuario`) e botão de logout.
  - Modal interativo para **Troca de Senha** com validação de complexidade mínima (8 caracteres) e confirmação visual instantânea.
  - Script CLI `reset_senha.py` para redefinição emergencial de senhas diretamente pelo terminal.
- 👥 **Gestão de Usuários na Interface Web (Painel do Administrador)**:
  - Painel modal de gerenciamento acessível pelo Menu do Sistema (exclusivo para perfil `admin`).
  - Busca e filtragem em tempo real de usuários cadastrados por login ou nome completo.
  - Cadastro de novos operadores com validações de login, senha segura e seleção de perfil (`admin` ou `usuario`).
  - Edição de perfil e status de ativação/bloqueio com salvamento instantâneo.
  - Redefinição de senha individual de qualquer operador diretamente pelo administrador.
  - Travas automáticas de integridade e segurança (proteção contra auto-exclusão, auto-bloqueio e garantia de administrador ativo).
  - Rotas de API protegidas com o decorator `@admin_required`.
- 💻 **CLI via Terminal**:
  - Script autônomo `main.py` para geração de relatórios diretos pelo console.

---

## 📁 Estrutura do Projeto

```
BudgetControl_v1.00/
├── DB scripts/
│   ├── add_usuarios.sql           # Migração da tabela de usuários e admin inicial
│   ├── inserts.sql
│   ├── migrationwithupdates.sql   # Tabelas base, constraints e triggers
│   ├── rollbacksec.sql            # Script de reversão
│   └── teste.sql
├── Documentation/
│   ├── BudgetControl_Documentacao_Sistema_v1.00.docx
│   ├── BudgetControl_Documentacao_Sistema_v1.00.pdf
│   └── gerar_documentacao.py      # Gerador automatizado de documentação
├── Exportações/                   # PDFs gerados pelo sistema
├── Logs/                          # Arquivos de log
├── README.md                      # Documentação completa
└── python sections/
    ├── .env                       # Credenciais do banco (ignorado no Git)
    ├── .gitignore
    ├── config.py                  # Leitura de variáveis de ambiente
    ├── database.py                # Camada de dados, consultas SQL e persistência (psycopg2)
    ├── report.py                  # Geração de PDFs com ReportLab (resumido e detalhado)
    ├── app.py                     # Servidor Web e API REST (Flask)
    ├── main.py                    # Script CLI para terminal
    ├── reset_senha.py             # CLI para redefinição de senhas
    ├── requirements.txt           # Dependências Python
    ├── static/
    │   └── css/
    │       └── style.css          # Estilos desacoplados do dashboard
    └── templates/
        ├── index.html             # Interface Web do Dashboard
        └── login.html             # Tela de Login Responsiva
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
│ percentual_alerta      │         │ valor                  │         │ fornecedor_id (FK forn)│
│ descricao              │         └────────────────────────┘         │ rubrica_id (FK categ)  │
└────────────────────────┘                                            │ destino                │
                                                                      │ descricao              │
┌────────────────────────┐         ┌────────────────────────┐         │ valor                  │
│        setores         │         │      fornecedores      │         │ data_compra            │
├────────────────────────┤         ├────────────────────────┤         │ data_criacao           │
│ id (PK, SERIAL)        │         │ id (PK, SERIAL)        │         └────────────────────────┘
│ nome                   │         │ nome                   │                     │
│ descricao              │         │ descricao              │                     ▼
└────────────────────────┘         └────────────────────────┘         ┌────────────────────────┐
            │                                                         │   despesas_auditoria   │
            ▼                                                         ├────────────────────────┤
┌────────────────────────┐         ┌────────────────────────┐         │ id (PK, SERIAL)        │
│   orcamentos_setores   │         │        rubricas        │         │ despesa_id             │
├────────────────────────┤         ├────────────────────────┤         │ acao (INS/UPD/DEL)     │
│ id (PK, SERIAL)        │         │ id (PK, SERIAL)        │         │ dados_anteriores (JSON)│
│ setor_id (FK setores)  │         │ nome (Categoria)       │         │ dados_novos (JSON)     │
│ ano                    │         │ descricao              │         │ usuario                │
│ mes (1 a 12)           │         └────────────────────────┘         │ data_alteracao         │
│ valor                  │                                            └────────────────────────┘
│ UNIQUE(setor, ano, mes)│
└────────────────────────┘
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
git clone https://github.com/felipebm12/budgetcontrolv1.00.git
cd budgetcontrolv1.00/python\ sections
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
DB_HOST=aws-1-sa-east-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.seu_projeto
DB_PASSWORD=sua_senha_aqui
```

### 5. Iniciar a Aplicação Web
```bash
python app.py
```
Acesse no navegador:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔌 API REST (Endpoints)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Dashboard principal |
| `GET` | `/api/dados` | Dados consolidados por mês com orçamentos e gastos |
| `GET` | `/api/despesas` | Lançamentos individuais filtrados |
| `POST` | `/api/despesas` | Cadastro de nova despesa empresarial |
| `DELETE` | `/api/despesas/<id>` | Exclusão de despesa individual |
| `DELETE` | `/api/despesas/limpar-todas` | Limpeza de todas as despesas |
| `GET` | `/api/setores` | Listagem de setores com gastos acumulados |
| `POST` | `/api/setores` | Cadastro de novo setor |
| `PUT` | `/api/setores/<id>` | Edição de setor |
| `DELETE` | `/api/setores/<id>` | Exclusão de setor (protegida contra vínculos) |
| `GET` | `/api/fornecedores` | Listagem de fornecedores com gastos acumulados |
| `POST` | `/api/fornecedores` | Cadastro de novo fornecedor |
| `PUT` | `/api/fornecedores/<id>` | Edição de fornecedor |
| `DELETE` | `/api/fornecedores/<id>` | Exclusão de fornecedor (protegida contra vínculos) |
| `GET` | `/api/categorias` | Listagem de categorias (rubricas) |
| `GET` | `/api/orcamentos-setor?setor_id=X&ano=YYYY` | 12 meses de orçamento e gasto de um setor |
| `POST` | `/api/orcamentos-setor` | Salvar orçamento mensal (`aplicar_todos: true` para lote) |
| `GET` | `/api/orcamentos-setor/resumo?ano=YYYY` | Resumo anual comparativo de todos os setores |
| `GET` | `/api/exportar-pdf` | Geração e download do relatório em PDF |

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologias |
|---|---|
| **Linguagem** | Python 3.10+ |
| **Backend Web** | Flask |
| **Banco de Dados** | PostgreSQL (Supabase) via `psycopg2` |
| **Relatórios PDF** | ReportLab |
| **Frontend** | HTML5 semântico, CSS3 Modular (`style.css`), JavaScript Vanilla |
| **Alertas & Modais** | SweetAlert2 |
