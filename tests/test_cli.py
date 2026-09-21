"""The command line: inputs, exit codes, JSON, and `python3 -m agenttrace` itself."""

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import unittest

from agenttrace.cli import run
from tests.support import REPO_ROOT, fixture

ADDRESS = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
CADDY = fixture("caddy-sample.log")
COMBINED = fixture("combined-sample.log")


def without_source_lines(text):
    return "\n".join(line for line in text.splitlines() if not line.startswith("source  "))


def invoke(arguments, stdin_text=None):
    """Run the CLI in process and return (exit code, stdout, stderr)."""

    out, err = io.StringIO(), io.StringIO()
    original_stdin = sys.stdin
    try:
        if stdin_text is not None:
            sys.stdin = io.StringIO(stdin_text)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run(arguments)
    finally:
        sys.stdin = original_stdin
    return code, out.getvalue(), err.getvalue()


class InputTests(unittest.TestCase):
    def test_one_file(self):
        code, out, _ = invoke([str(CADDY)])
        self.assertEqual(0, code)
        self.assertIn("Is /llms.txt being read?", out)
        self.assertIn("GPTBot", out)

    def test_every_input_shape_gives_the_same_answer(self):
        code, from_path, _ = invoke([str(CADDY)])
        _, from_glob, _ = invoke([str(fixture("caddy-sa*.log"))])
        _, from_many, _ = invoke([str(CADDY), str(CADDY)])
        _, from_stdin, _ = invoke(["--stdin"], stdin_text=CADDY.read_text(encoding="utf-8"))
        self.assertEqual(0, code)
        for other in (from_glob, from_many, from_stdin):
            self.assertEqual(without_source_lines(from_path), without_source_lines(other))

    def test_a_source_named_twice_is_counted_once(self):
        analysis = invoke([str(CADDY), str(fixture(".") / "caddy-sample.log")])[1]
        self.assertIn("33 requests", analysis)

    def test_dash_reads_standard_input(self):
        _, out, _ = invoke(["-"], stdin_text=COMBINED.read_text(encoding="utf-8"))
        self.assertIn("<stdin>", out)

    def test_format_override(self):
        code, out, _ = invoke(["--format", "combined", str(COMBINED)])
        self.assertEqual(0, code)
        self.assertIn("(combined)", out)

    def test_a_wrong_override_refuses_to_answer(self):
        code, out, _ = invoke(["--format", "caddy", str(COMBINED)])
        self.assertEqual(2, code)
        self.assertIn("CANNOT ANSWER", out)


class UsageErrorTests(unittest.TestCase):
    def test_no_input_named(self):
        with self.assertRaises(SystemExit) as caught:
            invoke([])
        self.assertEqual(1, caught.exception.code)

    def test_a_missing_file(self):
        code, out, err = invoke([str(fixture("does-not-exist.log"))])
        self.assertEqual(1, code)
        self.assertEqual("", out)
        self.assertIn("no such file", err)
        self.assertIn("no report produced", err)

    def test_a_directory_is_not_a_log(self):
        code, _, err = invoke([str(fixture("."))])
        self.assertEqual(1, code)
        self.assertIn("is a directory", err)

    def test_a_glob_that_matches_nothing(self):
        code, _, err = invoke([str(fixture("*.nope"))])
        self.assertEqual(1, code)
        self.assertIn("no files match", err)

    def test_an_unreadable_file(self):
        path = fixture("unreadable.log")
        path.write_text("x\n", encoding="utf-8")
        try:
            os.chmod(path, 0)
            if os.access(path, os.R_OK):  # running as a user who ignores the mode
                self.skipTest("file permissions are not enforced here")
            code, _, err = invoke([str(path)])
        finally:
            os.chmod(path, 0o644)
            path.unlink()
        self.assertEqual(1, code)
        self.assertIn("cannot read", err)


class ExitCodeTests(unittest.TestCase):
    def test_a_report_with_agents(self):
        self.assertEqual(0, invoke([str(CADDY)])[0])

    def test_a_parsed_log_with_no_agents_is_still_an_answer(self):
        code, out, _ = invoke([str(fixture("caddy-no-agents.log"))])
        self.assertEqual(0, code)
        self.assertIn("NO NAMED AI AGENT TRAFFIC IN THIS LOG", out)

    def test_an_empty_log_is_not_an_answer(self):
        code, out, _ = invoke([str(fixture("empty.log"))])
        self.assertEqual(2, code)
        self.assertIn("CANNOT ANSWER", out)

    def test_a_damaged_file_reports_what_it_could_read(self):
        code, out, _ = invoke([str(fixture("malformed.log"))])
        self.assertEqual(0, code)
        self.assertIn("6 lines, 2 read as requests, 3 not read as requests", out)


class JsonTests(unittest.TestCase):
    def test_json_is_json_and_matches_the_text_counts(self):
        code, out, _ = invoke(["--json", str(CADDY)])
        self.assertEqual(0, code)
        document = json.loads(out)
        self.assertEqual("reported", document["state"])
        self.assertEqual(33, document["totals"]["requests"])
        self.assertEqual(13, document["totals"]["named_agent_requests"])
        self.assertTrue(document["discovery"]["/llms.txt"]["read"])
        self.assertEqual(["GPTBot"], document["discovery"]["/llms.txt"]["agents"])
        self.assertEqual(8, len(document["named_agents_not_seen"]))

    def test_json_carries_the_boundary_and_no_address(self):
        for path in (CADDY, COMBINED, fixture("caddy-no-agents.log"), fixture("empty.log")):
            with self.subTest(fixture=path.name):
                _, out, _ = invoke(["--json", str(path)])
                document = json.loads(out)
                self.assertIn("self-declared", document["claim_boundary"])
                self.assertIsNone(ADDRESS.search(out))

    def test_json_for_an_empty_log_still_explains_itself(self):
        code, out, _ = invoke(["--json", str(fixture("empty.log"))])
        self.assertEqual(2, code)
        document = json.loads(out)
        self.assertEqual("no_readable_lines", document["state"])
        self.assertIn("not a count of zero agents", document["notice"])


class ModuleEntryPointTests(unittest.TestCase):
    """`python3 -m agenttrace` is the documented invocation, so it is tested as one."""

    def module(self, arguments, stdin_text=None):
        environment = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
        return subprocess.run(
            [sys.executable, "-m", "agenttrace"] + arguments,
            cwd=str(REPO_ROOT),
            env=environment,
            input=stdin_text,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_version(self):
        result = self.module(["--version"])
        self.assertEqual(0, result.returncode)
        self.assertIn("agenttrace", result.stdout)

    def test_a_report_over_a_fixture(self):
        result = self.module([str(CADDY)])
        self.assertEqual(0, result.returncode)
        self.assertIn("Is /llms.txt being read?", result.stdout)
        self.assertIsNone(ADDRESS.search(result.stdout))

    def test_json_over_standard_input(self):
        result = self.module(["--json", "--stdin"], stdin_text=COMBINED.read_text(encoding="utf-8"))
        self.assertEqual(0, result.returncode)
        self.assertEqual(13, json.loads(result.stdout)["totals"]["requests"])

    def test_the_empty_case_exit_code(self):
        result = self.module([str(fixture("empty.log"))])
        self.assertEqual(2, result.returncode)
        self.assertIn("CANNOT ANSWER", result.stdout)


if __name__ == "__main__":
    unittest.main()
