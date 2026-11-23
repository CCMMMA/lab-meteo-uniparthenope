#!/usr/bin/env python3
"""Provision local (NativeAuthenticator) accounts from the command line.

Run inside the Hub container; passwords are read from standard input, never from arguments:

    printf '%s\n' "$PASSWORD" | docker compose exec -T jupyterhub \
        python -m wxhub_ext.manage_users create alice --role researcher

Administrators are declared with ``WXHUB_ADMIN_USERS``; the ``admin`` role here only records the
intent and approves the local account. Roles other than ``user`` and ``admin`` are Hub groups.
"""

from __future__ import annotations

import argparse
import sys

import bcrypt
from jupyterhub import orm
from nativeauthenticator.orm import UserInfo

ROLE_GROUPS = ("students", "researchers", "instructors")
DB_URL = "sqlite:////srv/jupyterhub/data/jupyterhub.sqlite"
MIN_PASSWORD_LENGTH = 12


def session():
    return orm.new_session_factory(DB_URL)()


def read_password() -> str:
    password = sys.stdin.readline().rstrip("\n")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"password must have at least {MIN_PASSWORD_LENGTH} characters")
    return password


def ensure_hub_user(db, username: str, role: str):
    user = orm.User.find(db, username)
    if user is None:
        user = orm.User(name=username)
        db.add(user)
        db.commit()
    for group_name in ROLE_GROUPS:
        group = orm.Group.find(db, group_name)
        if group is None:
            group = orm.Group(name=group_name)
            db.add(group)
        if group_name == role and group not in user.groups:
            user.groups.append(group)
        elif group_name != role and group in user.groups:
            user.groups.remove(group)
    db.commit()
    return user


def create(args) -> None:
    db = session()
    username = args.username.strip().lower()
    password = read_password()
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    info = UserInfo.find(db, username)
    if info is None:
        info = UserInfo(username=username, password=hashed, is_authorized=True)
        db.add(info)
    elif not args.update:
        raise SystemExit(f"{username} already exists; pass --update to reset the password")
    else:
        info.password = hashed
        info.is_authorized = True
    db.commit()
    role = args.role if args.role in ROLE_GROUPS else None
    ensure_hub_user(db, username, role)
    print(f"{username}: local account ready (role: {args.role})")


def list_users(_args) -> None:
    db = session()
    for info in db.query(UserInfo).order_by(UserInfo.username):
        user = orm.User.find(db, info.username)
        groups = ",".join(sorted(g.name for g in user.groups)) if user else "-"
        admin = bool(user and user.admin)
        print(f"{info.username:24} approved={info.is_authorized!s:5} admin={admin!s:5} groups={groups}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    create_parser = sub.add_parser("create", help="create or reset an approved local account")
    create_parser.add_argument("username")
    create_parser.add_argument(
        "--role", default="user", choices=["user", "admin", *ROLE_GROUPS],
    )
    create_parser.add_argument("--update", action="store_true", help="reset an existing password")
    create_parser.set_defaults(func=create)
    list_parser = sub.add_parser("list", help="list local accounts")
    list_parser.set_defaults(func=list_users)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
