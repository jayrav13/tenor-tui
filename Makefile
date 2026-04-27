.PHONY: snapshots demos docs docs-strict docs-serve help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-15s %s\n", $$1, $$2}'

snapshots:  ## Regenerate SVG snapshots from bin/snapshot
	poetry run python bin/snapshot

demos:  ## Regenerate VHS GIFs from docs/tapes/*.tape
	@for tape in docs/tapes/*.tape; do \
		echo "→ vhs $$tape"; \
		vhs $$tape; \
	done

docs:  ## Build the MkDocs site (output to docs/site/site/)
	cd docs/site && poetry run mkdocs build

docs-strict:  ## Build the MkDocs site with --strict (fails on broken links)
	cd docs/site && poetry run mkdocs build --strict

docs-serve:  ## Serve the MkDocs site at http://127.0.0.1:8000
	cd docs/site && poetry run mkdocs serve
