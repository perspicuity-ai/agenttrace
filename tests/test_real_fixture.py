"""The one fixture taken from a real server, and the redaction rules it must keep.

The rules are registered in `docs/records/2026-09-21-real-log-fixture-redaction.md`; the
provenance of this particular extract is in
`tests/fixtures/real-findmynextbite-2026-09-21-1828Z.md`. These tests exist so the
redaction survives later edits to the fixture: an address, a query string or a cookie
reintroduced there fails the build.
"""

import json
import re
import unittest

from agenttrace.classify import CATEGORY_NAMED_AGENT, classify
from agenttrace.parse import FORMAT_CADDY, parse_line
from tests.support import fixture

NAME = "real-findmynextbite-2026-09-21-1828Z.log"
CHECK = "real-findmynextbite-2026-09-21-1828Z.md"

ADDRESS = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
FORBIDDEN_KEYS = {
    "remote_ip", "client_ip", "remote_port",
    "Cookie", "Set-Cookie", "Authorization", "Proxy-Authorization",
    "resp_headers",  # dropped at extraction: the tool never reads it, and it can carry Set-Cookie
}
EXPECTED_ENTRIES = 21


def lines():
    return fixture(NAME).read_text(encoding="utf-8").splitlines()


def records():
    return [json.loads(line) for line in lines() if line.strip()]


def keys_of(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from keys_of(item)
    elif isinstance(value, list):
        for item in value:
            yield from keys_of(item)


class RedactionTests(unittest.TestCase):
    def test_no_address_like_token_survives(self):
        self.assertIsNone(ADDRESS.search(fixture(NAME).read_text(encoding="utf-8")))

    def test_no_request_target_carries_a_query_string(self):
        targets = [record["request"]["uri"] for record in records()]
        self.assertEqual([], [target for target in targets if "?" in target])

    def test_no_address_or_cookie_material_survives(self):
        present = set()
        for record in records():
            present.update(keys_of(record))
        self.assertEqual(set(), present & FORBIDDEN_KEYS)

    def test_the_provenance_note_records_the_window(self):
        note = fixture(CHECK).read_text(encoding="utf-8")
        self.assertIn("2026-09-21T18:28:02Z", note)
        self.assertIn("2026-09-21T18:34:50Z", note)
        self.assertIn("408 seconds", note)


class RealShapeTests(unittest.TestCase):
    """What a real server wrote, read by the real parser."""

    def test_every_line_is_read_as_a_caddy_request(self):
        parsed = [parse_line(line, FORMAT_CADDY)[0] for line in lines()]
        self.assertEqual(EXPECTED_ENTRIES, len(parsed))
        self.assertTrue(all(entry is not None for entry in parsed))

    def test_the_window_bounds_the_requests(self):
        entries = [parse_line(line, FORMAT_CADDY)[0] for line in lines()]
        first = min(entry.timestamp for entry in entries).strftime("%Y-%m-%dT%H:%M:%SZ")
        last = max(entry.timestamp for entry in entries).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual("2026-09-21T18:28:02Z", first)
        self.assertEqual("2026-09-21T18:34:50Z", last)

    def test_the_window_holds_one_claimed_named_agent_and_that_is_the_point(self):
        claims = [classify(parse_line(line, FORMAT_CADDY)[0].user_agent) for line in lines()]
        named = [claim.label for claim in claims if claim.category == CATEGORY_NAMED_AGENT]
        self.assertEqual(["GPTBot"], named)

    def test_the_busiest_client_is_not_a_named_agent(self):
        # 17 of the 21 entries are the site's own monitor. Whatever bucket it lands in,
        # it must never be counted as an AI agent claim.
        counts = {}
        for line in lines():
            agent = parse_line(line, FORMAT_CADDY)[0].user_agent
            counts[agent] = counts.get(agent, 0) + 1
        busiest = max(counts, key=counts.get)
        self.assertIn("FindMyNextBiteMonitor", busiest)
        self.assertEqual(17, counts[busiest])
        self.assertNotEqual(CATEGORY_NAMED_AGENT, classify(busiest).category)


if __name__ == "__main__":
    unittest.main()
