"""The counts the report prints, and the two promises it must keep.

The expected numbers are hand counts of the fixtures: every assertion here can be
checked by reading the log lines under ``tests/fixtures/``.
"""

import json
import re
import unittest
from collections import Counter

from agenttrace import CLAIM_BOUNDARY, DISCOVERY_FILES
from agenttrace.classify import CATEGORY_ORDER, CATEGORY_UNKNOWN
from agenttrace.classify import NAMED_AI_AGENTS
from agenttrace.report import (
    STATE_NO_AGENT_TRAFFIC,
    STATE_NO_READABLE_LINES,
    STATE_REPORTED,
    discovery_verdict,
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
                "declared_self": 0,
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
                "declared_self": 0,
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
        # The boundary is carried in every state, including the one with no counts (W1 F3).
        self.assertIn(CLAIM_BOUNDARY, unwrapped(text))
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
        "caddy-drifted.log",
        "caddy-llms-statuses.log",
        "combined-referer.log",
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
        self.assertTrue(document["discovery"]["/llms.txt"]["served"])
        self.assertEqual(["GPTBot"], document["discovery"]["/llms.txt"]["agents"])


class DiscoveryVerdictTests(unittest.TestCase):
    """W1 F1: below 400 is not "read"."""

    def test_a_2xx_is_read(self):
        for status in (200, 204, 206):
            with self.subTest(status=status):
                verdict, served = discovery_verdict(Counter({status: 1}))
                self.assertEqual("READ", verdict)
                self.assertTrue(served)

    def test_a_redirect_is_not_read(self):
        verdict, served = discovery_verdict(Counter({302: 1}))
        self.assertIn("REDIRECTED", verdict)
        self.assertIn("302", verdict)
        self.assertFalse(served)

    def test_not_modified_is_read_with_the_reason(self):
        verdict, served = discovery_verdict(Counter({304: 1}))
        self.assertIn("NOT MODIFIED", verdict)
        self.assertTrue(served)

    def test_a_refusal_and_a_missing_file_are_not_read(self):
        for status, expected in ((404, "NOT SERVED"), (410, "NOT SERVED"), (403, "REFUSED"),
                                 (401, "REFUSED"), (503, "SERVER ERROR")):
            with self.subTest(status=status):
                verdict, served = discovery_verdict(Counter({status: 1}))
                self.assertIn(expected, verdict)
                self.assertIn(str(status), verdict)
                self.assertFalse(served)

    def test_no_response_recorded_is_not_read(self):
        verdict, served = discovery_verdict(Counter({0: 1}))
        self.assertIn("NO RESPONSE", verdict)
        self.assertFalse(served)

    def test_a_success_anywhere_wins_over_a_redirect(self):
        verdict, served = discovery_verdict(Counter({302: 1, 200: 1}))
        self.assertEqual("READ", verdict)
        self.assertTrue(served)


class DiscoveryAgreementTests(unittest.TestCase):
    """W1 F2: the text and the JSON must not disagree about the same figure."""

    def test_the_json_names_each_discovery_figure(self):
        analysis = analyse_fixtures(["caddy-sample.log"])
        document = json.loads(render_json_text(analysis))
        robots = document["discovery"]["/robots.txt"]
        self.assertEqual(4, robots["requests_from_all_clients"])
        self.assertEqual(2, robots["named_agent_requests"])
        self.assertEqual(["ClaudeBot", "GPTBot"], robots["agents"])
        self.assertEqual({"200": 2}, robots["named_agent_statuses"])
        self.assertEqual({"200": 4}, robots["statuses_from_all_clients"])
        self.assertEqual("READ", robots["verdict"])
        self.assertTrue(robots["served"])

    def test_the_text_and_the_json_agree_on_the_named_agent_count(self):
        analysis = analyse_fixtures(["caddy-sample.log"])
        text = render_text(analysis)
        document = json.loads(render_json_text(analysis))
        for path in DISCOVERY_FILES:
            with self.subTest(path=path):
                listed = document["discovery"][path]["named_agent_requests"]
                if listed:
                    self.assertIn(f"{listed} request", text)

    def test_a_redirected_llms_txt_does_not_read_as_read(self):
        analysis = analyse_fixtures(["caddy-llms-statuses.log"])
        text = render_text(analysis)
        document = json.loads(render_json_text(analysis))
        self.assertIn("REDIRECTED (302)", text)
        self.assertNotIn("VERDICT: READ", text)
        self.assertFalse(document["discovery"]["/llms.txt"]["served"])
        self.assertIn("NOT MODIFIED", text)  # /robots.txt, 304
        self.assertIn("REFUSED (403)", text)  # /sitemap.xml, forbidden


class SelfDeclarationTests(unittest.TestCase):
    """The site's own monitor must not be presented as somebody's agent."""

    REAL = "real-findmynextbite-2026-09-21-1828Z.log"

    def test_without_a_declaration_the_dominant_client_is_called_out(self):
        analysis = analyse_fixtures([self.REAL])
        text = render_text(analysis)
        self.assertIn("17 of 21 requests (81.0%) came from one client", text)
        self.assertIn("FindMyNextBiteMonitor/1.0", text)
        self.assertIn("--self FindMyNextBiteMonitor", text)
        self.assertIn("cannot tell whether that is your own monitoring", text)

    def test_a_declaration_sets_the_client_aside_and_silences_the_warning(self):
        analysis = analyse_fixtures([self.REAL], declarations=("FindMyNextBiteMonitor",))
        text = unwrapped(render_text(analysis))
        self.assertIn("Set aside — declared your own (--self)", text)
        self.assertIn("17 FindMyNextBiteMonitor (15 path(s))", text)
        self.assertNotIn("cannot tell whether that is your own monitoring", text)
        self.assertEqual(17, analysis.by_category["declared_self"])
        self.assertEqual(0, analysis.by_category[CATEGORY_UNKNOWN])
        document = render_json(analysis)
        self.assertEqual(["FindMyNextBiteMonitor"], document["declared_self"]["declarations"])
        self.assertEqual(17, document["declared_self"]["matched"][0]["requests"])

    def test_a_declaration_that_matches_nothing_is_reported(self):
        analysis = analyse_fixtures([self.REAL], declarations=("NoSuchClient",))
        text = unwrapped(render_text(analysis))
        self.assertIn("--self matched nothing for: NoSuchClient", text)

    def test_the_dominant_client_in_the_json_carries_its_note(self):
        analysis = analyse_fixtures([self.REAL])
        document = render_json(analysis)
        self.assertEqual(17, document["dominant_client"]["requests"])
        self.assertIn("cannot tell", document["dominant_client"]["note"])


class WindowTests(unittest.TestCase):
    """A short window must not read like a week."""

    def test_a_short_window_is_reported_with_its_length(self):
        analysis = analyse_fixtures(["real-findmynextbite-2026-09-21-1828Z.log"])
        text = render_text(analysis)
        self.assertIn("(6.8 minutes, 21 requests)", text)
        document = render_json(analysis)
        self.assertEqual(408, round(document["coverage"]["duration_seconds"]))
        self.assertTrue(document["coverage"]["short_window"])

    def test_a_longer_window_carries_no_thin_window_warning(self):
        analysis = analyse_fixtures(["caddy-sample.log"])
        self.assertGreater(analysis.coverage_seconds, 3600)
        self.assertFalse(render_json(analysis)["coverage"]["short_window"])
        self.assertNotIn("describe that window only", render_text(analysis))


class DriftReportTests(unittest.TestCase):
    """W1 F9 and W2: a changed format is named, never guessed at."""

    def test_a_drifted_schema_refuses_and_explains(self):
        analysis = analyse_fixtures(["caddy-drifted.log"])
        self.assertEqual(STATE_NO_READABLE_LINES, analysis.state)
        self.assertEqual(1, len(analysis.sources[0].diagnostics))
        text = render_text(analysis)
        self.assertIn("WARNING", text)
        self.assertIn("request.uri", text)
        self.assertIn("status", text)
        self.assertIn("CANNOT ANSWER", text)
        self.assertNotIn("Site-wide", text)

    def test_a_partly_readable_source_is_flagged_at_the_top(self):
        analysis = analyse_fixtures(["malformed.log"])
        self.assertEqual(STATE_REPORTED, analysis.state)
        self.assertIn("were not read as requests", analysis.sources[0].diagnostics[0])
        text = render_text(analysis)
        self.assertIn("WARNING", text)
        self.assertIn("50%", text)

    def test_json_carries_the_diagnostics(self):
        analysis = analyse_fixtures(["caddy-drifted.log"])
        document = json.loads(render_json_text(analysis))
        self.assertTrue(document["sources"][0]["diagnostics"])


class HostHistoryTests(unittest.TestCase):
    """W1 F7: the tool must not assert a false present-tense fact about a real host."""

    def test_no_state_claims_the_host_still_keeps_no_log(self):
        # "If the web server keeps no access log" is a hypothetical and stays; a
        # present-tense claim about this host would be false since 2026-09-21.
        for name in ("empty.log", "caddy-no-agents.log", "caddy-drifted.log"):
            with self.subTest(fixture=name):
                analysis = analyse_fixtures([name])
                for text in (render_text(analysis), render_json_text(analysis)):
                    self.assertNotIn("findmynextbite.food keeps no", text)
                    self.assertNotIn("findmynextbite.food writes no", text)

    def test_the_history_is_stated_in_the_past_tense(self):
        analysis = analyse_fixtures(["caddy-no-agents.log"])
        self.assertIn("kept none until 2026-09-21", unwrapped(render_text(analysis)))


if __name__ == "__main__":
    unittest.main()
