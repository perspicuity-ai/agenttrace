.PHONY: help ci records test

help:
	@echo "make ci        run every check: the records, then the project checks"
	@echo "make records   check the Perspicuity records mechanically"
	@echo "make test      byte-compile the package and run the offline test suite"

ci:
	./scripts/ci.sh

records:
	./scripts/check_records.sh

test:
	./scripts/check-project.sh
