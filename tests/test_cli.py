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
REAL = fixture("real-findmynextbite-2026-09-21-1828Z.log")


def unwrapped(text):
    """The report with its display line wrapping removed."""

    return " ".join(text.split())


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
        # A source that cannot be opened is reported as a failed source, and the run
        # still explains itself rather than printing nothing (W1 F8).
        code, out, err = invoke([str(fixture("does-not-exist.log"))])
        self.assertEqual(1, code)
        self.assertIn("cannot read", err)
        self.assertIn("CANNOT ANSWER", out)
        self.assertIn("cannot read this source", unwrapped(out))

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
            code, out, err = invoke([str(path)])
        finally:
            os.chmod(path, 0o644)
            path.unlink()
        self.assertEqual(1, code)
        self.assertIn("cannot read", err)
        # W1 F8: the failure is reported in the output too, not swallowed.
        self.assertIn("cannot read this source", unwrapped(out))
        self.assertIn("CANNOT ANSWER", out)

    def test_one_unreadable_source_does_not_discard_the_others(self):
        code, out, err = invoke([str(CADDY), str(fixture("does-not-exist.log"))])
        self.assertEqual(1, code)
        self.assertIn("cannot read", err)
        self.assertIn("Site-wide", out)
        self.assertIn("33", out)
        self.assertIn("cannot read this source", unwrapped(out))


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


class DeclarationTests(unittest.TestCase):
    """--self: the operator's own clients are set aside, not presented as agents."""

    def test_without_a_declaration_the_whole_log_is_counted(self):
        code, out, _ = invoke([str(REAL)])
        self.assertEqual(0, code)
        self.assertIn("17 of 21 requests (81.0%) came from one client", out)

    def test_a_declaration_sets_the_client_aside(self):
        code, out, _ = invoke(["--self", "FindMyNextBiteMonitor", str(REAL)])
        self.assertEqual(0, code)
        self.assertIn("Set aside — declared your own (--self)", out)
        self.assertIn("17", out)
        self.assertNotIn("came from one client", out)

    def test_an_unmatched_declaration_is_stated(self):
        code, out, _ = invoke(["--self", "NoSuchClient", str(REAL)])
        self.assertEqual(0, code)
        self.assertIn("--self matched nothing for: NoSuchClient", out)

    def test_the_json_carries_the_declaration(self):
        _, out, _ = invoke(["--self", "FindMyNextBiteMonitor", "--json", str(REAL)])
        document = json.loads(out)
        self.assertEqual(17, document["declared_self"]["matched"][0]["requests"])
        self.assertEqual([], document["declared_self"]["unmatched"])
        self.assertIsNone(document["dominant_client"])


class DriftTests(unittest.TestCase):
    def test_a_drifted_format_refuses_with_a_reason(self):
        code, out, _ = invoke([str(fixture("caddy-drifted.log"))])
        self.assertEqual(2, code)
        self.assertIn("CANNOT ANSWER", out)
        self.assertIn("request.uri", out)
        self.assertIn("status_code", out)

    def test_the_json_carries_the_diagnostic(self):
        code, out, _ = invoke(["--json", str(fixture("caddy-drifted.log"))])
        self.assertEqual(2, code)
        document = json.loads(out)
        self.assertEqual("no_readable_lines", document["state"])
        self.assertTrue(document["sources"][0]["diagnostics"])

    def test_a_partly_readable_source_still_reports_and_warns(self):
        code, out, _ = invoke([str(fixture("malformed.log"))])
        self.assertEqual(0, code)
        self.assertIn("WARNING", out)
        self.assertIn("Site-wide", out)


class JsonTests(unittest.TestCase):
    def test_json_is_json_and_matches_the_text_counts(self):
        code, out, _ = invoke(["--json", str(CADDY)])
        self.assertEqual(0, code)
        document = json.loads(out)
        self.assertEqual("reported", document["state"])
        self.assertEqual(33, document["totals"]["requests"])
        self.assertEqual(13, document["totals"]["named_agent_requests"])
        self.assertTrue(document["discovery"]["/llms.txt"]["served"])
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
