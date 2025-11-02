#!/usr/bin/env python3
"""Create an admin user for the Forensic app.

Run from the project root after installing requirements and setting up the environment:

    python scripts/create_admin.py --username admin --password secret

"""
import argparse
import sys

sys.path.insert(0, '.')

from app import app
from src.auth import db, User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()

    with app.app_context():
        db.create_all()
        existing = User.query.filter_by(username=args.username).first()
        if existing:
            print('User already exists:', args.username)
            return
        user = User(username=args.username)
        user.set_password(args.password)
        db.session.add(user)
        db.session.commit()
        print('Created user', args.username)


if __name__ == '__main__':
    main()
