"""Classify a self-declared user-agent string.

The taxonomy is deliberately shallow and data-driven. Named AI agents first — they
are the ones the report exists for — then search crawlers, other bots, browsers, and
unknown. The order is the whole trick: almost every crawler prefixes its string with
``Mozilla/5.0``, so a browser test that ran first would swallow most of the bots.

Nothing here verifies anything. A client chooses its own user-agent string, so the
output of :func:`classify` is a label for a claim.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

CATEGORY_NAMED_AGENT = "named_ai_agent"
CATEGORY_SEARCH_CRAWLER = "search_crawler"
CATEGORY_OTHER_BOT = "other_bot"
CATEGORY_BROWSER = "browser"
CATEGORY_UNKNOWN = "unknown"
#: A client the operator declared as their own (``--self``). Not a judgement by the tool:
#: a site's own monitor is usually the loudest bot in its log, and counting it as AI
#: traffic would be the most misleading thing this report could do.
CATEGORY_SELF = "declared_self"

#: Display order for the site-wide breakdown: the agents the report is about first, the
#: clients the operator set aside last.
CATEGORY_ORDER = (
    CATEGORY_NAMED_AGENT,
    CATEGORY_SEARCH_CRAWLER,
    CATEGORY_OTHER_BOT,
    CATEGORY_BROWSER,
    CATEGORY_UNKNOWN,
    CATEGORY_SELF,
)

CATEGORY_LABELS = {
    CATEGORY_NAMED_AGENT: "named AI agent",
    CATEGORY_SEARCH_CRAWLER: "search crawler",
    CATEGORY_OTHER_BOT: "other bot",
    CATEGORY_BROWSER: "browser",
    CATEGORY_UNKNOWN: "unrecognised",
    CATEGORY_SELF: "declared your own",
}

#: The named AI agents, exactly as the brief lists them. Order does not matter here:
#: the list is matched longest token first so that, for example, ``Applebot-Extended``
#: can never be counted as ``Applebot`` (which is a search crawler, matched later).
NAMED_AI_AGENTS = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-User",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "CCBot",
    "Applebot-Extended",
    "Bytespider",
    "meta-externalagent",
)

#: Search-engine crawlers. Googlebot is here rather than among the named AI agents:
#: the brief lists ``Google-Extended``, which is a different claim.
SEARCH_CRAWLERS = (
    "Googlebot",
    "Google-InspectionTool",
    "GoogleOther",
    "Google-Read-Aloud",
    "AdsBot-Google",
    "Mediapartners-Google",
    "APIs-Google",
    "FeedFetcher-Google",
    "Bingbot",
    "BingPreview",
    "msnbot",
    "DuckDuckBot",
    "Applebot",
    "YandexBot",
    "YandexImages",
    "Baiduspider",
    "Sogou",
    "Exabot",
    "Slurp",
    "PetalBot",
    "SeznamBot",
    "Qwantify",
    "MojeekBot",
    "ia_archiver",
    "Naver",
    "Yeti",
    "Daum",
)

#: Everything else that is plainly a robot or a client library rather than a person.
#: ``meta-externalfetcher`` is Meta's other AI fetcher; it is not one of the twelve
#: named agents, so it is counted here rather than merged into that list.
OTHER_BOT_PATTERNS = (
    "HeadlessChrome",
    "externalfetcher",
    "bot",
    "spider",
    "crawl",
    "slurp",
    "scrape",
    "scrapy",
    "curl/",
    "wget/",
    "python-requests",
    "python-urllib",
    "aiohttp",
    "httpx",
    "Go-http-client",
    "okhttp",
    "java/",
    "httpclient",
    "libwww-perl",
    "axios/",
    "node-fetch",
    "undici",
    "guzzle",
    "feedfetcher",
    "feedreader",
    "facebookexternalhit",
    "whatsapp",
    "telegrambot",
    "discordbot",
    "slackbot",
    "twitterbot",
    "linkedinbot",
    "pinterest",
    "embedly",
    "validator",
    "lighthouse",
    "uptime",
    "pingdom",
    "nagios",
    "semrushbot",
    "ahrefsbot",
    "mj12bot",
    "dotbot",
    "blexbot",
    "dataforseo",
    "serpstatbot",
    "screaming frog",
    "zoominfobot",
    "megaindex",
    "monitoring",
    # Health checks and monitors. A site's own monitor is usually the loudest client in
    # its log; these tokens at least stop it being counted as an unrecognised visitor.
    # ``--self`` is the honest fix when the operator knows which one is theirs.
    "monitor",
    "healthcheck",
    "health-check",
    "kube-probe",
    "blackbox",
)

#: A browser has to look like one: a Mozilla-compatible string carrying an engine
#: token, or one of the small text browsers. Anything less is not assumed to be a
#: person — see CATEGORY_UNKNOWN.
BROWSER_PATTERNS = (
    "Firefox/",
    "Seamonkey/",
    "Chrome/",
    "Chromium/",
    "CriOS/",
    "FxiOS/",
    "Edg/",
    "EdgA/",
    "EdgiOS/",
    "OPR/",
    "Opera/",
    "SamsungBrowser/",
    "Vivaldi/",
    "Brave/",
    "YaBrowser/",
    "Trident/",
    "MSIE ",
    "Safari/",
)

_MOZILLA = re.compile(r"Mozilla/", re.IGNORECASE)
_TEXT_BROWSERS = ("Lynx/", "Links (", "w3m/", "ELinks/")

# Longest first, so a longer token always wins over a prefix of itself.
_NAMED_RULES = tuple(
    (name.lower(), name) for name in sorted(NAMED_AI_AGENTS, key=len, reverse=True)
)
_SEARCH_RULES = tuple(
    (name.lower(), name) for name in sorted(SEARCH_CRAWLERS, key=len, reverse=True)
)
_OTHER_BOT_RULES = tuple(token.lower() for token in OTHER_BOT_PATTERNS)
_BROWSER_RULES = tuple(token.lower() for token in BROWSER_PATTERNS)
_TEXT_BROWSER_RULES = tuple(token.lower() for token in _TEXT_BROWSERS)


@dataclass(frozen=True)
class Claim:
    """What a user-agent string claims to be."""

    category: str
    #: Canonical agent name for a named AI agent, otherwise ``None``.
    agent: str | None
    #: Grouping label: the agent name, or the category's display label.
    label: str

    @property
    def is_named_agent(self) -> bool:
        return self.category == CATEGORY_NAMED_AGENT


def _claim(category: str, agent: str | None = None) -> Claim:
    return Claim(category=category, agent=agent, label=agent or CATEGORY_LABELS[category])


def classify(user_agent: str | None, declared_self: Sequence[str] = ()) -> Claim:
    """Return the claim made by *user_agent*.

    An absent, empty or ``-`` user-agent is ``unknown``: no claim was made at all.

    A token in *declared_self* — the operator's ``--self`` declarations — wins over every
    rule below it, including the named agents. That is deliberate: the operator knows
    which client is the site's own, and a declaration is the only way the tool can avoid
    presenting a site's own monitor as somebody's agent.
    """

    text = (user_agent or "").strip()
    lowered = text.lower()

    for token in declared_self:
        cleaned = (token or "").strip()
        if cleaned and cleaned.lower() in lowered:
            return Claim(category=CATEGORY_SELF, agent=None, label=cleaned)

    if not text or text == "-":
        return _claim(CATEGORY_UNKNOWN)

    for token, name in _NAMED_RULES:
        if token in lowered:
            return _claim(CATEGORY_NAMED_AGENT, name)

    for token, name in _SEARCH_RULES:
        if token in lowered:
            return _claim(CATEGORY_SEARCH_CRAWLER, name)

    for token in _OTHER_BOT_RULES:
        if token in lowered:
            return _claim(CATEGORY_OTHER_BOT)

    if _MOZILLA.search(text):
        for token in _BROWSER_RULES:
            if token in lowered:
                return _claim(CATEGORY_BROWSER)

    for token in _TEXT_BROWSER_RULES:
        if token in lowered:
            return _claim(CATEGORY_BROWSER)

    return _claim(CATEGORY_UNKNOWN)
