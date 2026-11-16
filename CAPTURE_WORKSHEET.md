# Offline observation capture worksheet

Open `CAPTURE_WORKSHEET.html` from the extracted folder in a modern browser. It helps prepare the existing `index,field` checklist and `index,field,value` observations formats without reading a trace or connecting to a chart. It is a capture aid, **not a chart, validator, strategy tester or independent evidence**.

## Single-snapshot evidence bundle

After planning and recording cells, select **Download evidence bundle JSON**. The worksheet validates the plan once and captures its checklist and recorded observations together in one file. Unrecorded values are omitted; an explicitly recorded blank is included. At least one planned cell is required. The file is not encrypted or automatically saved, and it may contain sensitive information. It is for the audit, **not** the editable worksheet backup. Keep a separate backup if you need to resume editing.

Move the bundle into the extracted project folder with your prepared bars, then use your actual filenames and a new output name:

```bash
python -m reference.audit_report --bars your_bars.csv --bundle retest_evidence_bundle.json --output your_audit.html
```

Do not combine `--bundle` with `--observations` or `--required`. The audit validates the embedded CSVs and rejects observations not present in the checklist. It cannot prove the bundle was genuinely produced by the worksheet, that your observations are true, or that the plan is complete. The bundle and bars are read sequentially, not simultaneously. See `AUDIT_REPORT.md` for exit codes and privacy. To try a synthetic example with one deliberately missing observation, use `--bars sample_trace.csv --bundle sample_evidence_bundle.json`; a report with exit 1 is expected.

## Separate CSV workflow (still supported)

1. Record source, symbol, timeframe, timezone, settings, bar mapping and warm-up separately as described in `REPLAY_CAPTURE.md`. Use the same bar indexes as the prepared bars, not a guessed chart identifier.
2. Add planned cells by bar index and field. Indexes must be nonnegative safe integers; the worksheet supports up to 500 unique index/field pairs and values up to 1,024 UTF-16 code units. Leading zeros are normalized. The tool cannot check whether an index exists in your eventual trace.
3. Mark **Recorded** only after independently observing that value. A checked empty value is a recorded blank; an unchecked row is missing even if it retains text. Text remains in the form when unchecked and is exported if rechecked. The comparator trims surrounding whitespace and validates numeric fields. The worksheet does not check whether values are correct or numeric.
4. Download the checklist and observation CSVs **without editing the worksheet between downloads**. They are separate snapshots: edits between downloads can make the files inconsistent. The browser may rename files rather than overwrite a prior download; use the actual filenames. Files are not encrypted and may contain sensitive values.
5. Use your prepared bars and the two files in the offline audit. For example, after moving the downloads into the extracted folder:

```bash
python -m reference.audit_report --bars your_bars.csv --observations retest_observations.csv --required retest_checklist.csv --output your_audit.html
```

The audit requires a new output filename. With an empty observations file, all planned cells will be reported missing. The CLI validates trace indexes and formats; a completed checklist can still omit important behavior, and a match is not Pine parity or proof of profitability.

## Save and restore a private draft

Choose **Download backup JSON** to save the worksheet, including incomplete indexes, duplicate entries, recorded blanks and text held in unchecked rows. It is an unencrypted local file containing potentially sensitive information, not a CSV for the comparator and not proof of observations. The browser may rename later downloads; retain the file you intend. There is no auto-save or account sync.

To resume, choose **Restore backup** and select a v0.17 worksheet backup (version 1). The file is read locally; invalid UTF-8, invalid JSON, unsupported versions, malformed rows and files over 4 MiB are rejected without changing the worksheet. Up to 500 rows, 64 UTF-16 code units per draft index and 1,024 per value are supported. When cells already exist, confirmation is required before replacing all of them; cancelling leaves them intact. If the worksheet changes while the file is being read, restore is cancelled. This is replacement, not merge or undo. Review restored values and indexes before CSV export; backups can preserve duplicates or invalid/incomplete indexes, which CSV export will reject. The file format uses arrays only to avoid duplicate JSON object keys. A valid backup does not prove provenance or correctness.

No auto-save or account sync is used; refreshing or closing discards the worksheet unless a backup has been downloaded. Some browsers may warn before leaving. Downloaded CSVs are not loaded back by this worksheet; JSON backups and CSV exports serve different purposes. Preserve source notes separately. The content is exported without changing its meaning: **spreadsheet applications may execute formula-like cells** (e.g. values beginning `=`, `+`, `-`, or `@`). Open untrusted files in a plain-text editor or with a safe import method; do not remove characters merely to make the check pass. No network requests are needed for the tested local flow.
