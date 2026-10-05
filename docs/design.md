Known Limit (A3): Correction via bulk CSV upload is deliberately unsupported. All patient corrections must proceed through correct_patient_vital to ensure mandatory clinical justification, field-level diffing, and append-only audit preservation. Duplicate IDs during CSV upload are skipped and reported.

## Later

- Quarantine reasons are cut off in the narrow sidebar table
  (e.g. "Invalid patient_id: expect…"). Show the full reason, either
  wrapped in the table or listed under it. Ask Suresh which reads
  better for a clerk. (Found in v1.1 B2 hands-on check.)
  - When the store is unhealthy, the main area is blank. Show a clear
  message there too, not only in the sidebar. (Ask Suresh.)