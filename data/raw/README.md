# Raw Data — Saudi Labour Law & HR

This folder holds the original source documents ingested into the knowledge base.
**Do not edit files here** — re-download from the URLs in `data/sources.csv` if you
need to refresh.

## How to populate

The pipeline expects files at the paths declared in `data/sources.csv`. Two ways
to fill this folder:

### Option A — Manual download (recommended for fairness)

1. Open each `url` listed in `data/sources.csv`.
2. Save the file with the matching `file` path (e.g. `m51_en.pdf`).
3. Drop it into this folder.

### Option B — Programmatic fetch

```bash
python ingest/download_sources.py
```

This respects each source's license and only writes files that are missing.

## Sources at a glance

| source_id           | Title                                          | Lang  | Priority |
|---------------------|------------------------------------------------|-------|----------|
| `m51_en`            | Saudi Labour Law (Royal Decree M/51) — EN      | en    | 1 (core) |
| `m51_ar`            | نظام العمل — المرسوم الملكي م/51               | ar    | 1 (core) |
| `exec_reg_ar`       | اللائحة التنفيذية لنظام العمل                   | ar    | 1 (core) |
| `gosi_faq_en`       | GOSI FAQ                                       | en    | 2        |
| `wps_en`            | Wage Protection System overview                | en    | 2        |
| `nitaqat_en`        | Nitaqat bands                                  | en    | 3        |
| `female_workers_en` | Women in the workplace (MHRSD)                 | en    | 3        |
| `remote_work_ar`    | Remote Work guide (MHRSD)                      | ar    | 3        |

## Licensing

All listed sources are public Saudi government / ILO documents. Each row in
`sources.csv` records the originating publisher and the URL we used. If you add
new sources, **always record the license there** and prefer CC-BY / public-domain
material only.