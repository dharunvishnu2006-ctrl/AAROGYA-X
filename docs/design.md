# AAROGYA X — design notes (v1.1)

Not for clinical use. Synthetic data only; no real patient anywhere.

## Data model (SQLite, data/aarogya.db)

| Table | Holds | Key rules |
|---|---|---|
| patients | patient_id, name, age, gender, bmi, bp_systolic, bp_diastolic, sugar_fasting, city, updated_at (UTC) | patient_id matches ^P[0-9]{3,}$; identity is patient_id only |
| corrections | one row per corrected vital: patient, field, old value, new value, clinical justification, recorded_at (UTC) | append-only; never overwritten (ADR 0001) |
| ingest_log | one row per real upload: recorded_at (UTC), rows_read, accepted, rejected | no patient data; the seed is not an upload |
| hospitals | hospital_id, name, city, total_beds | from HOSPITAL_NETWORK |
| stays | stay_id, patient_id (FK), hospital_id (FK), ward, bed, admitted_at (UTC), discharged_at (UTC or empty) | rules in aarogya/m2_his/stays.py (ADR 0002) |

Every query reads one table (no joins before v2). Times are stored in
UTC and shown in IST.

Known Limit (A3): Correction via bulk CSV upload is deliberately unsupported. All patient corrections must proceed through correct_patient_vital to ensure mandatory clinical justification, field-level diffing, and append-only audit preservation. Duplicate IDs during CSV upload are skipped and reported.

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

## Known limits (v1.1)

- Not for clinical use. Synthetic data only. Risk bands come from fixed
  thresholds, not a validated clinical model.
- No authentication yet - API is localhost only (127.0.0.1).
  Anyone using this computer can call it; nobody else can reach it.
  Before a real hospital could use it: login, roles (who may see
  what), HTTPS, and an audit record of who read which patient.
- Flask's development server request log is switched off, because it
  printed patient_ids in request lines. A production server will need
  request logging that never records ids.
- Stay rules are enforced in Python only. A script writing straight to
  the database could break them; database-level checks are a v2 decision.
- Age is stored, not date of birth (needs a schema change - v2).
- No transfers between wards, waiting lists or login (later versions).
- FHIR export only - no import yet (v2); not tested with any other
  hospital system; no connection to ABDM.
- In the FHIR export, an Observation's time is when the patient record
  last changed (updated_at), not when the vital was measured. A real
  measurement time needs a schema change (v2).
- Ward and bed are not in the FHIR export; that would need FHIR
  Location resources.
- The FHIR validator (fhir.resources) checks the structure, not the
  code lists. The LOINC codes are guaranteed by our own tests, checked
  by hand on loinc.org.

## Later

- Quarantine reasons are cut off in the narrow sidebar table
  (e.g. "Invalid patient_id: expect…"). Show the full reason, either
  wrapped in the table or listed under it. Ask Suresh which reads
  better for a clerk. (Found in v1.1 B2 hands-on check.)
- When the store is unhealthy, the main area is blank. Show a clear
  message there too, not only in the sidebar. (Ask Suresh.)
- "Vitals by Group" table is too wide (16+ columns; sugar cut off).
  Show one vital at a time, or only mean / median / p90. (Ask Suresh.)