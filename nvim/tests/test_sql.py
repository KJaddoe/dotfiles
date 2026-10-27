#!/usr/bin/env python3
"""Tests for the pure helpers of nvim/config/lua/user/sql.lua.

Each case calls one helper in a headless `nvim --clean` with the repo's config on the
runtimepath and compares its JSON-encoded results, so no plugin or database is needed. The
interactive half of the module (prompts, vim-dadbod, the server) is checked end to end instead.
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "nvim" / "config"

PROBE = """
vim.opt.runtimepath:prepend(arg[1])
local call = vim.json.decode(arg[2], { luanil = { object = true, array = true } })
local results = vim.F.pack_len(require("user.sql")[call.fn](unpack(call.args, 1, call.n)))
local out = {}
for i = 1, results.n do
  out[i] = results[i] == nil and vim.NIL or results[i]
end
io.stdout:write(vim.json.encode(out))
"""


def nvim_missing():
    """True when this environment cannot run the suite at all."""
    return not (shutil.which("nvim") and CONFIG.is_dir())


@unittest.skipIf(nvim_missing(), "nvim or the repo config is unavailable")
class SqlCase(unittest.TestCase):
    """Base case that calls one user.sql helper in headless nvim."""

    probe = None

    @classmethod
    def setUpClass(cls):
        """Write the probe script once per class."""
        work = Path(tempfile.mkdtemp())
        cls.addClassCleanup(shutil.rmtree, work, ignore_errors=True)
        cls.probe = work / "probe.lua"
        cls.probe.write_text(PROBE, encoding="utf-8")

    def call(self, fn, *args):
        """Call user.sql's `fn` with `args`; return its results as a list, nil as None."""
        payload = json.dumps({"fn": fn, "n": len(args), "args": list(args)})
        result = subprocess.run(
            ["nvim", "--clean", "-l", str(self.probe), str(CONFIG), payload],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            self.fail(f"{fn} raised:\n{result.stderr[-2000:]}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return self.fail(
                f"{fn} printed non-JSON:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
            )


def conn(**fields):
    """A SQL Server connection table with test defaults, overridable per field."""
    return {"engine": "sqlserver", "host": "localhost", "user": "sa", "password": "pw", **fields}


class BuildUrl(SqlCase):
    """build_url turns a connection into the URL vim-dadbod expects."""

    def test_sqlserver_with_database(self):
        """The plain SQL Server form."""
        self.assertEqual(
            self.call("build_url", conn(database="app")), ["sqlserver://sa:pw@localhost/app"]
        )

    def test_reserved_characters_are_encoded(self):
        """User, password and database survive every URL delimiter and a space."""
        url = self.call(
            "build_url",
            conn(host="db", user="d@m:n", password="p@ss:w/rd%#? x", database="my db-1"),
        )
        self.assertEqual(url, ["sqlserver://d%40m%3An:p%40ss%3Aw%2Frd%25%23%3F%20x@db/my%20db-1"])

    def test_password_cannot_redirect_the_host(self):
        """A password shaped like a host part stays inside the userinfo."""
        url = self.call("build_url", conn(host="db", password="x@evil.example.com/"))
        self.assertEqual(url, ["sqlserver://sa:x%40evil.example.com%2F@db"])

    def test_database_cannot_add_parameters(self):
        """A database name shaped like a query string cannot switch on trust."""
        url = self.call("build_url", conn(database="app?trustServerCertificate=true#"))
        self.assertEqual(
            url, ["sqlserver://sa:pw@localhost/app%3FtrustServerCertificate%3Dtrue%23"]
        )

    def test_port(self):
        """A port follows the host."""
        self.assertEqual(
            self.call("build_url", conn(host="db", port="1433", database="app")),
            ["sqlserver://sa:pw@db:1433/app"],
        )

    def test_sqlserver_without_database(self):
        """SQL Server may connect to the login's default database."""
        self.assertEqual(self.call("build_url", conn()), ["sqlserver://sa:pw@localhost"])

    def test_without_password(self):
        """A nil password leaves no colon behind."""
        self.assertEqual(
            self.call("build_url", conn(password=None, database="app")),
            ["sqlserver://sa@localhost/app"],
        )

    def test_trust(self):
        """trust adds the certificate parameter vim-dadbod maps to -C."""
        self.assertEqual(
            self.call("build_url", conn(database="app", trust=True)),
            ["sqlserver://sa:pw@localhost/app?trustServerCertificate=true"],
        )

    def test_postgresql_falls_back_to_postgres(self):
        """PostgreSQL needs a database to connect, so none means postgres."""
        self.assertEqual(
            self.call("build_url", conn(engine="postgresql", user="postgres")),
            ["postgresql://postgres:pw@localhost/postgres"],
        )

    def test_postgresql_ignores_trust(self):
        """trust is a SQL Server setting only."""
        self.assertEqual(
            self.call(
                "build_url", conn(engine="postgresql", user="postgres", database="app", trust=True)
            ),
            ["postgresql://postgres:pw@localhost/app"],
        )


class ParseHost(SqlCase):
    """parse_host splits the host answer into host and port."""

    def test_plain_host(self):
        """No port."""
        self.assertEqual(self.call("parse_host", "db"), ["db", None])

    def test_sqlcmd_comma_port(self):
        """sqlcmd's own host,port form."""
        self.assertEqual(self.call("parse_host", "db,1433"), ["db", "1433"])

    def test_colon_port(self):
        """The URL-style host:port form."""
        self.assertEqual(self.call("parse_host", "db:5432"), ["db", "5432"])

    def test_surrounding_spaces(self):
        """Whitespace around the answer is dropped."""
        self.assertEqual(self.call("parse_host", "  db  "), ["db", None])

    def test_blank_and_nil(self):
        """Nothing usable gives no host."""
        self.assertEqual(self.call("parse_host", "   "), [None, None])
        self.assertEqual(self.call("parse_host", None), [None, None])

    def test_ipv6_is_not_split(self):
        """A bare IPv6 address, or a host with several colons, stays whole."""
        for value in ("::1", "fe80::1", "db:1433:5"):
            with self.subTest(value=value):
                self.assertEqual(self.call("parse_host", value), [value, None])

    def test_bracketed_ipv6_with_port(self):
        """A bracketed IPv6 address may carry a port."""
        self.assertEqual(self.call("parse_host", "[::1]:1433"), ["[::1]", "1433"])

    def test_non_numeric_port_is_not_split(self):
        """A malformed port stays part of the host, so the connection fails visibly."""
        self.assertEqual(self.call("parse_host", "db,abc"), ["db,abc", None])


if __name__ == "__main__":
    unittest.main(verbosity=2)
