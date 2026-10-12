Known Limit (A3): Correction via bulk CSV upload is deliberately unsupported. All patient corrections must proceed through correct_patient_vital to ensure mandatory clinical justification, field-level diffing, and append-only audit preservation. Duplicate IDs during CSV upload are skipped and reported.

## Later

- Quarantine reasons are cut off in the narrow sidebar table
  (e.g. "Invalid patient_id: expect…"). Show the full reason, either
  wrapped in the table or listed under it. Ask Suresh which reads
  better for a clerk. (Found in v1.1 B2 hands-on check.)
  - When the store is unhealthy, the main area is blank. Show a clear
  message there too, not only in the sidebar. (Ask Suresh.)
  - "Vitals by Group" table is too wide (16+ columns; sugar cut off).
  Show one vital at a time, or only mean / median / p90. (Ask Suresh.)

  ## v1.1 B3 timings

Mean + std of 4 vitals, median of 20 runs, seed 42
(scripts/bench_stats.py, measured 2026-10-12 on my laptop)

| Input     | Rows   | Plain loop (ms) | Vectorised (ms) |
|-----------|--------|-----------------|-----------------|
| sample    | 50     | 0.040           | 0.509           |
| synthetic | 50,000 | 37.827          | 1.429           |

At 50 rows the plain loop was about 13x faster: pandas has a fixed
start-up cost before it does any arithmetic. At 50,000 rows pandas was
about 26x faster. We keep the vectorised version because a real hospital
has thousands of patients, not 50.