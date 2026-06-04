"""Executive-assistant briefing for the AHSGR North Denver Chapter.

Two modules:
- brief.py    — generation + the fabrication gate (the gate is enforced in code,
                not just declared in spec YAML).
- delivery.py — Discord/Slack webhook delivery, channel routing, pause/test.

Ported from a stranded clone (~/projects/openclaw-agent, 2026-06-03) whose only
copy declared `forbid_fabrication: true` in YAML but never enforced it — and so
delivered hallucinated briefs to a live channel. See
support/project-ahsgr-denver/INCIDENT_2026-06-03_brief-fabrication.md.
"""
