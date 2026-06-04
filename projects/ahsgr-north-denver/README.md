# projects/ahsgr-north-denver

Working folder for the AHSGR North Denver Chapter client engagement.

| Folder | Purpose |
|---|---|
| `working/` | In-progress files, scratch, drafts under active development |
| `output/` | Completed deliverables (roster CSVs, reports, exports) |
| `archive/` | Frozen/versioned snapshots of completed work |
| `memory/` | Persistent project notes, decisions, context for future sessions |

## Promote outputs

Completed roster CSVs → data-hub-ahsgr:

```bash
cd ~/Laboratory/data-hub-ahsgr
.venv/bin/python cli.py promote \
  ~/Laboratory/project-ahsgr-denver/projects/ahsgr-north-denver/output/<file>.csv \
  --topic board/roster --source-agent project-ahsgr-denver
```
