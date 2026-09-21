"""Parsing both formats, and the fields the report depends on."""

import datetime as dt
import json
import unittest

from agenttrace.parse import (
    FORMAT_CADDY,
    FORMAT_COMBINED,
    combined_timestamp,
    explain,
    parse_caddy_line,
    parse_combined_line,
    parse_line,
    path_of,
    sniff,
    sniff_format,
)
from tests.support import fixture

CADDY_LINE = json.dumps(
    {
        "level": "info",
        "ts": 1789376400.0,
        "logger": "http.log.access.log0",
        "msg": "handled request",
        "request": {
            "remote_ip": "203.0.113.11",
            "client_ip": "203.0.113.11",
            "method": "get",
            "host": "findmynextbite.food",
            "uri": "/recipes/miso-soup?utm_source=news#top",
            "headers": {"User-Agent": ["GPTBot/1.2"], "Accept": ["*/*"]},
        },
        "status": 200,
    },
    separators=(",", ":"),
)

COMBINED_LINE = (
    '203.0.113.40 - - [16/Sep/2026:08:00:00 +0000] "GET /recipes/miso-soup?a=1 HTTP/1.1" '
    '200 8123 "-" "Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)"'
)


def read_lines(name):
    with open(fixture(name), "r", encoding="utf-8", errors="replace") as stream:
        return stream.read().splitlines()


class PathTests(unittest.TestCase):
    def test_query_and_fragment_are_removed(self):
        self.assertEqual("/pricing", path_of("/pricing?utm_source=news#buy"))
        self.assertEqual("/pricing", path_of("/pricing"))
        self.assertEqual("/pricing", path_of("/pricing?"))

    def test_absolute_request_target(self):
        self.assertEqual("/a/b", path_of("https://example.invalid/a/b?x=1"))

    def test_empty_and_unusual_targets(self):
        self.assertEqual("/", path_of(""))
        self.assertEqual("/", path_of("?x=1"))
        self.assertEqual("*", path_of("*"))


class TimestampTests(unittest.TestCase):
    def test_combined_timestamp_is_converted_to_utc(self):
        moment = combined_timestamp("16/Sep/2026:08:00:00 +0000")
        self.assertEqual(dt.datetime(2026, 9, 16, 8, 0, tzinfo=dt.timezone.utc), moment)

    def test_a_non_utc_offset_is_applied(self):
        moment = combined_timestamp("16/Sep/2026:12:00:00 +0200")
        self.assertEqual(dt.datetime(2026, 9, 16, 10, 0, tzinfo=dt.timezone.utc), moment)

    def test_month_names_do_not_depend_on_the_locale(self):
        for text, month in (("01/Jan/2026:00:00:00 +0000", 1), ("31/Dec/2026:23:59:59 +0000", 12)):
            with self.subTest(text=text):
                self.assertEqual(month, combined_timestamp(text).month)

    def test_unreadable_timestamps(self):
        for text in ("", "not a time", "32/Foo/2026:00:00:00 +0000", "16/Sep/2026:99:00:00 +0000"):
            with self.subTest(text=text):
                self.assertIsNone(combined_timestamp(text))


class CaddyTests(unittest.TestCase):
    def test_a_whole_line(self):
        entry = parse_caddy_line(CADDY_LINE)
        self.assertIsNotNone(entry)
        self.assertEqual(dt.datetime(2026, 9, 14, 9, 0, tzinfo=dt.timezone.utc), entry.timestamp)
        self.assertEqual("GET", entry.method)
        self.assertEqual("/recipes/miso-soup", entry.path)
        self.assertEqual(200, entry.status)
        self.assertEqual("GPTBot/1.2", entry.user_agent)

    def test_a_non_access_runtime_line_is_not_a_request(self):
        line = json.dumps({"level": "info", "ts": 1789376400.0, "msg": "certificate obtained"})
        self.assertIsNone(parse_caddy_line(line))

    def test_a_line_without_a_status_is_not_a_request(self):
        record = json.loads(CADDY_LINE)
        del record["status"]
        self.assertIsNone(parse_caddy_line(json.dumps(record)))

    def test_a_header_logged_as_a_string_still_reads(self):
        record = json.loads(CADDY_LINE)
        record["request"]["headers"] = {"user-agent": "ClaudeBot/1.0"}
        self.assertEqual("ClaudeBot/1.0", parse_caddy_line(json.dumps(record)).user_agent)

    def test_missing_user_agent_is_empty_not_an_error(self):
        record = json.loads(CADDY_LINE)
        record["request"]["headers"] = {}
        self.assertEqual("", parse_caddy_line(json.dumps(record)).user_agent)

    def test_malformed_json(self):
        self.assertIsNone(parse_caddy_line('{"level":"info","ts":'))
        self.assertIsNone(parse_caddy_line("not json at all"))


class CombinedTests(unittest.TestCase):
    def test_a_whole_line(self):
        entry = parse_combined_line(COMBINED_LINE)
        self.assertIsNotNone(entry)
        self.assertEqual(dt.datetime(2026, 9, 16, 8, 0, tzinfo=dt.timezone.utc), entry.timestamp)
        self.assertEqual("GET", entry.method)
        self.assertEqual("/recipes/miso-soup", entry.path)
        self.assertEqual(200, entry.status)
        self.assertIn("GPTBot", entry.user_agent)

    def test_the_common_format_has_no_user_agent(self):
        line = '203.0.113.60 - - [17/Sep/2026:12:00:00 +0000] "GET / HTTP/1.1" 200 5123'
        entry = parse_combined_line(line)
        self.assertIsNotNone(entry)
        self.assertEqual("/", entry.path)
        self.assertEqual("", entry.user_agent)

    def test_hostname_in_place_of_an_address_still_parses(self):
        line = COMBINED_LINE.replace("203.0.113.40", "logs.example.invalid")
        self.assertIsNotNone(parse_combined_line(line))

    def test_a_dash_request_is_not_a_request(self):
        line = '203.0.113.60 - - [17/Sep/2026:12:00:00 +0000] "-" 408 0'
        self.assertIsNone(parse_combined_line(line))

    def test_lines_that_are_not_combined(self):
        for line in ("", "this line is not an access log entry at all", '{"level":"info"}'):
            with self.subTest(line=line):
                self.assertIsNone(parse_combined_line(line))


class DetectionTests(unittest.TestCase):
    def test_the_caddy_fixture_is_detected(self):
        self.assertEqual(FORMAT_CADDY, sniff_format(read_lines("caddy-sample.log")))

    def test_the_combined_fixture_is_detected(self):
        self.assertEqual(FORMAT_COMBINED, sniff_format(read_lines("combined-sample.log")))
        self.assertEqual(FORMAT_COMBINED, sniff_format(read_lines("combined-common.log")))

    def test_an_undecidable_file(self):
        self.assertIsNone(sniff_format(["nothing here", ""]))

    def test_an_override_pins_the_parser(self):
        entry, used = parse_line(COMBINED_LINE, FORMAT_CADDY)
        self.assertIsNone(entry)
        self.assertEqual(FORMAT_CADDY, used)
        entry, used = parse_line(COMBINED_LINE, FORMAT_COMBINED)
        self.assertIsNotNone(entry)
        self.assertEqual(FORMAT_COMBINED, used)

    def test_auto_mode_tries_both(self):
        for line in (CADDY_LINE, COMBINED_LINE):
            with self.subTest(line=line[:20]):
                entry, used = parse_line(line)
                self.assertIsNotNone(entry)
                self.assertIn(used, (FORMAT_CADDY, FORMAT_COMBINED))


class FixtureLineTests(unittest.TestCase):
    def test_every_caddy_fixture_line_is_accounted_for(self):
        lines = read_lines("caddy-sample.log")
        entries = [parse_line(line, FORMAT_CADDY)[0] for line in lines]
        self.assertEqual(35, len(lines))
        self.assertEqual(33, sum(entry is not None for entry in entries))
        self.assertEqual(2, sum(entry is None for entry in entries))

    def test_every_combined_fixture_line_is_accounted_for(self):
        lines = read_lines("combined-sample.log")
        entries = [parse_line(line, FORMAT_COMBINED)[0] for line in lines]
        self.assertEqual(13, len(lines))
        self.assertEqual(13, sum(entry is not None for entry in entries))

    def test_the_common_fixture_reads_with_no_user_agent(self):
        lines = read_lines("combined-common.log")
        entries = [parse_line(line, FORMAT_COMBINED)[0] for line in lines]
        self.assertEqual(4, len(entries))
        self.assertTrue(all(entry.user_agent == "" for entry in entries))


class CombinedVariantTests(unittest.TestCase):
    """Shapes real servers write that are not the textbook combined line."""

    def test_one_trailing_field_that_is_a_referer_is_not_a_user_agent(self):
        line = ('1.1.1.1 - - [19/Sep/2026:06:00:00 +0000] "GET /robots.txt HTTP/1.1" 200 219 '
                '"https://duckduckgo.com/"')
        entry = parse_combined_line(line)
        self.assertIsNotNone(entry)
        self.assertEqual("", entry.user_agent)

    def test_one_trailing_field_that_is_a_user_agent_is_read(self):
        line = ('1.1.1.1 - - [19/Sep/2026:06:00:00 +0000] "GET /llms.txt HTTP/1.1" 200 219 '
                '"Mozilla/5.0 (compatible; GPTBot/1.1)"')
        entry = parse_combined_line(line)
        self.assertIsNotNone(entry)
        self.assertEqual("Mozilla/5.0 (compatible; GPTBot/1.1)", entry.user_agent)

    def test_a_vhost_prefixed_line_parses(self):
        line = ('findmynextbite.food:443 1.1.1.1 - - [19/Sep/2026:06:00:00 +0000] '
                '"GET / HTTP/1.1" 200 5123 "-" "curl/8.4.0"')
        entry = parse_combined_line(line)
        self.assertIsNotNone(entry)
        self.assertEqual("/", entry.path)
        self.assertEqual("curl/8.4.0", entry.user_agent)

    def test_a_target_with_no_path_is_not_a_request(self):
        # Inventing "/" would report a page the server never logged.
        self.assertIsNone(parse_combined_line('1.1.1.1 - - [19/Sep/2026:06:00:00 +0000] "/a" 200 1'))


class StatusRangeTests(unittest.TestCase):
    def test_a_status_outside_the_protocol_is_not_a_request(self):
        for status in (999, 1000, -1, 42, "999"):
            with self.subTest(status=status):
                line = ('1.1.1.1 - - [19/Sep/2026:06:00:00 +0000] "GET / HTTP/1.1" '
                        f'{status} 1 "-" "curl/8.4.0"')
                self.assertIsNone(parse_combined_line(line))
                record = {"ts": 1790015282.4, "status": status,
                          "request": {"uri": "/", "method": "GET", "headers": {}}}
                self.assertIsNone(parse_caddy_line(json.dumps(record)))

    def test_zero_is_kept_as_no_response_rather_than_dropped(self):
        record = {"ts": 1790015282.4, "status": 0,
                  "request": {"uri": "/", "method": "GET", "headers": {"User-Agent": ["curl/8.4.0"]}}}
        entry = parse_caddy_line(json.dumps(record))
        self.assertIsNotNone(entry)
        self.assertEqual(0, entry.status)


class DriftExplanationTests(unittest.TestCase):
    """A changed schema must produce a specific reason, not a shrug."""

    def test_a_renamed_caddy_field_is_explained(self):
        lines = read_lines("caddy-drifted.log")
        evidence = sniff(lines)
        self.assertIsNone(evidence.fmt)
        self.assertEqual(2, evidence.json_objects)
        self.assertIn("path", evidence.request_keys)
        sentence = explain(evidence)
        self.assertIn("JSON objects", sentence)
        self.assertIn("request.uri", sentence)
        self.assertIn("status", sentence)

    def test_prose_is_explained_by_showing_it(self):
        evidence = sniff(["this line is not an access log entry at all"])
        self.assertIsNone(evidence.fmt)
        self.assertIn("this line is not an access log entry at all", explain(evidence))

    def test_an_empty_source_says_so(self):
        evidence = sniff(["", "   "])
        self.assertIsNone(evidence.fmt)
        self.assertIn("no non-blank line", explain(evidence))


if __name__ == "__main__":
    unittest.main()
