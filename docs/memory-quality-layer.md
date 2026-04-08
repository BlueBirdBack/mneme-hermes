# Memory Quality Layer Spec

## Problem
Memory can exist but still fail in practice:
- stale facts
- duplicates
- contradictions
- poor recallability
- weak provenance
- important facts buried in notes or transcripts

## Goal
Create a Mneme-inspired quality layer for Hermes memory.

## Candidate responsibilities
1. Inspect built-in memory stores
2. Inspect other evidence sources such as wiki raw sources or transcripts
3. Detect quality issues
4. Suggest durable fact promotions with source citations
5. Suggest consolidations or repairs
6. Keep outputs reviewable

## Important rule
This layer should improve trust in memory, not replace Hermes with another opaque memory stack.

## Future forms
- standalone scripts
- skill-driven workflow
- plugin tool surface
- external provider companion layer
