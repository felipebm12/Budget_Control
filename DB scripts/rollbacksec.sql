-- ============================================================
-- REVERSÃO: DESFAZ TODAS AS MELHORIAS DE MODELAGEM
-- Sistema de Orçamento e Despesas (PostgreSQL)
-- ============================================================
-- Reverte o script de migração completo:
--   1. Remove trigger e função de auditoria
--   2. Remove tabela despesas_auditoria
--   3. Remove FK e coluna orcamento_mensal_id
--   4. Remove CHECKs de valores positivos
--   5. Remove índices de performance
--   6. Remove NOT NULL de rubrica_id/setor_id
--   7. Remove constraint de unicidade
-- ============================================================
-- ATENÇÃO: A exclusão de registros duplicados feita na migração
-- (DELETE em orcamentos_mensais) NÃO pode ser revertida — dados
-- apagados não voltam. Este script reverte apenas a estrutura.
-- ============================================================

BEGIN;

-- ============================================================
-- 1. REMOVER TRIGGER E FUNÇÃO DE AUDITORIA
-- ============================================================

DROP TRIGGER IF EXISTS trg_despesas_auditoria ON despesas;

DROP FUNCTION IF EXISTS fn_auditar_despesa();

-- ============================================================
-- 2. REMOVER TABELA DE AUDITORIA
-- ============================================================

DROP TABLE IF EXISTS despesas_auditoria;

-- ============================================================
-- 3. REMOVER FK E COLUNA ORCAMENTO_MENSAL_ID
-- ============================================================

-- Remove a coluna (a FK é removida automaticamente junto)
ALTER TABLE despesas DROP COLUMN IF EXISTS orcamento_mensal_id;

-- ============================================================
-- 4. REMOVER CHECKS DE VALORES POSITIVOS
-- ============================================================

ALTER TABLE despesas
  DROP CONSTRAINT IF EXISTS chk_despesas_valor_positivo;

ALTER TABLE orcamentos_mensais
  DROP CONSTRAINT IF EXISTS chk_orcamento_valor_positivo;

ALTER TABLE orcamentos_anuais
  DROP CONSTRAINT IF EXISTS chk_orcamento_anual_valor_positivo;

-- ============================================================
-- 5. REMOVER ÍNDICES DE PERFORMANCE
-- ============================================================

DROP INDEX IF EXISTS idx_despesas_data_compra;
DROP INDEX IF EXISTS idx_despesas_rubrica_id;
DROP INDEX IF EXISTS idx_despesas_setor_id;
DROP INDEX IF EXISTS idx_despesas_rubrica_data;
DROP INDEX IF EXISTS idx_despesas_setor_data;
DROP INDEX IF EXISTS idx_despesas_data_compra_mes;

-- ============================================================
-- 6. REMOVER NOT NULL DE RUBRICA_ID / SETOR_ID
-- (volta a permitir despesas sem classificação)
-- ============================================================

ALTER TABLE despesas ALTER COLUMN rubrica_id DROP NOT NULL;
ALTER TABLE despesas ALTER COLUMN setor_id DROP NOT NULL;

-- ============================================================
-- 7. REMOVER CONSTRAINT DE UNICIDADE
-- (volta a permitir mais de um orçamento por mês/ano)
-- ============================================================

ALTER TABLE orcamentos_mensais
  DROP CONSTRAINT IF EXISTS uq_orcamento_mensal_anual_mes;

-- ============================================================
-- 8. RESUMO DA REVERSÃO
-- ============================================================

-- Confirma que tudo foi removido (deve retornar 0 em todas as colunas)
SELECT
  (SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_despesas_auditoria') AS trigger_auditoria,
  (SELECT count(*) FROM pg_proc WHERE proname = 'fn_auditar_despesa') AS funcao_auditoria,
  (SELECT count(*) FROM pg_tables WHERE tablename = 'despesas_auditoria') AS tabela_auditoria,
  (SELECT count(*) FROM information_schema.columns WHERE table_name = 'despesas' AND column_name = 'orcamento_mensal_id') AS coluna_fk,
  (SELECT count(*) FROM pg_constraint WHERE conname LIKE 'chk_%_valor_positivo') AS checks_valores,
  (SELECT count(*) FROM pg_indexes WHERE indexname LIKE 'idx_despesas_%') AS indices_despesas,
  (SELECT count(*) FROM pg_constraint WHERE conname = 'uq_orcamento_mensal_anual_mes') AS constraint_unicidade;

COMMIT;