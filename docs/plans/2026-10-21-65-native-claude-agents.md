# Plan: native Claude Code agents (#65)

Issue: #65

## Approach

1. Copy the four agent drafts named in the issue (project manager, software
   engineer, code reviewer, CI watcher) into `.claude/agents/`.
2. Run each command and check each path they reference against this repo;
   fix anything that doesn't work (invalid frontmatter, run-specific merge
   authorization that conflicts with CLAUDE.md, shell variables used across
   Bash calls).
3. Add an "Agent-driven workflow" subsection to the CLAUDE.md Git Workflow
   section (roles, the per-issue flow, the 3-issues-in-flight limit) and a
   Documentation Sync row for agent definitions.
4. Reconcile the agents' plan handling with the CLAUDE.md Planning rule: the
   engineer always commits a plan under `docs/plans/`, and the reviewer flags
   a PR without one.
5. Add a CHANGELOG `[Unreleased]` entry.

## Files

- `.claude/agents/{project-manager,software-engineer-agent,code-review-agent,ci-agent}.md`
- `CLAUDE.md`
- `CHANGELOG.md`
- this plan

## Tests

No production code changes, so no unit tests. Verification: parse each
agent's frontmatter with `yaml.safe_load`; run the engineer's worktree,
install, gate and line-count commands; run the reviewer and CI watcher
`gh` commands against a merged PR; confirm every referenced label and path
exists.

## Out of scope

Any change under `src/`, `tests/` or `docs/site/`.
