"""
CLI de gestión del usuario administrador.

Uso:
    python scripts/manage_admin.py info               # Muestra info del admin
    python scripts/manage_admin.py reset-password     # Genera contraseña nueva
    python scripts/manage_admin.py set-password X     # Setea contraseña a X
    python scripts/manage_admin.py create-if-missing  # Crea admin si no existe

Sin FLASK_DEBUG ni servidor corriendo — opera directo sobre la DB.
"""
import argparse
import os
import secrets
import string
import sys

import sqlite3
from werkzeug.security import generate_password_hash


def find_db():
    """Busca la DB de la app. Prioridad: env DB_PATH, luego rutas comunes."""
    env_path = os.environ.get('DB_PATH')
    if env_path and os.path.exists(env_path):
        return env_path
    for p in ('instance/database.db', 'database.db', 'app.db'):
        if os.path.exists(p):
            return p
    sys.exit("No se encontró la DB. Setear DB_PATH o ejecutar desde la raíz del proyecto.")


def get_admin(conn):
    """Devuelve el primer usuario con role='admin' o None."""
    row = conn.execute(
        "SELECT id, username, email, role, is_active FROM users WHERE role='admin' LIMIT 1"
    ).fetchone()
    return row


def generate_password(length=16):
    """Genera una contraseña legible (sin caracteres ambiguos)."""
    alphabet = ''.join(c for c in string.ascii_letters + string.digits if c not in 'O0Il1')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def cmd_info(args):
    conn = sqlite3.connect(args.db)
    try:
        admin = get_admin(conn)
        if not admin:
            print("No existe ningún usuario con role='admin'.")
            return 1
        print(f"Admin encontrado:")
        print(f"  id       : {admin[0]}")
        print(f"  username : {admin[1]}")
        print(f"  email    : {admin[2]}")
        print(f"  role     : {admin[3]}")
        print(f"  is_active: {admin[4]}")
        if not admin[4]:
            print("\n⚠️  El admin está INACTIVO. Activá con:")
            print("    python scripts/manage_admin.py activate")
        return 0
    finally:
        conn.close()


def cmd_reset_password(args):
    conn = sqlite3.connect(args.db)
    try:
        admin = get_admin(conn)
        if not admin:
            print("No existe ningún admin. Usá 'create-if-missing' primero.")
            return 1
        new_pwd = args.password or generate_password()
        new_hash = generate_password_hash(new_pwd)
        conn.execute(
            "UPDATE users SET hash = ?, is_active = 1 WHERE id = ?",
            (new_hash, admin[0]),
        )
        conn.commit()
        print(f"✓ Contraseña del admin '{admin[1]}' reseteada.")
        print(f"  username: {admin[1]}")
        print(f"  password: {new_pwd}")
        print(f"\n⚠️  Guardala ahora — no se vuelve a mostrar.")
        return 0
    finally:
        conn.close()


def cmd_set_password(args):
    if not args.password or len(args.password) < 6:
        sys.exit("La contraseña debe tener al menos 6 caracteres.")
    conn = sqlite3.connect(args.db)
    try:
        admin = get_admin(conn)
        if not admin:
            print("No existe ningún admin. Usá 'create-if-missing' primero.")
            return 1
        new_hash = generate_password_hash(args.password)
        conn.execute(
            "UPDATE users SET hash = ?, is_active = 1 WHERE id = ?",
            (new_hash, admin[0]),
        )
        conn.commit()
        print(f"✓ Contraseña del admin '{admin[1]}' actualizada.")
        return 0
    finally:
        conn.close()


def cmd_create_if_missing(args):
    conn = sqlite3.connect(args.db)
    try:
        admin = get_admin(conn)
        if admin:
            print(f"Ya existe admin '{admin[1]}'. No se creó nada.")
            return 0
        pwd = args.password or generate_password()
        username = args.username
        email = args.email
        conn.execute(
            "INSERT INTO users (username, email, hash, role, is_active) VALUES (?, ?, ?, 'admin', 1)",
            (username, email, generate_password_hash(pwd)),
        )
        conn.commit()
        print(f"✓ Admin creado.")
        print(f"  username: {username}")
        print(f"  email   : {email}")
        print(f"  password: {pwd}")
        return 0
    finally:
        conn.close()


def cmd_activate(args):
    conn = sqlite3.connect(args.db)
    try:
        admin = get_admin(conn)
        if not admin:
            print("No existe ningún admin.")
            return 1
        conn.execute("UPDATE users SET is_active = 1 WHERE id = ?", (admin[0],))
        conn.commit()
        print(f"✓ Admin '{admin[1]}' activado.")
        return 0
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Gestión del usuario administrador")
    parser.add_argument('--db', default=None, help='Path a la DB (default: autodetecta)')
    sub = parser.add_subparsers(dest='cmd', required=True)

    sub.add_parser('info', help='Muestra info del admin actual')

    p_reset = sub.add_parser('reset-password', help='Genera una contraseña nueva')
    p_reset.add_argument('--password', default=None, help='Si se omite, se genera una aleatoria')

    p_set = sub.add_parser('set-password', help='Setea la contraseña a un valor explícito')
    p_set.add_argument('password', help='Nueva contraseña (mínimo 6 chars)')

    p_create = sub.add_parser('create-if-missing', help='Crea admin si no existe ninguno')
    p_create.add_argument('--username', default='admin', help='Username (default: admin)')
    p_create.add_argument('--email', default='admin@archestate.local', help='Email')
    p_create.add_argument('--password', default=None, help='Password (auto si se omite)')

    sub.add_parser('activate', help='Activa la cuenta admin si está inactiva')

    args = parser.parse_args()
    if not args.db:
        args.db = find_db()

    if not os.path.exists(args.db):
        sys.exit(f"DB no existe: {args.db}")

    handlers = {
        'info': cmd_info,
        'reset-password': cmd_reset_password,
        'set-password': cmd_set_password,
        'create-if-missing': cmd_create_if_missing,
        'activate': cmd_activate,
    }
    sys.exit(handlers[args.cmd](args))


if __name__ == '__main__':
    main()
