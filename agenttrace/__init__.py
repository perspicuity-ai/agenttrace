"""agenttrace — what claimed AI agents asked a web server for.

Standard library only. The tool reads an access log that already exists: it never
captures traffic, never opens a network connection, and never prints a client
address. Every count it produces is a count of *claims*: a user-agent string is
self-declared and trivially spoofable.

Run it as ``python3 -m agenttrace <log> [<log> ...]``.
"""

__version__ = "0.1.0"

CLAIM_BOUNDARY = (
    "A user-agent string is self-declared and trivially spoofable. Every count "
    "below is a count of claims to be that agent, not a count of verified agents."
)

TOOL_NAME = "agenttrace"

#: The discovery files the report singles out, most important first. Whether the first
#: of these is read at all is the question this tool exists to answer.
DISCOVERY_FILES = ("/llms.txt", "/robots.txt", "/sitemap.xml")

#: The host this tool was written for, which keeps no access log. It is named in the
#: empty output because a zero from a server that logs nothing means nothing.
NO_LOG_HOST = "findmynextbite.food"
