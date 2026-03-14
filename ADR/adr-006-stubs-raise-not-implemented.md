# ADR-006: Stubs Raise NotImplementedError, Routes Return HTTP 501

**Date**: 2026-01-15
**Status**: Accepted
**Supersedes**: —

---

## Context

The application is built incrementally over 9 steps. Many modules exist as planned files but are not yet implemented. How should unimplemented code behave at runtime?

## Decision

- **Module stubs**: raise `NotImplementedError` with a descriptive message
- **Route stubs**: return `HTTP 501 Not Implemented` with a JSON body `{"detail": "not implemented"}`

## Rationale

- Raises loud errors immediately if stub code is accidentally called — no silent failures
- `NotImplementedError` is the Python convention for abstract/unimplemented methods
- HTTP 501 is the semantically correct response code for planned-but-not-ready endpoints
- Distinguishes clearly from HTTP 500 (unexpected error) — makes debugging easier
- Allows the frontend to check for 501 and show "coming soon" UI instead of an error state

## Consequence

- Implemented stubs are tracked in `ROADMAP.md` by step
- Every stub has a comment `# TODO: implement in Step N` to explain when it will be wired
- Do not silently return empty data or `None` from stubs — that would hide bugs
