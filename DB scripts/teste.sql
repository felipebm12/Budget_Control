SELECT
  (SELECT count(*) FROM pg_constraint WHERE conname = 'uq_orcamento_mensal_anual_mes') AS constraint_unicidade,
  (SELECT count(*) FROM pg_indexes WHERE indexname LIKE 'idx_despesas_%') AS indices_despesas,
  (SELECT count(*) FROM pg_constraint WHERE conname LIKE 'chk_%_valor_positivo') AS checks_valores,
  (SELECT count(*) FROM pg_tables WHERE tablename = 'despesas_auditoria') AS tabela_auditoria,
  (SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_despesas_auditoria') AS trigger_auditoria;