# Vision

Mneme-Hermes should make Hermes memory and knowledge workflows more trustworthy over time.

## Core idea

Do not replace Hermes memory with another opaque system.
Instead:
- inspect it
- repair it
- enrich it
- track provenance
- keep it healthy as repos and conversations evolve

## Design principles

1. Provenance first
Every promoted fact should point back to a source.

2. Delta-aware maintenance
Prefer incremental updates over full re-ingestion.

3. Subsystem summaries, not page-per-file mirroring
The output should stay navigable.

4. Hermes-native where useful
Fit the existing Hermes architecture instead of fighting it.

5. Human-reviewable outputs
No black-box silent rewriting of important memory.
