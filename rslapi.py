import getpass
import requests
import urllib.parse
from datetime import datetime
import bs4
from pathlib import Path

requests.packages.urllib3.disable_warnings()


class ResilioSyncFolder(object):
    def __init__(self, folder_obj):
        self.data = folder_obj

        # first the straightforward copies
        self.name = folder_obj["name"]
        self.folderid = folder_obj["folderid"]

        # now for more complicated things
        self.path = None
        if "path" in folder_obj:
            self.path = Path(folder_obj["path"]).resolve()

        self.synclevel = folder_obj["synclevel"]
        self.selected = self.synclevel > 0

    def __repr__(self):
        return f'<ResilioSyncFolder "{self.name}">'


class ResilioSyncClient(object):
    def __init__(self, host, port, username, password):
        self.host, self.port = host, port
        self.api_url = f"http://{self.host}:{self.port}"
        self.username, self.password = username, password

        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.timeout = 1
        self.session.verify = False

        self.token = self.get_token()

    def format_timestamp(self):
        dt = datetime.utcnow() - datetime(1970, 1, 1)
        ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
        return int(ms)

    def normalize_path(self, path):
        return Path(path).absolute().resolve()

    def get_token(self):
        token_url = urllib.parse.urljoin(self.api_url, "gui/token.html")
        response = self.session.get(
            token_url, params={"t": self.format_timestamp()}, timeout=5
        )

        soup = bs4.BeautifulSoup(response.content, "lxml")
        token_divs = soup.select("#token")
        token = token_divs[0].decode_contents()
        return token

    def get_generic(self, params):
        response = self.session.get(
            urllib.parse.urljoin(self.api_url, "gui/"),
            params={"token": self.token, **params, "t": self.format_timestamp()},
            timeout=5,
        )

        return response.json()

    def get_folders(self):
        json = self.get_generic({"action": "getsyncfolders", "discovery": 1})
        assert json["status"] == 200
        return [ResilioSyncFolder(obj) for obj in json["folders"]]

    def get_folder_by_path(self, rel_path):
        abs_path = self.normalize_path(rel_path)
        folders = self.get_folders()
        containing_folders = []
        for folder in folders:
            if not folder.selected:
                continue
            if folder.path == abs_path or folder.path in abs_path.parents:
                containing_folders.append(folder)

        assert len(containing_folders) <= 1
        if not containing_folders:
            raise ValueError("Path is not contained in a synced folder.")

        return containing_folders[0]

    def file_exists(self, folder, path):
        assert folder.selected
        path = Path(path)
        if not path.is_absolute():
            path = folder.path / path

        abs_path = self.normalize_path(path)
        base_path = Path(".")

        while True:
            path_str = str(base_path)
            if base_path == Path("."):
                path_str = ""

            result = self.get_generic(
                {
                    "action": "getfileslist",
                    "folderid": folder.folderid,
                    "path": path_str,
                }
            )

            assert result["status"] == 200
            files = result["value"]["files"]
            for f in files:
                test_path = folder.path / base_path / f["name"]
                if test_path == abs_path:
                    return True

                if test_path in abs_path.parents:
                    base_path /= f["name"]
                    break
            else:
                return False

    def set_sync_status(self, rel_path, sync=True):
        # First, track down the parent folder, if it exists
        abs_path = self.normalize_path(rel_path)
        folder = self.get_folder_by_path(abs_path)
        child_rel_path = abs_path.relative_to(folder.path)

        # Now, check if the folder has our file
        if not self.file_exists(folder, child_rel_path):
            raise ValueError("Path does not exist in the folder!")

        self.get_generic(
            {
                "action": "setfilemode",
                "folderid": folder.folderid,
                "path": child_rel_path,
                "selected": "true" if sync else "false",
                "removefromall": "false",
            }
        )
