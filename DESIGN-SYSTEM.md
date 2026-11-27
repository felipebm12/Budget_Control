# Design System — BudgetControl SaaS

> **Fonte principal de estilos:** `python sections/static/css/style.css`  
> **Fontes locais:** `python sections/fonts/GoogleSans-Regular.ttf` e `GoogleSans-Bold.ttf`  
> **Paleta de relatórios PDF:** `python sections/report.py`

---

## 1. Direção Visual

O BudgetControl SaaS adota a linguagem visual **"Painel Operacional Corporativo"**, orientada a clareza financeira, leitura rápida de grandes volumes numéricos e baixa fadiga visual em jornadas longas de trabalho:

- **Sobriedade institucional:** predominância de azul-marinho profundo (`#12253f`) no cabeçalho e ações de navegação, contrastado com superfícies brancas (`#ffffff`) sobre fundo cinza-azulado suave (`#f4f7fb`).
- **Semântica objetiva por cor:** verde para ações de criação e status saudável; âmbar para atenção preventiva e setores; vermelho para estouro orçamentário e ações destrutivas; azul para edição e fornecedores; roxo para categorias/rubricas.
- **Precisão numérica:** valores monetários e percentuais usam `font-variant-numeric: tabular-nums` para alinhamento vertical perfeito em tabelas e KPIs.
- **Elevação contida:** bordas sutis de `1px` combinadas com sombras azuladas suaves (`rgba(15, 35, 59, ...)`) em vez de gradientes pesados ou efeitos chamativos.
- **Tema:** `color-scheme: light` como modo oficial do produto.

---

## 2. Paleta de Cores

### 2.1 Tokens Ativos da Interface Web (`style.css` — Bloco *Refinamento visual: painel operacional*)

> **Importante:** `python sections/static/css/style.css` possui um bloco `:root` inicial (linhas 4–32) com tokens legados e um bloco `:root` de refinamento visual (linhas 1316–1341) que **sobrescreve e define a paleta ativa em produção**. Toda nova feature deve respeitar os tokens ativos abaixo.

#### Cores de Marca e Ação
| Token CSS | Valor Hex | Uso Principal |
|---|---|---|
| `--primaria` | `#12253f` | Header principal, preset ativo, foco de navegação, links de mês |
| `--primaria-hover` | `#0b1a2d` | Hover de botões primários e seleção de texto |
| `--primaria-light` | `#e8f0f8` | Fundo de destaque suave, coluna ordenada ativa, botão de filtros ativo |
| `--verde` | `#16845b` | CTA "Nova Despesa", status *Dentro do orçamento*, avatar do usuário |
| `--verde-hover` | `#0f6b49` | Hover do CTA verde e texto de status positivo |
| `--verde-bg` | `#e5f5ed` | Fundo de badges/tags verdes e item destaque do menu |

#### Cores Semânticas e de Entidades
| Token CSS | Valor Hex | Uso Principal |
|---|---|---|
| `--vermelho` | `#c53a45` | Alerta *Acima do orçamento*, exclusão, hover do botão Sair |
| `--vermelho-bg` | `#fbeaec` | Fundo de tags de estouro, botões de exclusão e item perigoso no menu |
| `--azul` | `#2369a7` | Tags de **Fornecedor**, botão editar, borda de foco em inputs |
| `--azul-bg` | `#e6f0f8` | Fundo de `.badge-fornecedor` e `.btn-icone-edit` |
| `--roxo` | `#7c3aed` | Tags de **Categoria (Rubrica)** *(herdado do `:root` base)* |
| `--roxo-bg` | `#f3e8ff` | Fundo de `.badge-categoria` *(herdado do `:root` base)* |
| `--ambar` | `#a86012` | Tags de **Setor** / **Setor Destino** e alerta *Perto do orçamento* |
| `--ambar-bg` | `#fdf1df` | Fundo de `.badge-setor` e destaque preventivo |

#### Escala Neutra e Superfícies
| Token CSS | Valor Hex | Uso Principal |
|---|---|---|
| `--branco` | `#ffffff` | Superfície de cards, modais, toolbar, tabelas e inputs |
| *(body background)* | `#f4f7fb` | Fundo geral da aplicação |
| `--cinza-50` | `#f8fafc` | Superfícies secundárias e cabeçalhos sutis (`#f6f8fb` em `thead`) |
| `--cinza-100` | `#f1f5f9` | Fundos de agrupamento leve |
| `--cinza-200` | `#e2e8f0` | Bordas de cards, divisores, trilho da barra de progresso |
| `--cinza-300` | `#cbd5e1` | Bordas de inputs e botões outline |
| `--cinza-400` | `#64748b` | Placeholders, ícones secundários, textos auxiliares |
| `--cinza-600` | `#475569` | Subtítulos de KPI, cabeçalhos de tabela (`thead th`), descrições |
| `--cinza-700` | `#334155` | Textos de controles e labels |
| `--cinza-800` | `#172033` | Texto principal e títulos |

### 2.2 Paleta de Relatórios PDF (`python sections/report.py`)
Os PDFs gerados pelo ReportLab utilizam uma paleta de impressão de alto contraste dedicada:
- **Cabeçalho da tabela (`COR_PRIMARIA`):** `#DB7E04` (laranja corporativo)
- **Linha de totalização (`COR_PRIMARIA_E` / `COR_TOTAL_BG`):** `#B5670A` / `#FEF3E2`
- **Zebrado (`COR_ZEBRA`):** `#FFF8EE`
- **Grade (`COR_GRADE`):** `#E2E8F0`
- **Status no PDF:** OK `#DCFCE7` (texto `#166534`), Perto `#FEF3C7` (texto `#B45309`), Alerta `#FEE2E2` (texto `#991B1B`).

---

## 3. Tipografia

### 3.1 Família Tipográfica
- **Fonte primária:** `"Google Sans"` (auto-hospedada em `python sections/fonts/` e servida via `/fonts/` com `font-display: swap`).
- **Fallback:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`.
- **Cobertura total:** aplicada também a elementos nativos (`button`, `input`, `select`, `textarea`, `option`) e modais SweetAlert2 (`.swal2-*`).
- **PDFs:** mesma família *Google Sans* registrada no ReportLab via `python sections/pdf_fonts.py`.

### 3.2 Escala Tipográfica e Pesos
| Elemento | Tamanho | Peso | Tracking / Detalhes |
|---|---|---|---|
| Valor de KPI (`.card-valor`) | `1.65rem` (`1.3rem` mobile) | `700` | `letter-spacing: -0.025em`, `tabular-nums` |
| Título da marca no Header | `1.125rem` | `700` | `letter-spacing: -0.015em`, `line-height: 1.2` |
| Título de painel (`.painel-titulo-box h2`) | `1.06rem` | `700` | `letter-spacing: -0.012em` |
| Botão CTA / Padrão (`.btn`) | `0.84rem` – `0.88rem` | `600` – `700` | `white-space: nowrap` |
| Corpo / Células de tabela | `0.82rem` – `0.88rem` | `400` – `600` | `tabular-nums` nas tabelas |
| Labels e cabeçalhos de tabela (`thead th`, `.card-label`) | `0.72rem` – `0.78rem` | `600` – `700` | `uppercase`, `letter-spacing: 0.075em` |
| Badges, tags e subtítulos | `0.68rem` – `0.80rem` | `400` – `700` | `line-height: 1.25` – `1.45` |

---

## 4. Espaçamento, Grid e Responsividade

### 4.1 Container e Ritmo Espacial
- **Largura máxima:** `1360px` (`.header-content`, `.toolbar-container`, `main`), centralizado horizontalmente.
- **Escala base:** múltiplos de `0.25rem` (`4px`):
  - Micro (`0.25rem`–`0.5rem`): gaps de ícones, badges e botões compactos.
  - Padrão (`0.75rem`–`1rem`): padding interno de toolbar, inputs e itens de dropdown.
  - Seção (`1.125rem`–`1.5rem`): margens entre header, toolbar, grid de KPIs e painel da tabela.

### 4.2 Breakpoints Responsivos
| Breakpoint | Alvo | Comportamento |
|---|---|---|
| `> 768px` | Desktop | Layout completo até `1360px`, grid de KPIs em 4 colunas fluidas, barra de filtros em linha. |
| `≤ 768px` | Tablet / Mobile | Header com padding `1rem`, `.cards-grid` em `repeat(2, minmax(0, 1fr))`, `.card-valor` reduzido para `1.3rem`, `.painel-header` empilhado. |
| `≤ 480px` | Mobile compacto | Subtítulo do header oculto, `.cards-grid` em `1fr` (1 coluna), campos de filtro em `100%` de largura, `.view-btn` compacto (`0.72rem`). |

---

## 5. Raio de Borda e Elevação

### 5.1 Escala de `border-radius`
- **`4px`**: badges compactos de entidade na tabela (`.badge-setor`, `.badge-fornecedor`, `.badge-categoria`).
- **`6px`**: botões de ícone (`.btn-icone`), inputs internos de modal e controles compactos.
- **`8px` – `9px`**: botões padrão (`.btn`), CTA verde (`.btn-cadastrar-despesa`), inputs da toolbar (`.input-controle`, `.busca-input`), presets.
- **`10px` – `12px`**: ícones de KPI (`.card-icone`), logo do header (`.header-logo`), modais.
- **`14px` (`--radius`)**: superfícies principais (`.toolbar`, `.card`, `.painel-tabela`, `.dropdown-painel`).
- **`20px` / `99px` / `50%`**: pills (`.usuario-header-badge`, badges de status, barras de progresso) e avatares circulares.

### 5.2 Sombras (Elevação)
- **`--sombra`:** `0 1px 2px rgba(15, 35, 59, .05)` — cards em repouso.
- **`--sombra-md`:** `0 8px 20px rgba(15, 35, 59, .08)` — toolbar, painel da tabela e hover de cards.
- **`--sombra-lg`:** `0 20px 40px rgba(15, 35, 59, .14)` — modais e menu dropdown suspenso.

---

## 6. Catálogo de Componentes de UI

1. **Header Corporativo (`header`)**: logo + título/subtítulo à esquerda; à direita, CTA `+ Nova Despesa`, botão **Menu do Sistema** (dropdown categorizado em *Lançamentos & Cadastros* e *Relatórios & Manutenção*), badge do usuário autenticado (avatar com inicial, nome e tag `ADMIN`/`USUARIO`) e botão **Sair**.
2. **Toolbar de Filtros (`.toolbar`)**:
   - Linha principal: campos de data (*De* / *Até*), botão **Filtros** com contador dinâmico, botão **Limpar Filtros** e alternador de visão (**Resumida** / **Detalhada**).
   - Linha de atalhos: presets rápidos (`Este Mês`, `Mês Anterior`, `Este Ano`, `Ano Anterior`, `Todo o Período`).
   - Gaveta retrátil: selects de *Setor Responsável*, *Setor de Destino*, *Fornecedor* e *Categoria*.
3. **Cards de KPI (`.cards-grid` / `.card`)**: altura mínima `142px`, ícone contextual (`.card-icone`), rótulo em caixa alta, valor tabular em destaque, subtítulo e barra de progresso (`.prog-bar` / `.prog-fill`) no card de consumo.
4. **Painel de Tabela (`.painel-tabela`)**: cabeçalho com título/subtítulo, busca instantânea (`.busca-input`), controles de ordenação (coluna + direção) e botões de exportação (PDF, CSV, PNG); tabela com rolagem horizontal estilizada (`.tabela-scroll`), cabeçalhos clicáveis ordenáveis (`.th-sortable.sort-ativo`) e linhas com hover suave (`#f3f8fc`).
5. **Badges Semânticos**:
   - Entidades: `.badge-setor` (âmbar), `.badge-fornecedor` (azul), `.badge-categoria` (roxo).
   - Status orçamentário: verde (`< 80%`), âmbar (`80%–99%`), vermelho (`≥ 100%`).
6. **Botões**:
   - `.btn-cadastrar-despesa`: CTA sólido verde (`--verde`).
   - `.btn-primario`: ação principal azul-marinho (`--primaria`).
   - `.btn-outline`: ação secundária neutra.
   - `.btn-pdf`: exportação PDF (`#b91c1c`).
   - `.btn-icone-edit` / `.btn-icone-del` / `.btn-icone-key`: ações em linha na tabela (azul, vermelho, âmbar).
7. **Modais e Diálogos**:
   - Modais customizados de formulário/CRUD (Despesa, Setores, Fornecedores, Categorias, Orçamento por Setor com grade de 12 meses, Gestão de Usuários e Troca de Senha).
   - **SweetAlert2** (hospedado localmente em `static/js/sweetalert2.all.min.js` com fallback CDN) para confirmações destrutivas, feedback de sucesso/erro e escolha de escopo na exportação PNG.
8. **Telas de Autenticação (`login.html`, `redefinir_senha.html`)**: card centralizado branco sobre fundo primário escuro, campos com foco nítido e mensagens de alerta/sucesso inline.

---

## 7. Estados de Interface

| Estado | Comportamento Visual |
|---|---|
| **Hover** | Transição suave de `0.15s`–`0.18s ease`; cards elevam `-2px` com `--sombra-md`; linhas de tabela ganham fundo `#f3f8fc`; links de mês deslocam a seta `→` em `+3px`. |
| **Active / Selected** | Preset ativo usa `--primaria` com texto branco; botão de filtros aberto/ativo usa `--primaria-light` com borda `#aac6df`; coluna ordenada destaca `thead th.sort-ativo`. |
| **Focus Visible** | Global `:focus-visible` com `outline: 3px solid rgba(35, 105, 167, .35)` e `outline-offset: 2px`; inputs recebem borda `--azul` e halo `0 0 0 3px rgba(35, 105, 167, .13)`. |
| **Disabled** | Botões e campos desabilitados durante requisições de rede (evita duplo envio) ou quando o usuário não possui a permissão granular correspondente. |
| **Loading** | Feedback visual de carregamento ao consultar `/api/dados`, `/api/despesas` ou gerar exportações PDF/PNG. |
| **Empty State** | Mensagens claras na tabela quando nenhum lançamento ou orçamento corresponde aos filtros ativos. |
| **Error / Warning / Success** | Alertas modais ou toasts via SweetAlert2 utilizando as cores semânticas (`--vermelho`, `--ambar`, `--verde`). |

---

## 8. Acessibilidade (a11y)

### Práticas Implementadas
- **Foco visível consistente** via `:focus-visible` em toda a aplicação.
- **Navegação por teclado:** fechamento de dropdowns e modais com tecla `Esc`; salvamento na grade de orçamento com `Enter`.
- **Contraste adequado:** textos principais (`#172033`) sobre superfícies claras (`#ffffff` / `#f4f7fb`) e texto branco sobre `--primaria` (`#12253f`) atendem WCAG AA (`≥ 4.5:1`).
- **Atributos ARIA:** botões dinâmicos como `.link-mes-detalhe` recebem `aria-label` descritivo (ex.: `"Ver despesas detalhadas de Janeiro"`).
- **Semântica HTML5:** uso de `<header>`, `<main>`, `<table>`, `<thead>`, `<tbody>`, `<label>` e `<footer>`.

### Diretrizes Obrigatórias para Novas Implementações
1. Todo controle sem texto visível (botões de ícone) **deve** possuir `aria-label` e `title`.
2. Todo modal **deve** gerenciar foco ao abrir/fechar e suportar fechamento via `Esc`.
3. Nunca transmitir status orçamentário apenas por cor: manter sempre texto explícito (*Dentro do orçamento*, *Perto do orçamento*, *Acima do orçamento*) junto ao badge/cor.
4. Garantir `min-height ≥ 34px` em inputs/botões e área de toque adequada em viewports móveis (`≤ 768px`).
