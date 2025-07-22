#!/usr/bin/env python3
# Icelect - Voter credential generator
# (c) 2025 Martin Mareš <mj@ucw.cz>

import argparse

from icelect.crypto import gen_credential, cred_to_h1, h1_to_h2


def main() -> None:
    parser = argparse.ArgumentParser(
        description="""
    Generate voter credentials.
    Produces: OUTPUT.cred (credentials to distribute to the voters and then discard),
    OUTPUT.h1 (credential hashes to keep), and
    OUTPUT.h2 (credential hashes to upload to the election server).
    """
    )

    parser.add_argument('--count', '-c', type=int, required=True, help="number of voters")
    parser.add_argument('--output', '-o', required=True, help="base name of generated files")

    args = parser.parse_args()

    creds = [gen_credential() for _ in range(args.count)]
    assert len(creds) == len(set(creds))

    with open(args.output + '.cred', 'w') as out_cred:
        with open(args.output + '.h1', 'w') as out_h1:
            with open(args.output + '.h2', 'w') as out_h2:
                for cred in creds:
                    print(cred, file=out_cred)
                    h1 = cred_to_h1(cred)
                    h2 = h1_to_h2(h1)
                    print(h1, file=out_h1)
                    print(h2, file=out_h2)


if __name__ == '__main__':
    main()
