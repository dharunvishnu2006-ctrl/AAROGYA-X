# Platform decisions — AAROGYA X

Three decisions made in v1.1 that every module and every later version
builds on. Changing one of them later means changing the whole platform.

| Decision | Made in | Why | What it makes possible |
|---|---|---|---|
| Append, never overwrite: a correction is added with its reason; the old value is kept | A3 (ADR 0001) | A patient's history must show what was known, and when | A patient timeline; the v4 deterioration model needs it |
| Identity = patient_id, nothing else | v1.1 Batch 2 | Matching on name, age and city can merge two people or split one | Safe merging of duplicate records later (v2) |
| Occupancy = open stays / beds, per hospital | v1.1 Batch 4 (ADR 0002) | Patients living in a city are not patients in beds | M2: wards, transfers, census, the v6 command centre |

## Rules that follow from them
- No module edits a stored vital in place. It appends a correction.
- No module decides "same patient" by any field except patient_id.
- No module computes occupancy from where patients live.