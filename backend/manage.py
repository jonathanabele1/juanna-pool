"""Command-line account tools (run from the project root):

  python -m backend.manage create-user <username> [--admin] [--name "Display Name"]
  python -m backend.manage reset-password <username>
  python -m backend.manage list-users
"""
import argparse
import getpass

from . import auth, db


def _password() -> str:
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Again: "):
        raise SystemExit("Passwords don't match")
    if len(pw) < auth.MIN_PASSWORD:
        raise SystemExit(f"Password must be at least {auth.MIN_PASSWORD} characters")
    return pw


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-user")
    c.add_argument("username")
    c.add_argument("--admin", action="store_true")
    c.add_argument("--name", default="")
    r = sub.add_parser("reset-password")
    r.add_argument("username")
    sub.add_parser("list-users")
    a = ap.parse_args()

    if a.cmd == "create-user":
        u = db.create_user(a.username, a.name or a.username, auth.hash_password(_password()), a.admin)
        print(f"Created {u['username']} (id {u['id']}{', admin' if u['isAdmin'] else ''})")
    elif a.cmd == "reset-password":
        found = db.get_login(a.username)
        if not found:
            raise SystemExit("No such user")
        db.update_user(found[0]["id"], password_hash=auth.hash_password(_password()))
        db.delete_user_sessions(found[0]["id"])
        print("Password reset")
    else:
        for u in db.list_users():
            print(f"{u['id']:>3}  {u['username']:<16} {u['displayName']:<20} {'admin' if u['isAdmin'] else ''}"
                  f"{'' if u['active'] else ' (inactive)'}")


if __name__ == "__main__":
    main()
