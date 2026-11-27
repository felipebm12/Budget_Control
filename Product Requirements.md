# Product Requirements Document (PRD) — BudgetControl SaaS

> **Produto:** BudgetControl SaaS  
> **Versão de referência:** v1.53  
> **Idioma do produto:** Português (pt-BR)  
> **Público deste documento:** Produto, Engenharia, Design e Agentes de IA

---

## 1. Visão Geral

O **BudgetControl SaaS** é uma plataforma corporativa de **Controle Orçamentário e Gestão de Despesas Empresariais** voltada para organizações que precisam planejar tetos financeiros por setor, registrar lançamentos operacionais com rastreabilidade completa e acompanhar a execução orçamentária em tempo real.

A aplicação combina:
- **Painel Web interativo e responsivo** (Flask + HTML/CSS/JavaScript Vanilla) com visões consolidada e analítica.
- **Persistência relacional auditável** em PostgreSQL (Supabase), com triggers de auditoria automática.
- **Exportação corporativa** de relatórios em **PDF** (ReportLab), **CSV** (compatível com Excel/pt-BR) e **PNG** (captura visual do dashboard via `html2canvas`).
- **Governança de acesso** baseada em perfis (`admin` e `usuario`) e permissões granulares em JSONB, com recuperação de senha via *Magic Link* por e-mail.
- **Ferramentas CLI** complementares para geração de relatórios em lote e recuperação emergencial de acesso.

---

## 2. Problema e Objetivo

### 2.1 Problema
Equipes financeiras, administrativas e de compras frequentemente controlam orçamentos e despesas em planilhas isoladas, o que gera:
- **Falta de visibilidade em tempo real** do consumo mensal em relação ao teto planejado por setor.
- **Baixa rastreabilidade** sobre quem comprou, para qual setor de destino, qual fornecedor foi contratado e em qual categoria (rubrica) o gasto foi alocado.
- **Risco de estouro orçamentário silencioso**, identificado apenas no fechamento contábil.
- **Ausência de controle de acesso e auditoria**, permitindo exclusões ou edições sem histórico.
- **Retrabalho na geração de relatórios gerenciais** para diretoria e prestação de contas.

### 2.2 Objetivos do Produto
1. **Centralizar** o planejamento orçamentário mensal por setor e os lançamentos de despesas em uma única fonte de dados confiável.
2. **Prevenir estouros orçamentários** por meio de indicadores visuais claros em três faixas de consumo (`< 80%`, `80%–99%`, `≥ 100%`).
3. **Garantir governança e segurança** com autenticação forte, permissões granulares por operador e trilha de auditoria no banco de dados.
4. **Agilizar a análise e prestação de contas** com filtros combináveis, busca instantânea, ordenação multicoluna e exportação em 1 clique (PDF, CSV e PNG).

---

## 3. Usuários-Alvo e Personas

| Persona | Perfil no Sistema | Principais Necessidades |
|---|---|---|
| **Administrador Financeiro / TI** | `admin` | Configurar tetos orçamentários por setor, manter cadastros base (setores, fornecedores, categorias), gerenciar usuários e permissões, disparar links de redefinição de senha e auditar a operação. |
| **Analista / Operador de Compras** | `usuario` (permissões configuráveis) | Lançar, editar e consultar despesas rapidamente, filtrar por período/setor/fornecedor/categoria e exportar relatórios operacionais. |
| **Gestor de Setor / Diretoria** | `usuario` (leitura + exportação) ou `admin` | Monitorar KPIs consolidados, acompanhar o saldo disponível por setor no ano e extrair relatórios executivos (PDF/PNG/CSV) para reuniões. |

---

## 4. Funcionalidades Principais

### 4.1 Dashboard Interativo (Visões Resumida e Detalhada)
- **Alternância instantânea** entre:
  - **Visão Resumida:** consolidado mês a mês comparando *Orçado*, *Gasto*, *Saldo*, *% Utilizado* e *Status*, com link direto no nome do mês para abrir o detalhamento daquele período.
  - **Visão Detalhada:** listagem analítica de lançamentos individuais com badges coloridos (Setor Responsável, Setor de Destino, Fornecedor, Categoria) e coluna de ações (editar/excluir).
- **Cards de KPI dinâmicos** atualizados conforme filtros ativos:
  - Orçamento Total, Gasto Total, Saldo Disponível, % Consumido (com barra de progresso) e **Categoria Mais Custosa** na visão detalhada.

### 4.2 Filtros Dinâmicos, Busca e Ordenação
- **Intervalo de datas livre** (*De* / *Até*) com atalhos rápidos: `Este Mês` (padrão), `Mês Anterior`, `Este Ano`, `Ano Anterior` e `Todo o Período`.
- **Gaveta retrátil de filtros avançados** por *Setor Responsável*, *Setor de Destino*, *Fornecedor* e *Categoria*, com badge numérico indicando quantos filtros estão ativos e botão **Limpar Filtros**.
- **Busca textual instantânea** na visão detalhada (descrição, setor, setor de destino, fornecedor, categoria, destino ou data).
- **Ordenação multicoluna** bidirecional (crescente/decrescente) via dropdown dedicado ou clique nos cabeçalhos `<th>`.

### 4.3 Gestão de Despesas Empresariais
- **Cadastro e edição em modal** (`POST /api/despesas`, `PUT /api/despesas/<id>`) com campos: *Descrição*, *Valor (R$)*, *Data da Compra*, *Setor Responsável* (filtrado por setores que realizam compras), *Setor de Destino*, *Fornecedor*, *Categoria (Rubrica)* e *Destino / Finalidade* (até 500 caracteres).
- **Campos limpos por padrão** ao abrir novo lançamento, com data inicializada para o dia atual.
- **Exclusão individual** com confirmação via SweetAlert2 e **Limpeza em massa** (restrita a administradores, com dupla confirmação preventiva).

### 4.4 Orçamento por Setor
- **Grade de 12 meses** por setor e ano com carregamento automático ao alterar setor/ano.
- **Salvamento automático** por célula ao sair do campo (`blur`) ou pressionar `Enter`.
- **Aplicação em lote ("Aplicar para todos os meses")** com persistência atômica no banco de dados.
- **Resumo Comparativo por Setor:** painel consolidado anual comparando orçamento, gasto, saldo e status de cada setor, com exportação própria em PDF e CSV.

### 4.5 Cadastros Auxiliares (Setores, Fornecedores e Categorias)
- CRUD completo em modais dedicados acessíveis pelo **Menu do Sistema**.
- Exibição de contagem de lançamentos e montante financeiro acumulado por entidade.
- **Setores** possuem flag `realiza_compras` (booleano) para diferenciar setores compradores de setores apenas destinatários.
- **Integridade referencial:** bloqueio de exclusão de setores, fornecedores ou categorias que possuam despesas ou orçamentos vinculados.

### 4.6 Exportações Corporativas
- **PDF (`/api/exportar-pdf` e `/api/orcamentos-setor/resumo/exportar-pdf`):** relatórios formatados com ReportLab e fonte *Google Sans*, respeitando os filtros ativos e salvos com timestamp na pasta `Exportações/`.
- **CSV (`/api/exportar-csv` e `/api/orcamentos-setor/resumo/exportar-csv`):** UTF-8 com BOM (`utf-8-sig`), separador `;`, valores no padrão decimal brasileiro e sanitização contra *CSV Formula Injection*.
- **Imagem PNG (Frontend):** captura visual com `html2canvas` permitindo escolher o escopo (dashboard completo, KPIs ou tabela).

### 4.7 Autenticação, Recuperação de Senha e RBAC Granular
- Login por sessão segura (`Flask-Login`) com senhas criptografadas via `bcrypt` (cost 12) e proteção contra força bruta.
- **Recuperação de senha via Magic Link** (`/esqueci-senha` e `/redefinir-senha/<token>`): token criptográfico de uso único, armazenado apenas como hash SHA-256, expiração configurável (padrão 30 min) e envio via SMTP (com fallback em log no modo dev).
- **Troca de senha autenticada** (`/api/trocar-senha`) exigindo mínimo de 8 caracteres.
- **Gestão de Usuários (`@admin_required`):** CRUD de operadores com e-mail único obrigatório, ativação/desativação, disparo de Magic Link ou redefinição manual de senha e configuração de **8 permissões granulares**:
  - `despesas_criar`, `despesas_editar`, `despesas_excluir`
  - `setores_gerenciar`, `fornecedores_gerenciar`, `categorias_gerenciar`
  - `orcamentos_editar`, `relatorios_exportar`
- **Travas de segurança:** impede auto-exclusão, auto-bloqueio e desativação/remoção do último administrador ativo.

### 4.8 Utilitários CLI
- `main.py`: geração de relatórios PDF via linha de comando (`--ano`, `--saida`).
- `reset_senha.py`: redefinição emergencial de senha via terminal sem exibir caracteres digitados.

---

## 5. Regras de Negócio Críticas

1. **Classificação de Status Orçamentário (`calcular_status_orcamento`):**
   - **Dentro do orçamento:** consumo `< 80%` (e orçamento `> 0`).
   - **Perto do orçamento:** consumo entre `80%` e `99,99%`.
   - **Acima do orçamento:** consumo `≥ 100%` ou quando há gasto (`> 0`) em um período sem orçamento definido (`≤ 0`).
2. **Validação Monetária:** despesas exigem valor finito estritamente positivo (`> 0` até `999.999.999,99`); orçamentos permitem valor `≥ 0` até o mesmo teto, arredondados em 2 casas decimais.
3. **Classificação Obrigatória:** toda despesa exige obrigatoriamente `rubrica_id` (categoria) e `setor_id` (setor responsável).
4. **Destino / Finalidade:** limite máximo de 500 caracteres.
5. **Unicidade:** não podem existir dois orçamentos para a mesma combinação `(setor_id, ano, mes)` nem dois usuários com mesmo `username` ou `email` (case-insensitive).
6. **Auditoria Automática:** toda operação `INSERT`, `UPDATE` ou `DELETE` em `despesas` é gravada automaticamente em `despesas_auditoria` via trigger PostgreSQL.

---

## 6. Escopo: MVP vs. Pós-MVP

### 6.1 MVP (Entregue — Núcleo Operacional v1.x)
- [x] Autenticação segura (`Flask-Login` + `bcrypt`), troca de senha e recuperação por Magic Link (SMTP).
- [x] Controle de acesso por perfil (`admin`/`usuario`) e 8 permissões granulares.
- [x] Dashboard web responsivo com Visão Resumida, Visão Detalhada, KPIs e alertas percentuais.
- [x] CRUD completo de Despesas (com Setor Responsável e Setor de Destino), Setores (`realiza_compras`), Fornecedores e Categorias.
- [x] Gestão de Orçamento por Setor (grade de 12 meses, lote e resumo comparativo anual).
- [x] Filtros dinâmicos por data, gaveta de filtros avançados, busca instantânea e ordenação multicoluna.
- [x] Exportação em PDF, CSV e PNG respeitando filtros ativos.
- [x] Auditoria de despesas em banco (trigger) e CLI de relatório/reset de senha.

### 6.2 Pós-MVP (Roadmap Evolutivo)
- [ ] **Multi-tenancy SaaS:** isolamento lógico por organização/empresa (`tenant_id`) com planos e faturamento.
- [ ] **Anexos e Comprovantes:** upload de notas fiscais e recibos (Storage S3/Supabase Storage) vinculados a cada despesa.
- [ ] **Fluxo de Aprovação:** workflow configurável de solicitação → aprovação do gestor → efetivação da despesa.
- [ ] **Notificações Proativas:** alertas automáticos por e-mail/webhook quando um setor atingir 80% ou 100% do teto.
- [ ] **Visualizações Gráficas:** gráficos interativos de tendência mensal, distribuição por categoria e comparativo anual.
- [ ] **Interface de Auditoria:** tela administrativa para consulta e filtragem do histórico gravado em `despesas_auditoria`.
- [ ] **Importação em Lote:** importação assistida de despesas e orçamentos via planilha CSV/XLSX com validação prévia.
- [ ] **Suíte de Testes Automatizados e CI/CD:** cobertura automatizada de API, regras de negócio e pipeline de deploy.

---

## 7. Requisitos Não Funcionais

- **Segurança:** senhas em `bcrypt` (cost 12), proteção CSRF same-origin, rate limiting contra força bruta, cookies `HttpOnly` e `SameSite=Lax`, prevenção contra Open Redirect, XSS e CSV Injection, e cabeçalhos de segurança HTTP (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).
- **Desempenho:** pool de conexões PostgreSQL (`ThreadedConnectionPool`) fork-safe com pré-aquecimento assíncrono na tela de login, cache em memória para `user_loader` (TTL 60s) e índices compostos em `despesas`.
- **Responsividade:** layout adaptável para desktop (`max-width: 1360px`), tablet (`≤ 768px`) e smartphones (`≤ 480px`).
- **Disponibilidade / Operação:** compatível com deploy WSGI via Gunicorn (ex.: Render) conectado a PostgreSQL gerenciado (Supabase) com `sslmode="require"` e health-check transparente de conexões ociosas.

---

## 8. Critérios de Aceite

### CA-01 — Autenticação e Recuperação de Acesso
- **Dado** um usuário ativo com credenciais válidas, **quando** realiza login em `/login`, **então** é redirecionado ao dashboard com sessão válida de 8 horas.
- **Dado** tentativas excessivas de login, **quando** o limite de taxa é atingido, **então** a requisição é bloqueada com feedback claro sem vazar se o usuário existe.
- **Dado** uma solicitação em `/esqueci-senha`, **quando** o link é usado dentro do prazo, **então** a senha é atualizada com mínimo de 8 caracteres e o token é invalidado imediatamente (uso único).

### CA-02 — Gestão de Despesas e Integridade
- **Dado** um usuário com permissão `despesas_criar`, **quando** cadastra uma despesa com valor `> 0`, categoria e setor válidos, **então** o registro é persistido, auditado em `despesas_auditoria` e refletido imediatamente nos KPIs e na tabela.
- **Dado** um usuário sem permissão `despesas_excluir`, **quando** tenta chamar `DELETE /api/despesas/<id>`, **então** o backend rejeita a operação com HTTP `403`.

### CA-03 — Orçamento por Setor e Alertas
- **Dado** um administrador ou usuário com `orcamentos_editar`, **quando** preenche a grade de 12 meses com "Aplicar para todos os meses" marcado, **então** todos os 12 meses são salvos atomicamente e a Visão Resumida recalcula os percentuais e status (`< 80%`, `80%–99%`, `≥ 100%`).

### CA-04 — Cadastros Auxiliares Protegidos
- **Dado** um setor, fornecedor ou categoria que possua ao menos uma despesa vinculada, **quando** o administrador tenta excluí-lo, **então** a API bloqueia a exclusão e retorna mensagem explicativa preservando a integridade referencial.

### CA-05 — Exportações Fiéis aos Filtros
- **Dado** um conjunto de filtros ativos (período, setor, fornecedor, categoria), **quando** o usuário exporta PDF, CSV ou PNG, **então** o arquivo gerado contém exclusivamente os dados correspondentes aos filtros vigentes e sem fórmulas executáveis em células CSV.

### CA-06 — Governança de Usuários
- **Dado** o último usuário `admin` ativo do sistema, **quando** tenta se auto-excluir, se desativar ou rebaixar o próprio perfil, **então** o sistema impede a operação retornando erro de validação.
