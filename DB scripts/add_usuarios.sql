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
    email           varchar(255),
    senha_hash      varchar(255) NOT NULL,
    nome_completo   varchar(100) NOT NULL DEFAULT '',
    tipo            varchar(20)  NOT NULL DEFAULT 'usuario'
                    CHECK (tipo IN ('admin', 'usuario')),
    ativo           boolean      NOT NULL DEFAULT true,
    permissoes      jsonb        NOT NULL DEFAULT '{}'::jsonb,
    criado_em       timestamptz  NOT NULL DEFAULT now(),
    ultimo_acesso   timestamptz
);

-- Garante as colunas de permissões e e-mail caso a tabela já tenha sido criada anteriormente
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS permissoes jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email varchar(255);

-- Índices para busca rápida por username e unicidade de e-mail
CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios (username);
CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email_unique ON usuarios (LOWER(email)) WHERE email IS NOT NULL AND email <> '';

-- ============================================================
-- 1.1. TABELA DE TOKENS DE RECUPERAÇÃO DE SENHA (MAGIC LINK)
-- ============================================================

CREATE TABLE IF NOT EXISTS tokens_recuperacao_senha (
    id              integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id      integer NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_hash      varchar(64) NOT NULL UNIQUE,
    expira_em       timestamptz NOT NULL,
    usado_em        timestamptz,
    ip_solicitante  varchar(64),
    criado_em       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tokens_recuperacao_hash ON tokens_recuperacao_senha (token_hash);
CREATE INDEX IF NOT EXISTS idx_tokens_recuperacao_usuario ON tokens_recuperacao_senha (usuario_id);

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
    (SELECT count(*) FROM pg_tables WHERE tablename = 'tokens_recuperacao_senha') AS tabela_tokens_criada,
    (SELECT count(*) FROM usuarios WHERE username = 'admin')         AS admin_criado,
    (SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_usuarios_username') AS indice_criado;

COMMIT;
