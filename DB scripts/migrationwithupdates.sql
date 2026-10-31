-- ANTES DE TUDO, VASCO DA GAMA!, depois um pai nosso pra isso dar certo 
--
-- ============================================================
-- MIGRAÇÃO: MELHORIAS DE MODELAGEM (VERSÃO COMPLETA - APLICAÇÃO IMEDIATA)
-- Sistema de Orçamento e Despesas (PostgreSQL)
-- ============================================================
-- Este script aplica TODAS as melhorias sem necessidade de descomentar:
--   1. Unicidade em orcamentos_mensais (ano + mês)
--   2. Obrigatoriedade de classificação (rubrica/setor)
--   3. Índices de performance
--   4. Validação de valores positivos (CHECK)
--   5. FK despesa -> orçamento mensal (opcional, incluído)
--   6. Tabela de auditoria (opcional, incluída)
-- ============================================================

BEGIN;

-- ============================================================
-- 1. UNICIDADE EM ORCAMENTOS_MENSAIS
-- ============================================================

-- 1.1 Remove duplicatas existentes (mantém o registro mais antigo de cada ano+mês)
DELETE FROM orcamentos_mensais a
USING orcamentos_mensais b
WHERE a.orcamento_anual_id = b.orcamento_anual_id
  AND a.mes = b.mes
  AND a.id > b.id;

-- 1.2 Cria a constraint de unicidade
ALTER TABLE orcamentos_mensais
  ADD CONSTRAINT uq_orcamento_mensal_anual_mes
  UNIQUE (orcamento_anual_id, mes);

-- ============================================================
-- 2. OBRIGATORIEDADE DE CLASSIFICAÇÃO (rubrica/setor)
-- ============================================================

-- 2.1 Identifica despesas sem classificação para revisão
-- (Se houver linhas, decida: preencher, excluir ou manter antes de prosseguir)
SELECT id, descricao, valor, data_compra
FROM despesas
WHERE rubrica_id IS NULL OR setor_id IS NULL;

-- 2.2 Aplica NOT NULL
ALTER TABLE despesas ALTER COLUMN rubrica_id SET NOT NULL;
ALTER TABLE despesas ALTER COLUMN setor_id SET NOT NULL;

-- ============================================================
-- 3. ÍNDICES DE PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_despesas_data_compra
  ON despesas (data_compra);

CREATE INDEX IF NOT EXISTS idx_despesas_rubrica_id
  ON despesas (rubrica_id);

CREATE INDEX IF NOT EXISTS idx_despesas_setor_id
  ON despesas (setor_id);

CREATE INDEX IF NOT EXISTS idx_despesas_fornecedor_id
  ON despesas (fornecedor_id);

-- Índices compostos para as consultas mais comuns
CREATE INDEX IF NOT EXISTS idx_despesas_rubrica_data
  ON despesas (rubrica_id, data_compra);

CREATE INDEX IF NOT EXISTS idx_despesas_setor_data
  ON despesas (setor_id, data_compra);

-- Índice para o comparativo gasto x orçado (por mês/ano)
CREATE INDEX IF NOT EXISTS idx_despesas_data_compra_mes
  ON despesas (EXTRACT(YEAR FROM data_compra), EXTRACT(MONTH FROM data_compra));

-- ============================================================
-- 4. VALIDAÇÃO DE VALORES POSITIVOS (CHECK)
-- ============================================================

-- 4.1 Verifica valores negativos existentes (deve retornar vazio)
SELECT 'despesas' AS tabela, id, valor FROM despesas WHERE valor < 0
UNION ALL
SELECT 'orcamentos_mensais', id, valor FROM orcamentos_mensais WHERE valor < 0;

-- 4.2 Aplica os CHECKs
ALTER TABLE despesas
  ADD CONSTRAINT chk_despesas_valor_positivo CHECK (valor >= 0);

ALTER TABLE orcamentos_mensais
  ADD CONSTRAINT chk_orcamento_valor_positivo CHECK (valor >= 0);

ALTER TABLE orcamentos_anuais
  ADD CONSTRAINT chk_orcamento_anual_valor_positivo
  CHECK (valor_orcado IS NULL OR valor_orcado >= 0);

-- ============================================================
-- 5. FK DESPESA -> ORÇAMENTO MENSAL (opcional, incluído)
-- ============================================================

-- 5.1 Adiciona a coluna
ALTER TABLE despesas
  ADD COLUMN orcamento_mensal_id integer REFERENCES orcamentos_mensais(id);

-- 5.2 Índice para a nova FK
CREATE INDEX IF NOT EXISTS idx_despesas_orcamento_mensal_id
  ON despesas (orcamento_mensal_id);

-- ============================================================
-- 6. TABELA DE AUDITORIA (opcional, incluída)
-- ============================================================

CREATE TABLE IF NOT EXISTS despesas_auditoria (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  despesa_id integer NOT NULL REFERENCES despesas(id) ON DELETE CASCADE,
  acao character varying(10) NOT NULL CHECK (acao IN ('INSERT', 'UPDATE', 'DELETE')),
  dados_anteriores jsonb,
  dados_novos jsonb,
  usuario text,
  data_alteracao timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_despesas_auditoria_despesa
  ON despesas_auditoria (despesa_id);

-- ============================================================
-- 7. TRIGGERS DE AUDITORIA (opcional, incluído)
-- Registra automaticamente INSERT, UPDATE e DELETE em despesas
-- ============================================================

-- 7.1 Função de auditoria
CREATE OR REPLACE FUNCTION fn_auditar_despesa()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO despesas_auditoria (despesa_id, acao, dados_novos, usuario)
    VALUES (NEW.id, 'INSERT', to_jsonb(NEW), current_user);
    RETURN NEW;
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO despesas_auditoria (despesa_id, acao, dados_anteriores, dados_novos, usuario)
    VALUES (NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), current_user);
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO despesas_auditoria (despesa_id, acao, dados_anteriores, usuario)
    VALUES (OLD.id, 'DELETE', to_jsonb(OLD), current_user);
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 7.2 Triggers na tabela despesas
DROP TRIGGER IF EXISTS trg_despesas_auditoria ON despesas;
CREATE TRIGGER trg_despesas_auditoria
  AFTER INSERT OR UPDATE OR DELETE ON despesas
  FOR EACH ROW EXECUTE FUNCTION fn_auditar_despesa();

-- ============================================================
-- 8. RESUMO DAS ALTERAÇÕES APLICADAS
-- ============================================================

-- Confirmação visual do que foi aplicado
SELECT
  (SELECT count(*) FROM pg_constraint WHERE conname = 'uq_orcamento_mensal_anual_mes') AS constraint_unicidade,
  (SELECT count(*) FROM pg_indexes WHERE indexname LIKE 'idx_despesas_%') AS indices_despesas,
  (SELECT count(*) FROM pg_constraint WHERE conname LIKE 'chk_%_valor_positivo') AS checks_valores,
  (SELECT count(*) FROM pg_tables WHERE tablename = 'despesas_auditoria') AS tabela_auditoria,
  (SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_despesas_auditoria') AS trigger_auditoria;

COMMIT;