# AAROGYA X - Home page polish (after v1.1 Batch 5)
# Modules: M15 dashboard only. Learning order unchanged (step 80).

## Goal
Give the Batch 5 Overview the family hero band: the AAROGYA logo,
the Vision and Today lines, the logo's green as the accent.

## Tasks
1. src/brand.py (or aarogya/m15_dashboard/brand.py): name, vision
   "AI-powered healthcare platform", today "Today (v1.1): patient
   records, rule-based risk, beds and occupancy, FHIR export -
   synthetic data", accent green from the logo (about #15803D),
   band colour measured from the logo edge, logo path
   assets/logo.jpeg.
2. render_hero(): the family band (about 200 px; logo 180 px high;
   name in the logo's gold; Vision; Today in light green; version
   from versions.json). It replaces the Batch 5 header title line.
   The hospital selector, patient search and the caption
   "Synthetic data - not for clinical use" stay, directly below.
3. st.logo(assets/logo.jpeg) so every other page shows a small logo.
4. .streamlit/config.toml: primaryColor = the accent (replaces the
   Batch 5 teal/blue).
5. Batch 5's "no unsafe_allow_html" stays, with ONE exception:
   render_hero(). Every string escaped; the logo as base64
   (compressed to 150 KB or less).
6. Tests: the Today version equals versions.json; render_hero escapes
   a string containing <script>; every page still runs (AppTest).

## Must not
- Change any number, panel or rule from Batch 5.
- Add a package (Pillow comes with Streamlit).

## Verification
- Laptop 1366 x 768: hero band and the KPI row visible, no scroll.
- Light and dark: the band and the cards readable.
- The logo's edge and the band meet with no visible line.

## Changed by Dharun (18 Oct 2026)
- No hero band and no logo: the bright logo and the dark band did not fit the calm white page. The Overview top is plain text - title, Vision line, Today line (version from versions.json).
- No HTML anywhere in the app (a test scans every file).