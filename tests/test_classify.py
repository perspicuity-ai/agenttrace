"""The user-agent taxonomy: the twelve names, the ordering traps, the buckets."""

import unittest

from agenttrace.classify import (
    CATEGORY_BROWSER,
    CATEGORY_NAMED_AGENT,
    CATEGORY_OTHER_BOT,
    CATEGORY_SEARCH_CRAWLER,
    CATEGORY_UNKNOWN,
    NAMED_AI_AGENTS,
    classify,
)

#: One realistic string per named agent, as the vendor documents it.
NAMED_AGENT_STRINGS = {
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2; +https://openai.com/gptbot",
    "OAI-SearchBot": "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
    "ChatGPT-User": "Mozilla/5.0 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)",
    "ClaudeBot": "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "Claude-User": "Mozilla/5.0 (compatible; Claude-User/1.0; +https://www.anthropic.com/claude-user)",
    "PerplexityBot": "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Perplexity-User": "Mozilla/5.0 (compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)",
    "Google-Extended": "Mozilla/5.0 (compatible; Google-Extended/1.0; +http://www.google.com/bot.html)",
    "CCBot": "CCBot/2.0 (https://commoncrawl.org/faq/)",
    "Applebot-Extended": "Mozilla/5.0 (compatible; Applebot-Extended/0.3; +http://www.apple.com/go/applebot)",
    "Bytespider": "Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)",
    "meta-externalagent": "meta-externalagent/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)",
}

CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"
SAFARI = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
HEADLESS = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) HeadlessChrome/119.0.0.0 Safari/537.36"
)


class NamedAgentTests(unittest.TestCase):
    def test_the_brief_names_twelve_distinct_agents(self):
        self.assertEqual(12, len(NAMED_AI_AGENTS))
        self.assertEqual(len(NAMED_AI_AGENTS), len(set(NAMED_AI_AGENTS)))

    def test_every_named_agent_string_is_recognised(self):
        for name, user_agent in NAMED_AGENT_STRINGS.items():
            with self.subTest(agent=name):
                claim = classify(user_agent)
                self.assertEqual(CATEGORY_NAMED_AGENT, claim.category)
                self.assertEqual(name, claim.agent)
                self.assertEqual(name, claim.label)

    def test_every_agent_table_entry_has_a_test_string(self):
        self.assertEqual(set(NAMED_AI_AGENTS), set(NAMED_AGENT_STRINGS))

    def test_a_bare_agent_token_is_enough(self):
        for name in NAMED_AI_AGENTS:
            with self.subTest(agent=name):
                self.assertEqual(name, classify(f"{name}/1.0").agent)


class OrderingTests(unittest.TestCase):
    """A longer token must never be swallowed by a shorter one, or by a browser."""

    def test_applebot_extended_is_not_applebot(self):
        claim = classify(NAMED_AGENT_STRINGS["Applebot-Extended"])
        self.assertEqual("Applebot-Extended", claim.agent)

    def test_applebot_is_a_search_crawler_not_a_named_agent(self):
        claim = classify(
            "Mozilla/5.0 (compatible; Applebot/0.3; +http://www.apple.com/go/applebot)"
        )
        self.assertEqual(CATEGORY_SEARCH_CRAWLER, claim.category)
        self.assertEqual("Applebot", claim.label)

    def test_google_extended_is_not_googlebot(self):
        self.assertEqual("Google-Extended", classify(NAMED_AGENT_STRINGS["Google-Extended"]).agent)
        googlebot = classify("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
        self.assertEqual(CATEGORY_SEARCH_CRAWLER, googlebot.category)
        self.assertEqual("Googlebot", googlebot.label)

    def test_a_mozilla_prefixed_crawler_is_not_a_browser(self):
        for name in ("GPTBot", "ClaudeBot", "Googlebot", "bingbot", "Applebot"):
            with self.subTest(agent=name):
                claim = classify(f"Mozilla/5.0 (compatible; {name}/1.0; +https://example.invalid)")
                self.assertNotEqual(CATEGORY_BROWSER, claim.category)

    def test_a_headless_browser_is_automation_not_a_person(self):
        claim = classify(HEADLESS)
        self.assertEqual(CATEGORY_OTHER_BOT, claim.category)

    def test_meta_externalfetcher_is_not_merged_into_the_named_list(self):
        claim = classify("meta-externalfetcher/1.1")
        self.assertEqual(CATEGORY_OTHER_BOT, claim.category)
        self.assertIsNone(claim.agent)


class BucketTests(unittest.TestCase):
    def test_browsers(self):
        for user_agent in (CHROME, FIREFOX, SAFARI):
            with self.subTest(user_agent=user_agent):
                self.assertEqual(CATEGORY_BROWSER, classify(user_agent).category)

    def test_search_crawlers_by_name(self):
        for name in ("Googlebot", "bingbot", "DuckDuckBot", "YandexBot", "Baiduspider"):
            with self.subTest(crawler=name):
                claim = classify(f"Mozilla/5.0 (compatible; {name}/1.0)")
                self.assertEqual(CATEGORY_SEARCH_CRAWLER, claim.category)

    def test_other_bots(self):
        for user_agent in (
            "curl/8.4.0",
            "Wget/1.21.3",
            "python-requests/2.31.0",
            "Go-http-client/1.1",
            "facebookexternalhit/1.1",
            "Mozilla/5.0 (compatible; SemrushBot/7~bl; +http://www.semrush.com/bot.html)",
        ):
            with self.subTest(user_agent=user_agent):
                self.assertEqual(CATEGORY_OTHER_BOT, classify(user_agent).category)

    def test_unknown_when_no_claim_was_made(self):
        for user_agent in ("", "   ", "-", None, "Mozilla/5.0 (compatible)"):
            with self.subTest(user_agent=user_agent):
                claim = classify(user_agent)
                self.assertEqual(CATEGORY_UNKNOWN, claim.category)
                self.assertIsNone(claim.agent)


if __name__ == "__main__":
    unittest.main()
