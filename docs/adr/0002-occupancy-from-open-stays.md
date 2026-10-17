# ADR 0002 — Occupancy is open stays divided by beds, per hospital

Status: accepted (v1.1 Batch 4, 17 October 2026)

## Context
v1 showed occupancy as "patients living in a city / one hospital's beds".
Chennai showed 1.0%. The arithmetic was right, but the number answered
the wrong question: living in a city is not lying in a bed, and one
hospital's beds are not a city's beds. Because 1.0% looked reasonable,
nobody would have questioned it.

## Decision
- A hospital stay is recorded in a "stays" table: patient, hospital,
  ward, bed, admitted_at (UTC), discharged_at (UTC or empty).
- An open stay is one with no discharge time yet.
- Occupancy per hospital = open stays at that hospital / its total beds.
- Above 100% is shown and flagged, never clamped.
- A hospital with 0 beds shows "—", never 0.0%.
- Stay rules (no double admission, no double-booked bed, discharge
  after admission, no discharge without admission) live in one place:
  aarogya/m2_his/stays.py. No copy of them in SQL constraints.
- Every query reads one table (no joins before v2).

## Consequences
- Occupancy depends only on stays, never on where patients live.
- Wards, transfers, census and the v6 command centre can build on stays.
- Rules are enforced in Python only, so a script writing straight to the
  database could break them. Database-level checks are a v2 decision.