# Offline replay audit report

The audit tool assembles one **local HTML document** from the existing Python preflight, reference trace and optional manually recorded observation comparator. It does not connect to a chart, run Pine, simulate orders or establish trading performance. A match covers only supplied cells and a checklist is only as complete as the plan you provide. `DEMO_AUDIT.html` is a clearly marked synthetic example, not market evidence.

## Quick start

From the extracted project folder (Python 3.10+):

```bash
python -m reference.audit_report --bars sample_trace.csv --observations sample_observations.csv --required sample_required.csv --output audit.html
```

Open `audit.html` in a modern browser. The sample bars and observations are made up; the sample preflight deliberately reports missing session/confirmation flags and warm-up inputs. The command creates a new file only; choose a fresh output name each time. Do not treat a zero exit as proof of correctness.

For your own prepared bars, you can run preflight and the model without supplying observations:

```bash
python -m reference.audit_report --bars your_bars.csv --config your_config.json --check-tick --strict --output your_audit.html
```

Omit `--config` to use the Python reference defaults, including a tick size of 0.01. Set the tick deliberately before using `--check-tick`; adjusted feeds or variable tick schedules can produce legitimate warnings. Add `--observations your_observations.csv` to compare independently recorded cells and, optionally, `--required your_checklist.csv` to check planned coverage. A checklist requires an observations file (which may be header-only to identify all planned cells as missing). Follow `REPLAY_CAPTURE.md` for input formats, collection steps and limitations.

## Use a worksheet evidence bundle

`CAPTURE_WORKSHEET.html` can export a single bundle from one worksheet snapshot. From the extracted folder, for example:

```bash
python -m reference.audit_report --bars sample_trace.csv --bundle sample_evidence_bundle.json --output bundle_audit.html
```

The supplied example is synthetic and intentionally has one missing planned cell, so exit 1 is expected. For your own evidence, replace the filenames and keep the bundle private. `--bundle` cannot be used with `--observations` or `--required`; separate CSV mode is unchanged. The input is an array-only versioned JSON envelope containing checklist and observation CSV strings, limited to 8 MiB; malformed JSON, unsupported formats, invalid CSVs, duplicates, absent trace indexes and recorded cells outside the checklist are rejected without producing a report. The audit hashes the exact bundle input bytes, not each embedded CSV separately. It cannot authenticate the bundle or prove it was produced from one genuine worksheet snapshot; files can be edited. Bars, config and bundle are read sequentially. Use a worksheet backup to resume editing; the bundle is not a backup.

## Optional cadence review

Use `--expected-seconds 300` (or your own whole-second interval, 1–31,536,000) to add an advisory timestamp check to the audit. It compares only adjacent offset-aware instants. Positive intervals shorter or longer than expected and pairs that cannot be checked are listed as warnings using the later bar's index; a single bar is also reported as unassessed. Equal or backward instants have separate existing order warnings. With `--strict`, any warning causes exit 1 after report creation. The overview states whether cadence was requested. See `CADENCE_GUIDE.html` for examples and limitations. No exchange schedule or missing-bar count is inferred.

## What the report shows

- Bar count, preflight warning categories and whether a comparison was performed. A missing observations file is explicitly **not run**, not a pass.
- Up to 10 example bar indexes per warning category; up to 50 differences and 50 missing planned cells; and the first 25 model-event bars. Longer individual values are truncated for display. Run the existing `reference.preflight`, `reference.engine` and `reference.compare_trace` commands for full output and inspect the original inputs.
- When observations are present, recorded-cell and mismatch totals and bar coverage. A recorded blank is not an absent cell. No checklist means planned coverage is not assessed.
- The effective Python model configuration and SHA-256 fingerprints of each supplied input. The tool reads each input once and analyzes its private temporary copy. Inputs are read sequentially, not as an atomic simultaneous snapshot. Hashes identify those copied bytes, not the truth, origin, publisher or executed software; separately record the software ZIP hash and chart context.

## Exit codes and safety

- **0:** report created, no differences or missing planned cells; warnings may still exist when `--strict` is omitted, and comparison may not have run.
- **1:** report created and at least one difference, missing planned cell, or (with `--strict`) a preflight warning was found. Investigate; do not fabricate data to clear warnings.
- **2:** invalid input or file error; the report was not successfully completed; inspect the destination if interrupted. Existing output files, including symlinks and hard links, are never overwritten. A temporary file is written beside the destination and linked into place without clobbering; filesystems without hard-link support may reject this operation.

Inputs are limited to 8 MiB each. They are not modified. The private temporary directory holds copies while the command runs and is normally deleted afterward; an abrupt termination can leave temporary copies. A system administrator could still have access to local files. The HTML report contains filenames, input hashes, settings, warnings, example model events and possibly observed values. Treat it as sensitive and review it before sharing. Its HTML escapes imported text, but the report is not a security certification. No internet request is needed to generate or view it.

The Python model uses precomputed inputs and floating-point arithmetic. The report uses the same model as the trace and preflight; it is not an independent validation. Pine v0.3 remains uncompiled/replay- and alert-untested in the current account context, and no returns, execution, risk limits or prop-firm compliance have been demonstrated.
