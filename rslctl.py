import appdirs
import argparse
import os

import base64
import shelve
import getpass
import json

from pathlib import Path
import rslapi


def main(args):
    conf_root = Path(appdirs.user_config_dir("rslctl", "PythonNut"))
    conf_file_path = conf_root / "config.json"
    conf_root.mkdir(exist_ok=True)

    cwd = Path(os.environ["CWD"])

    if not conf_file_path.exists():
        host = input("host [localhost]: ") or "localhost"
        port = input("port [8888]: ") or 8888
        username = input("username: ")
        password = base64.b64encode(
            getpass.getpass("password: ").encode("utf-8")
        ).decode("utf-8")
        with open(conf_file_path, "w") as f:
            json.dump(
                {
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": password,
                },
                f,
            )

    with open(conf_file_path) as f:
        config = json.load(f)

    api = rslapi.ResilioSyncClient(
        host=config["host"],
        port=config["port"],
        username=config["username"],
        password=base64.b64decode(config["password"]).decode("utf-8"),
    )

    if args.parser == "parser_select":
        for f in args.file:
            api.set_sync_status(cwd / f, True)
    elif args.parser == "parser_unselect":
        for f in args.file:
            api.set_sync_status(cwd / f, False)


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
