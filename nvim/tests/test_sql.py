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
            self.call("build_url", conn(database="app")),
            ["sqlserver://sa:pw@localhost/app?encrypt=mandatory"],
        )

    def test_reserved_characters_are_encoded(self):
        """User, password and database survive every URL delimiter and a space."""
        url = self.call(
            "build_url",
            conn(host="db", user="d@m:n", password="p@ss:w/rd%#? x", database="my db-1"),
        )
        self.assertEqual(
            url,
            ["sqlserver://d%40m%3An:p%40ss%3Aw%2Frd%25%23%3F%20x@db/my%20db-1?encrypt=mandatory"],
        )

    def test_password_cannot_redirect_the_host(self):
        """A password shaped like a host part stays inside the userinfo."""
        url = self.call("build_url", conn(host="db", password="x@evil.example.com/"))
        self.assertEqual(url, ["sqlserver://sa:x%40evil.example.com%2F@db?encrypt=mandatory"])

    def test_database_cannot_add_parameters(self):
        """A database name shaped like a query string cannot switch on trust."""
        url = self.call("build_url", conn(database="app?trustServerCertificate=true#"))
        self.assertEqual(
            url,
            [
                "sqlserver://sa:pw@localhost/app%3FtrustServerCertificate%3Dtrue%23"
                "?encrypt=mandatory"
            ],
        )

    def test_port(self):
        """A port follows the host."""
        self.assertEqual(
            self.call("build_url", conn(host="db", port="1433", database="app")),
            ["sqlserver://sa:pw@db:1433/app?encrypt=mandatory"],
        )

    def test_sqlserver_without_database(self):
        """SQL Server may connect to the login's default database."""
        self.assertEqual(
            self.call("build_url", conn()), ["sqlserver://sa:pw@localhost?encrypt=mandatory"]
        )

    def test_without_password(self):
        """A nil password leaves no colon behind."""
        self.assertEqual(
            self.call("build_url", conn(password=None, database="app")),
            ["sqlserver://sa@localhost/app?encrypt=mandatory"],
        )

    def test_trust(self):
        """trust adds the certificate parameter; vim-dadbod maps both to -N mandatory -C."""
        self.assertEqual(
            self.call("build_url", conn(database="app", trust=True)),
            ["sqlserver://sa:pw@localhost/app?encrypt=mandatory&trustServerCertificate=true"],
        )

    def test_sqlserver_requires_encryption(self):
        """Without trust, encryption is still required and the certificate is checked."""
        url = self.call("build_url", conn(database="app"))[0]
        self.assertTrue(url.endswith("?encrypt=mandatory"))
        self.assertNotIn("trustServerCertificate", url)

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


class Defaults(SqlCase):
    """defaults prefills the prompts from the engine's own environment variables."""

    def test_sqlserver_without_env(self):
        """localhost and sa, no password."""
        self.assertEqual(
            self.call("defaults", "sqlserver", {}), [{"host": "localhost", "user": "sa"}]
        )

    def test_sqlserver_full_env(self):
        """Host, user and the password from SQLCMD* variables."""
        env = {"SQLCMDSERVER": "db", "SQLCMDUSER": "app", "SQLCMDPASSWORD": "pw"}
        self.assertEqual(
            self.call("defaults", "sqlserver", env),
            [{"host": "db", "user": "app", "password": "pw"}],
        )

    def test_password_needs_host_and_user_from_env(self):
        """A password variable alone is not trusted for whatever host is typed."""
        env = {"SQLCMDSERVER": "db", "SQLCMDPASSWORD": "pw"}
        self.assertEqual(self.call("defaults", "sqlserver", env), [{"host": "db", "user": "sa"}])

    def test_password_not_released_without_host_from_env(self):
        """User and password variables without the host variable release no password."""
        env = {"SQLCMDUSER": "app", "SQLCMDPASSWORD": "pw"}
        self.assertEqual(
            self.call("defaults", "sqlserver", env), [{"host": "localhost", "user": "app"}]
        )

    def test_empty_variables_count_as_unset(self):
        """An exported but empty variable falls back like a missing one."""
        env = {"SQLCMDSERVER": "", "SQLCMDUSER": "", "SQLCMDPASSWORD": "pw"}
        self.assertEqual(
            self.call("defaults", "sqlserver", env), [{"host": "localhost", "user": "sa"}]
        )

    def test_postgresql_without_env(self):
        """localhost and postgres, no password."""
        self.assertEqual(
            self.call("defaults", "postgresql", {}), [{"host": "localhost", "user": "postgres"}]
        )

    def test_postgresql_full_env_with_port(self):
        """PGPORT joins the host prefill as host:port."""
        env = {"PGHOST": "pg", "PGPORT": "5433", "PGUSER": "app", "PGPASSWORD": "pw"}
        self.assertEqual(
            self.call("defaults", "postgresql", env),
            [{"host": "pg:5433", "user": "app", "password": "pw"}],
        )

    def test_engines_do_not_share_variables(self):
        """SQLCMD* variables never prefill a PostgreSQL connection."""
        env = {"SQLCMDSERVER": "db", "SQLCMDUSER": "app", "SQLCMDPASSWORD": "pw"}
        self.assertEqual(
            self.call("defaults", "postgresql", env), [{"host": "localhost", "user": "postgres"}]
        )


class PasswordFromEnv(SqlCase):
    """password_from_env releases the env password only for the prefilled login."""

    DEFAULTS = {"host": "db", "user": "app", "password": "pw"}

    def test_both_prefills_kept(self):
        """Accepting both prefills uses the env password."""
        self.assertEqual(self.call("password_from_env", self.DEFAULTS, "db", "app"), ["pw"])

    def test_host_changed(self):
        """Another host gets a prompt, never the env password."""
        self.assertEqual(self.call("password_from_env", self.DEFAULTS, "other", "app"), [None])

    def test_user_changed(self):
        """Another user gets a prompt, never the env password."""
        self.assertEqual(self.call("password_from_env", self.DEFAULTS, "db", "other"), [None])

    def test_no_env_password(self):
        """Without one there is nothing to release."""
        defaults = {"host": "localhost", "user": "sa"}
        self.assertEqual(self.call("password_from_env", defaults, "localhost", "sa"), [None])


class AutoTrust(SqlCase):
    """auto_trust skips certificate validation for the local machine only."""

    def test_local_names(self):
        """localhost and 127.0.0.1 are trusted."""
        self.assertEqual(self.call("auto_trust", "localhost"), [True])
        self.assertEqual(self.call("auto_trust", "127.0.0.1"), [True])

    def test_remote_names(self):
        """Anything else, including look-alikes, is not."""
        for host in ("db.example.com", "localhost.example.com", "mylocalhost", "127.0.0.2"):
            with self.subTest(host=host):
                self.assertEqual(self.call("auto_trust", host), [False])


class DatabaseListArgs(SqlCase):
    """database_list_args asks each client for one bare name per line."""

    def test_sqlserver(self):
        """No header, trimmed columns, no row count."""
        self.assertEqual(
            self.call("database_list_args", "sqlserver"),
            [["-h-1", "-W", "-Q", "SET NOCOUNT ON; SELECT name FROM sys.databases ORDER BY name"]],
        )

    def test_postgresql(self):
        """Unaligned tuples only, no psqlrc, templates left out."""
        self.assertEqual(
            self.call("database_list_args", "postgresql"),
            [
                [
                    "--no-psqlrc",
                    "-tAX",
                    "-c",
                    "SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY 1",
                ]
            ],
        )


class ParseDatabaseList(SqlCase):
    """parse_database_list turns client output into clean names."""

    def test_plain_lines(self):
        """One name per line."""
        self.assertEqual(
            self.call("parse_database_list", "master\ntempdb\n"), [["master", "tempdb"]]
        )

    def test_trailing_spaces_and_carriage_returns(self):
        """sqlcmd padding and CRLF line ends are stripped."""
        self.assertEqual(self.call("parse_database_list", "a   \r\nb\r\n"), [["a", "b"]])

    def test_blank_lines(self):
        """Blank lines are not databases."""
        self.assertEqual(self.call("parse_database_list", "\n\na\n\n"), [["a"]])

    def test_names_with_spaces_are_kept_whole(self):
        """Only the line ends are trimmed, not inner spaces."""
        self.assertEqual(self.call("parse_database_list", "probe db-1\n"), [["probe db-1"]])

    def test_empty_and_nil(self):
        """No output means no databases."""
        self.assertEqual(self.call("parse_database_list", ""), [[]])
        self.assertEqual(self.call("parse_database_list", None), [[]])


def padded(*cells, width=20):
    """A sqlcmd line: left-aligned cells, each padded to `width`, joined by one space."""
    return " ".join(cell.ljust(width) for cell in cells)


def dashes(columns, width=20):
    """The sqlcmd separator line under a header of `columns` cells."""
    return " ".join("-" * width for _ in range(columns))


class AlignSqlserver(SqlCase):
    """align_sqlserver shrinks sqlcmd's result columns to their content."""

    def test_columns_shrink_to_their_longest_cell(self):
        """Header included; the separator follows the new widths; the row count stays."""
        lines = [
            padded("name", "kind"),
            dashes(2),
            padded("alpha", "x"),
            padded("be", "yy"),
            "",
            "(2 rows affected)",
        ]
        self.assertEqual(
            self.call("align_sqlserver", lines),
            [["name  kind", "----- ----", "alpha x   ", "be    yy  ", "", "(2 rows affected)"]],
        )

    def test_right_aligned_numbers_and_inner_spaces(self):
        """Numbers stay right-aligned under a left-aligned header; inner spaces survive."""
        lines = [
            "n".ljust(11) + " " + "at".ljust(30),
            "-" * 11 + " " + "-" * 30,
            "42".rjust(11) + " " + "2015-12-03 15:14:30".ljust(30),
            "7".rjust(11) + " " + "NULL".ljust(30),
        ]
        self.assertEqual(
            self.call("align_sqlserver", lines),
            [
                [
                    "n  " + "at".ljust(19),
                    "-- " + "-" * 19,
                    "42 2015-12-03 15:14:30",
                    " 7 " + "NULL".ljust(19),
                ]
            ],
        )

    def test_header_wider_than_its_values(self):
        """A bit column keeps its header's width, values right-aligned under it."""
        lines = [padded("Confirmed", width=14), dashes(1, 14), "1".rjust(14), "0".rjust(14)]
        self.assertEqual(
            self.call("align_sqlserver", lines),
            [["Confirmed", "-" * 9, "        1", "        0"]],
        )

    def test_several_result_sets_and_a_message(self):
        """Each set shrinks on its own; a PRINT line between them is untouched."""
        lines = [
            padded("a"),
            dashes(1),
            padded("x"),
            "",
            "(1 row affected)",
            "hello",
            padded("bb"),
            dashes(1),
            padded("yy"),
            "",
            "(1 row affected)",
        ]
        self.assertEqual(
            self.call("align_sqlserver", lines),
            [
                [
                    "a",
                    "-",
                    "x",
                    "",
                    "(1 row affected)",
                    "hello",
                    "bb",
                    "--",
                    "yy",
                    "",
                    "(1 row affected)",
                ]
            ],
        )

    def test_empty_result_set(self):
        """No rows: the columns shrink to their headers."""
        lines = [padded("id", "name"), dashes(2), "", "(0 rows affected)"]
        self.assertEqual(
            self.call("align_sqlserver", lines), [["id name", "-- ----", "", "(0 rows affected)"]]
        )

    def test_multibyte_values_align_by_character(self):
        """sqlcmd pads by characters, so a multibyte value is not cut or misaligned."""
        lines = [padded("mail", width=10), dashes(1, 10), "ünï".ljust(10), "a".ljust(10)]
        self.assertEqual(self.call("align_sqlserver", lines), [["mail", "----", "ünï ", "a   "]])

    def test_line_broken_value_leaves_the_set_alone(self):
        """Rows narrower than the separator mean a value spans lines; nothing is guessed."""
        lines = ["multi".ljust(20), "-" * 20, "line1", "line2".ljust(14), "", "(1 row affected)"]
        self.assertEqual(self.call("align_sqlserver", lines), [lines])

    def test_psql_output_is_not_a_result_set(self):
        """psql's `-+-` separator is not sqlcmd's."""
        lines = [" id | label ", "----+-------", "  1 | one", "(1 row)"]
        self.assertEqual(self.call("align_sqlserver", lines), [lines])

    def test_dash_lines_that_are_not_separators(self):
        """Double spaces, other characters or a trailing space rule a line out."""
        lines = ["ab  cd", "--  --", "ab  cd", "", "abc", "-x-", "ab", "- "]
        self.assertEqual(self.call("align_sqlserver", lines), [lines])

    def test_empty(self):
        """No lines in, no lines out."""
        self.assertEqual(self.call("align_sqlserver", []), [[]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
