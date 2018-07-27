#!/usr/bin/env python
import argparse
import base64
import shelve
import getpass

from pathlib import Path
import rslapi

PERSIST_PATH = "./data.bin"


def main(args):
    persist = shelve.open(PERSIST_PATH, writeback=True)
    if "username" not in persist or "password" not in persist:
        persist["username"] = input("username: ")
        persist["password"] = base64.b64encode(
            getpass.getpass("password: ").encode("utf-8")
        )

    username = persist["username"]
    password = base64.b64decode(persist["password"]).decode("utf-8")

    api = rslapi.ResilioSyncClient(username, password)

    if args.parser == "parser_select":
        for f in args.file:
            api.set_sync_status(f, True)
    elif args.parser == "parser_unselect":
        for f in args.file:
            api.set_sync_status(f, False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Control Resilio Sync.")
    subparsers = parser.add_subparsers(help="subcommands")

    parser_select = subparsers.add_parser("select", help="select a file")
    parser_select.add_argument("file", type=str, nargs="+", help="file to select")
    parser_select.set_defaults(parser="parser_select")

    parser_unselect = subparsers.add_parser("unselect", help="unselect a file")
    parser_unselect.add_argument("file", type=str, nargs="+", help="file to select")
    parser_unselect.set_defaults(parser="parser_unselect")

    args = parser.parse_args()
    main(args)
