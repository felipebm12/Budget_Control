"""
Redefine a senha de um usuário (padrão: admin) sem precisar estar logado.

Uso, na pasta python sections, com o .env configurado:

    python reset_senha.py
    python reset_senha.py --usuario admin

A nova senha é pedida no terminal (não aparece na tela nem no histórico de comandos).
"""
from __future__ import annotations

import argparse
import getpass
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Redefine a senha de um usuário do BudgetControl (recuperação de acesso)."
    )
    parser.add_argument(
        "--usuario",
        default="admin",
        help="Nome de usuário cuja senha será redefinida (padrão: admin).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    usuario = (args.usuario or "").strip()
    if not usuario:
        print("Informe um nome de usuário válido.")
        sys.exit(1)

    print("=" * 56)
    print("  BudgetControl — redefinição de senha")
    print("=" * 56)
    print(f"Usuário: {usuario}")
    print("A senha precisa ter no mínimo 8 caracteres.")
    print()

    try:
        nova = getpass.getpass("Nova senha: ")
        confirmacao = getpass.getpass("Confirme a nova senha: ")
    except (EOFError, KeyboardInterrupt):
        print("\nOperação cancelada.")
        sys.exit(1)

    if not nova or not confirmacao:
        print("A senha não pode ficar em branco.")
        sys.exit(1)
    if nova != confirmacao:
        print("A senha e a confirmação não conferem.")
        sys.exit(1)

    # Importação adiada: config.py encerra o processo se o .env estiver incompleto.
    import database

    try:
        resultado = database.redefinir_senha_por_username(usuario, nova)
    except ValueError as ve:
        print(f"Não foi possível redefinir: {ve}")
        sys.exit(1)
    except Exception as e:
        print(f"Falha ao acessar o banco: {e}")
        sys.exit(1)

    print("-" * 56)
    print(f"Senha redefinida para '{resultado['username']}' ({resultado['tipo']}).")
    print("Faça login em http://127.0.0.1:5000/login")
    print("=" * 56)


if __name__ == "__main__":
    main()
