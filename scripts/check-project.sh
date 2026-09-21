#!/bin/sh
# Project-specific checks.
#
# Everything that must be true before a commit belongs here. `make ci` runs this after
# the record check, so a failure here fails the build.
#
# Two checks, both offline:
#   1. the package and the tests byte-compile;
#   2. the test suite passes, driven from the synthetic logs in tests/fixtures/.
#
# The tests make no network call and read nothing outside this repository. They do not
# establish that either log format is what a given server writes, that the twelve agent
# names match what the vendors actually send, or that any host produces a log at all.
set -eu

cd "$(dirname "$0")/.."

echo "== byte-compile =="
python3 -m compileall -q agenttrace tests
echo "agenttrace/ and tests/ compile"

echo
echo "== tests =="
echo "python3 -m unittest discover -s tests -t ."
python3 -m unittest discover -s tests -t .
