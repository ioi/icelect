#!/usr/bin/env python3
# Icelect - Administration script
# (c) 2025 Martin Mareš <mj@ucw.cz>

import argparse
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
import sys
from typing import NoReturn

from icelect.crypto import gen_key
import icelect.db as db
from icelect.election import ElectionConfig, ConfigError


def die(msg: str) -> NoReturn:
    print(msg, file=sys.stderr)
    sys.exit(1)


def cmd_create(args: argparse.Namespace):
    sess = db.get_session()

    try:
        ec = ElectionConfig.from_config_file(args.ident)
    except ConfigError as err:
        die(f'Cannot load configuration for election {args.ident}: {err}')

    elect = sess.scalar(select(db.Election).filter_by(ident=args.ident))
    if elect is not None:
        die(f'Election {args.ident} already exists.')

    elect = db.Election(
        ident=args.ident,
        state=db.ElectionState.init,
        config=ec.tree,
        election_key=gen_key(),
        verify_key=gen_key(),
    )
    sess.add(elect)
    sess.commit()


def cmd_update(args: argparse.Namespace):
    sess = db.get_session()

    try:
        ec = ElectionConfig.from_config_file(args.ident)
    except ConfigError as err:
        die(f'Cannot load configuration for election {args.ident}: {err}')

    elect = sess.scalar(select(db.Election).filter_by(ident=args.ident))
    if elect is None:
        die(f'Election {args.ident} does not exist.')

    if elect.state != db.ElectionState.init:
        die(f'Election {args.ident} is already running, cannot change its configuration.')

    elect.config=ec.tree
    sess.commit()


def obtain_election(ident: str) -> tuple[db.Election, ElectionConfig]:
    sess = db.get_session()
    elect = sess.scalar(select(db.Election).filter_by(ident=ident))
    if elect is None:
        die(f'Election {ident} does not exist.')

    ec = ElectionConfig(ident, elect.config)

    return elect, ec


def cmd_register(args: argparse.Namespace):
    elect, _ = obtain_election(args.ident)
    sess = db.get_session()

    hashes = []
    try:
        with open(f'etc/{args.ident}.h2') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    hashes.append(line)
    except FileNotFoundError:
        die(f'Cannot open etc/{args.ident}.h2')

    count_before = sess.scalar(select(func.count()).select_from(db.CredHash).filter_by(election_id=elect.election_id))

    for h2 in hashes:
        ins = (insert(db.CredHash)
               .values(election_id=elect.election_id, hash=h2)
               .on_conflict_do_nothing())
        sess.execute(ins)

    count_after = sess.scalar(select(func.count()).select_from(db.CredHash).filter_by(election_id=elect.election_id))
    sess.commit()

    print(f'Processed {len(hashes)} hashes. Registered voters: {count_before} before, {count_after} after.')



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Control elections",
    )

    subparsers = parser.add_subparsers(help='action to perform', dest='action', required=True, metavar='ACTION')

    create_parser = subparsers.add_parser('create',
                                          help='create a new election',
                                          description='Create a new election according to a configuration file etc/IDENT.toml')
    create_parser.add_argument('ident', help='alphanumeric identifier of the new election')
    create_parser.set_defaults(handler=cmd_create)

    update_parser = subparsers.add_parser('update',
                                          help='update an election',
                                          description='Update election configuration according to etc/IDENT.toml')
    update_parser.add_argument('ident', help='alphanumeric identifier of the election')
    update_parser.set_defaults(handler=cmd_update)

    register_parser = subparsers.add_parser('register',
                                            help='register voters',
                                            description='Register voters to an election according to etc/IDENT.h2')
    register_parser.add_argument('ident', help='alphanumeric identifier of the election')
    register_parser.set_defaults(handler=cmd_register)

    args = parser.parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
