-- ============================================================
-- MIGRAÇÃO: SISTEMA DE AUTENTICAÇÃO DE USUÁRIOS
-- BudgetControl — Sistema de Controle Orçamentário
-- ============================================================
-- Execute este script no SQL Editor do Supabase (ou psql)
-- ANTES de reiniciar o servidor Flask.
-- ============================================================

BEGIN;

-- ============================================================
-- 1. TABELA DE USUÁRIOS
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id              integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username        varchar(50)  NOT NULL UNIQUE,
    senha_hash      varchar(255) NOT NULL,
    nome_completo   varchar(100) NOT NULL DEFAULT '',
    tipo            varchar(20)  NOT NULL DEFAULT 'usuario'
                    CHECK (tipo IN ('admin', 'usuario')),
    ativo           boolean      NOT NULL DEFAULT true,
    criado_em       timestamptz  NOT NULL DEFAULT now(),
    ultimo_acesso   timestamptz
);

-- Índice para busca rápida por username (usado no login)
CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios (username);

-- ============================================================
-- 2. USUÁRIO ADMIN INICIAL
-- Senha: Admin@2026  (hash bcrypt rounds=12)
-- IMPORTANTE: Troque a senha após o primeiro acesso!
-- ============================================================

INSERT INTO usuarios (username, senha_hash, nome_completo, tipo)
VALUES (
    'admin',
    '$2b$12$TSRXe0YOedg7P3hEyYPT..opCzIbv2A8d1ahBhCXwJ1kK.3bDLihS',
    'Administrador',
    'admin'
)
ON CONFLICT (username) DO NOTHING;

-- ============================================================
-- 3. VERIFICAÇÃO
-- ============================================================

SELECT
    (SELECT count(*) FROM pg_tables WHERE tablename = 'usuarios')   AS tabela_criada,
    (SELECT count(*) FROM usuarios WHERE username = 'admin')         AS admin_criado,
    (SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_usuarios_username') AS indice_criado;

COMMIT;
