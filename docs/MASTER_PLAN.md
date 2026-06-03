# project-ahsgr-denver — MASTER PLAN

> **LIVING DOCUMENT.** Created 2026-06-02 while triaging audio during the *ratfam* corpus build —
> AHSGR-Denver-Metro content that surfaced was routed here to work on later. Mirrors the two-repo
> split: **raw + index live in `data-hub-ahsgr`**; **project-ahsgr-denver consumes the index**.
> Update Progress/Findings each session.

## Architecture (per Bryan)
- **Raw audio (calls, recordings) lives in `data-hub-ahsgr/raw/`** — kept out of the project repo
  because of size — **indexed there** (transcribe → RAG/structured), and **accessible to
  project-ahsgr-denver** (project = consumer/structured layer, same pattern as project-ratfam ↔
  data-hub-ratfam).
- **NotebookLM artifacts (audio overviews, videos) are OUTPUTS** for chapter meetings / YouTube /
  the *Unsere Zeitung* newsletter — a publish workflow, NOT raw-to-index. They live in a
  studio/published area (not `raw/`).

## Already relocated (2026-06-02, during ratfam triage)
- **Raw calls → `data-hub-ahsgr/raw/media/`:** `Shirley_Phone_Call_2026_04_28*` + `0428Call.*`
  (incl. whisperX transcripts .vtt/.srt/.tsv/.json), and 4 business calls (`NewMark Merrill`,
  `National Credit Care`, `American Driving Academy`, `N Pecos St` — all variants + N-Pecos
  `.qta`/`_cleaned.*`/`_speakers`).
- **Maifest content package (41 files) → `data-hub-ahsgr/denver-metro-chapter/maifest-2026/`:**
  the Maifest board-meeting recording (raw), NotebookLM audio podcasts + videos (Redemptioner series,
  Empress/False-Tsar/Pugachev, Roots & Ribbons, Volga German Journey/Migration), source research
  (.md/.pdf: German Redemptioner, Dismantling the Redemptioner Trap, Living Table, Diaspora),
  newsletter/event graphics (Unsere Zeitung cover, Spring Maifest Eventbrite banners), Gmail PDFs.

# PHASE 1 — Organize, index, publish the AHSGR-Denver audio + Maifest corpus
1. **Sort `maifest-2026/`** into proper subtypes: `raw/` (the board-meeting recording),
   `studio/` (NotebookLM audio+video artifacts), `research/` (source .md/.pdf), `assets/` (newsletter
   + Eventbrite graphics). Decide the canonical studio/published folder convention.
2. **Index the raw audio** in `data-hub-ahsgr` (transcribe board meeting + the relocated calls —
   whisperX already produced 0428Call transcripts; reuse/normalize) → RAG/structured, exposed to
   project-ahsgr-denver (mirror the ratfam `build_correspondence_index`/MCP pattern).
3. **Publish artifacts**: route NotebookLM audio/video to the chapter-meeting / YouTube / *Unsere
   Zeitung* newsletter workflow (likely via notebooklm-agent + newsletter-agent).
4. **Sweep the rest of `~/Downloads`** (a large mixed NotebookLM-artifact staging area): grab the
   remaining AHSGR/Volga-German pieces still there — `Journey_to_the_Steppe.mp4`,
   `The_Empire_Builder*.mp4`, `The_Commodified_Labor_Pipeline__Mittelberger*.mp4`, etc. → here.
   **NOT AHSGR** (route to their own projects, do not bring here): `Level_Up_Your_Writing`,
   `Mastering_SQ3R_Strategy` (study/education → frcc/research?), `Convergence_Disruption`,
   `Illusion_of_Choice`, `DIY_Rabbit_Taxidermy` (unknown — likely research-agent/other).

## Open decisions
- Studio/published folder convention for NotebookLM artifacts in `data-hub-ahsgr` (vs notebooklm-agent output).
- Verify `Who_writes_your_media_menu.m4a` is AHSGR (moved here tentatively — may be media-literacy/other).
- Chapter scope: `denver-chapter` vs `denver-metro-chapter` (Maifest content is "AHSGR Denver Metro").

## Provenance
Surfaced during the **project-ratfam** evidence-corpus build (see
`~/Laboratory/project-ratfam/docs/MASTER_PLAN.md` + `case-file-shared/03_analysis/audio-triage.md`).
None of this is Hein-case material.
