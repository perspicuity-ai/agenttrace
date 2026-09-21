"""The counts the report prints, and the two promises it must keep.

The expected numbers are hand counts of the fixtures: every assertion here can be
checked by reading the log lines under ``tests/fixtures/``.
"""

import json
import re
import unittest

from agenttrace import CLAIM_BOUNDARY, DISCOVERY_FILES
from agenttrace.classify import CATEGORY_ORDER
from agenttrace.classify import NAMED_AI_AGENTS
from agenttrace.report import (
    STATE_NO_AGENT_TRAFFIC,
    STATE_NO_READABLE_LINES,
    STATE_REPORTED,
    render_json,
    render_json_text,
    render_text,
)
from tests.support import FIXTURES, analyse_fixtures, fixture

ADDRESS = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def category_counts(analysis):
    """Category totals including the categories with no requests at all."""

    return {category: analysis.by_category[category] for category in CATEGORY_ORDER}


def unwrapped(text):
    """The rendered text with its display line wrapping removed."""

    return " ".join(text.split())


def agent_row(analysis, label):
    for record in analysis.named_agents:
        if record.label == label:
            return record
    raise AssertionError(f"{label} not found in {[r.label for r in analysis.named_agents]}")


class CaddyFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = analyse_fixtures(["caddy-sample.log"])

    def test_state_and_totals(self):
        self.assertEqual(STATE_REPORTED, self.analysis.state)
        self.assertEqual(33, self.analysis.requests)
        self.assertEqual(
            {
                "named_ai_agent": 13,
                "search_crawler": 8,
                "other_bot": 6,
                "browser": 4,
                "unknown": 2,
            },
            category_counts(self.analysis),
        )

    def test_source_accounting(self):
        source = self.analysis.sources[0]
        self.assertEqual("caddy", source.fmt)
        self.assertEqual(35, source.lines_read)
        self.assertEqual(33, source.requests_read)
        self.assertEqual(2, source.lines_not_requests)

    def test_named_agent_rows(self):
        rows = [(r.label, r.requests, r.unique_paths) for r in self.analysis.named_agents]
        self.assertEqual(
            [("GPTBot", 7, 7), ("ClaudeBot", 3, 3), ("PerplexityBot", 2, 2), ("ChatGPT-User", 1, 1)],
            rows,
        )

    def test_first_and_last_sighting_and_status_mix(self):
        gptbot = agent_row(self.analysis, "GPTBot")
        self.assertEqual("2026-09-14T09:00:00Z", gptbot.first.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.assertEqual("2026-09-14T09:00:30Z", gptbot.last.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.assertEqual({200: 6, 404: 1}, dict(gptbot.statuses))

    def test_the_query_string_does_not_split_a_path(self):
        # GPTBot asked for /pricing twice, once with a tracking parameter.
        self.assertIn("/pricing", agent_row(self.analysis, "GPTBot").paths)
        self.assertEqual(2, self.analysis.agent_paths["/pricing"])

    def test_discovery_files(self):
        llms = self.analysis.discovery["/llms.txt"]
        self.assertEqual({"GPTBot"}, llms["agents"])
        self.assertEqual({200: 1}, dict(llms["statuses"]))
        self.assertEqual({"ClaudeBot", "GPTBot"}, self.analysis.discovery["/robots.txt"]["agents"])
        self.assertEqual({"GPTBot"}, self.analysis.discovery["/sitemap.xml"]["agents"])

    def test_agent_share(self):
        self.assertEqual(13, self.analysis.named_agent_requests)
        self.assertAlmostEqual(13 / 33, self.analysis.agent_share, places=6)

    def test_top_paths_by_agents(self):
        top = self.analysis.agent_paths.most_common(4)
        self.assertEqual(2, top[0][1])
        self.assertEqual(
            {"/robots.txt", "/recipes/black-bean-tacos", "/recipes/miso-soup", "/pricing"},
            {path for path, count in top if count == 2},
        )

    def test_paths_agents_asked_for_and_did_not_get(self):
        missing = {item.path: item for item in self.analysis.missing.values()}
        self.assertEqual({"/about", "/recipes/vegan-carbonara"}, set(missing))
        self.assertEqual({"ClaudeBot"}, missing["/about"].agents)
        self.assertEqual({404: 1}, dict(missing["/about"].statuses))

    def test_a_search_crawlers_miss_is_not_an_agents_miss(self):
        # Googlebot asked for /recipes/vegan-carbonara and got a 410; Googlebot is not
        # one of the twelve named agents, so that miss must not be attributed to them.
        missing = {item.path: item for item in self.analysis.missing.values()}
        self.assertEqual({"GPTBot"}, missing["/recipes/vegan-carbonara"].agents)

    def test_named_agents_not_seen_are_named(self):
        seen = {record.label for record in self.analysis.named_agents}
        not_seen = [name for name in NAMED_AI_AGENTS if name not in seen]
        self.assertEqual(8, len(not_seen))
        text = render_text(self.analysis)
        for name in not_seen:
            self.assertIn(name, text)


class CombinedFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = analyse_fixtures(["combined-sample.log"])

    def test_state_and_totals(self):
        self.assertEqual(STATE_REPORTED, self.analysis.state)
        self.assertEqual(13, self.analysis.requests)
        self.assertEqual(
            {
                "named_ai_agent": 9,
                "search_crawler": 1,
                "other_bot": 2,
                "browser": 1,
                "unknown": 0,
            },
            category_counts(self.analysis),
        )

    def test_llms_is_not_requested_in_this_log(self):
        llms = self.analysis.discovery["/llms.txt"]
        self.assertEqual(set(), llms["agents"])
        self.assertIn("NOT REQUESTED", render_text(self.analysis))

    def test_time_zone_offsets_are_normalised(self):
        self.assertEqual("2026-09-16T08:00:00Z", self.analysis.first.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.assertEqual("2026-09-16T10:03:00Z", self.analysis.last.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def test_missing_paths_carry_their_status(self):
        missing = {item.path: item for item in self.analysis.missing.values()}
        self.assertEqual({"/missing-page", "/recipes/miso-soup", "/recipes/vegan-carbonara"}, set(missing))
        self.assertEqual({410: 1}, dict(missing["/recipes/miso-soup"].statuses))


class TaxonomyFixtureTests(unittest.TestCase):
    def test_all_twelve_named_agents_are_counted_and_no_more(self):
        analysis = analyse_fixtures(["caddy-all-agents.log"])
        self.assertEqual(14, analysis.requests)
        self.assertEqual(
            {name: 1 for name in NAMED_AI_AGENTS},
            {record.label: record.requests for record in analysis.named_agents},
        )
        self.assertEqual(
            {"Applebot": 1, "Googlebot": 1},
            {record.label: record.requests for record in analysis.search_crawlers},
        )


class EmptyStateTests(unittest.TestCase):
    def test_a_parsed_log_with_no_agent_claims_says_so(self):
        analysis = analyse_fixtures(["caddy-no-agents.log"])
        self.assertEqual(STATE_NO_AGENT_TRAFFIC, analysis.state)
        text = render_text(analysis)
        self.assertIn("NO NAMED AI AGENT TRAFFIC IN THIS LOG", text)
        self.assertIn("not logging at all", text)
        self.assertIn("findmynextbite.food", text)
        self.assertNotIn("Named AI agents —", text)
        document = render_json(analysis)
        self.assertEqual(STATE_NO_AGENT_TRAFFIC, document["state"])
        self.assertIn("may not be logging", document["notice"])

    def test_the_common_format_yields_unknown_clients_not_agents(self):
        analysis = analyse_fixtures(["combined-common.log"])
        self.assertEqual(STATE_NO_AGENT_TRAFFIC, analysis.state)
        self.assertEqual(4, analysis.by_category["unknown"])

    def test_nothing_readable_is_not_a_zero_count(self):
        analysis = analyse_fixtures(["empty.log"])
        self.assertEqual(STATE_NO_READABLE_LINES, analysis.state)
        text = render_text(analysis)
        self.assertIn("CANNOT ANSWER", text)
        self.assertNotIn(CLAIM_BOUNDARY, text)
        document = render_json(analysis)
        self.assertEqual(STATE_NO_READABLE_LINES, document["state"])
        self.assertIn("not a count of zero agents", document["notice"])

    def test_a_damaged_log_is_counted_and_what_parses_is_used(self):
        analysis = analyse_fixtures(["malformed.log"])
        self.assertEqual(STATE_REPORTED, analysis.state)
        source = analysis.sources[0]
        self.assertEqual(6, source.lines_read)
        self.assertEqual(2, source.requests_read)
        self.assertEqual(3, source.lines_not_requests)
        self.assertEqual(1, analysis.named_agent_requests)
        self.assertEqual({200: 1}, dict(agent_row(analysis, "GPTBot").statuses))


class ClaimBoundaryTests(unittest.TestCase):
    def test_the_boundary_is_in_every_report_that_has_counts(self):
        for name in ("caddy-sample.log", "combined-sample.log", "caddy-all-agents.log",
                     "caddy-no-agents.log", "malformed.log"):
            with self.subTest(fixture=name):
                analysis = analyse_fixtures([name])
                self.assertIn(CLAIM_BOUNDARY, unwrapped(render_text(analysis)))
                self.assertEqual(CLAIM_BOUNDARY, render_json(analysis)["claim_boundary"])

    def test_the_boundary_says_claims_not_verified_agents(self):
        self.assertIn("self-declared", CLAIM_BOUNDARY)
        self.assertIn("count of claims", CLAIM_BOUNDARY)


class NoAddressTests(unittest.TestCase):
    """The tool must not print addresses. The fixtures contain some, so this bites."""

    FIXTURES_WITH_ADDRESSES = (
        "caddy-sample.log",
        "combined-sample.log",
        "combined-common.log",
        "caddy-all-agents.log",
        "caddy-no-agents.log",
        "malformed.log",
    )

    def test_the_fixtures_really_do_contain_addresses(self):
        for name in self.FIXTURES_WITH_ADDRESSES:
            with self.subTest(fixture=name):
                self.assertIsNotNone(ADDRESS.search(fixture(name).read_text(encoding="utf-8")))

    def test_no_address_appears_in_any_rendering(self):
        for name in self.FIXTURES_WITH_ADDRESSES:
            with self.subTest(fixture=name):
                analysis = analyse_fixtures([name])
                self.assertIsNone(ADDRESS.search(render_text(analysis)))
                self.assertIsNone(ADDRESS.search(render_json_text(analysis)))

    def test_no_fixture_file_was_missed(self):
        on_disk = {path.name for path in FIXTURES.glob("*.log")}
        synthetic = set(self.FIXTURES_WITH_ADDRESSES) | {"empty.log"}
        # The real-log fixture has no addresses by design: its redaction is checked in
        # tests/test_real_fixture.py.
        real = {"real-findmynextbite-2026-09-21-1828Z.log"}
        self.assertEqual(on_disk, synthetic | real)


class DiscoveryOrderTests(unittest.TestCase):
    def test_llms_txt_is_asked_about_first(self):
        self.assertEqual("/llms.txt", DISCOVERY_FILES[0])

    def test_the_json_document_carries_the_same_question(self):
        analysis = analyse_fixtures(["caddy-sample.log"])
        document = json.loads(render_json_text(analysis))
        self.assertTrue(document["discovery"]["/llms.txt"]["read"])
        self.assertEqual(["GPTBot"], document["discovery"]["/llms.txt"]["agents"])


if __name__ == "__main__":
    unittest.main()
