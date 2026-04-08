# Repo-Aware Wiki Updater Spec

## Problem
A repository like Hermes changes frequently. Re-reading the entire repo for every wiki refresh is wasteful.

## Goal
Build a delta-based wiki maintenance workflow that updates knowledge from git history.

## Proposed flow
1. Store last ingested commit for a tracked repo
2. Fetch latest git state
3. Compute:
   - commits since last ingest
   - changed files
   - changed top-level subsystems
4. Generate a raw-source markdown snapshot summarizing that delta
5. Map changed paths to likely affected wiki pages
6. Update only relevant wiki pages
7. Record the new ingested commit

## Important non-goals
- do not create one wiki page per file
- do not create one wiki page per commit
- do not silently rewrite large parts of the wiki without a reviewable summary

## Candidate state format
```json
{
  "repos": {
    "/path/to/repo": {
      "last_ingested_commit": "abc123",
      "last_ingested_at": "2026-04-08T00:00:00Z",
      "wiki_path": "/path/to/wiki"
    }
  }
}
```

## Candidate page mapping examples
- `run_agent.py` -> `agent-runtime`, `system-prompt-architecture`
- `model_tools.py`, `tools/*` -> `tool-system`, `terminal-and-processes`, `programmatic-tool-calling`
- `gateway/*` -> `cli-and-gateway`, `gateway-session-model`
- `plugins/memory/*` -> `memory-system`, `memory-provider-architecture`
- `website/docs/*` -> `product-and-documentation-surface`
