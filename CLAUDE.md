# AAROGYA X — rules for Claude Code

## Project
AAROGYA X: a hospital software platform, 15 modules, built version by
version. Current version: v1.1. May use only Python Layer 1 tools
(roadmap steps 1-80): no SQL joins, no PostgreSQL, no scikit-learn.

## Commands
- Run app: streamlit run app.py
- Run tests: pytest
- Full check: python scripts/check.py (after Batch 1)

## Rules
- IMPORTANT: ask before adding any dependency.
- Synthetic data only. Secrets only in environment variables (.env, gitignored).
- Extend, never rewrite. A1-A3 code and its 27 tests must keep passing.
- One patient record shared by every module. Corrections are appended,
  never overwritten.
- Never write a patient name, patient_id or vital value into a log line.
- Every feature gets pytest tests. Run them and show me the output.
- Do not commit. Do not edit README.md, docs/build_log.md or docs/specs/.

## Each batch
- Before planning, explain in 5 plain lines what the batch builds
  and why the hospital needs it.
- Ask before installing a package, deleting a file or touching
  anything outside this folder.

## Code layout
- Comments 4-6 words, verb first. Max 76 characters per line, comment included.
- No inline comment on a def or class line.
- Align comments in a block to the longest code line + 2 spaces.
- A long line gets its comment on the line above. No blank line between
  a comment and its code.