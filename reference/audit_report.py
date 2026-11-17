"""Create an offline audit report from snapshot inputs, not a backtest.

The trace and preflight use the same Python model; comparison uses only user-
recorded cells. The report is neither a Pine-parity proof nor a trade record.
"""
import argparse
import csv
from dataclasses import asdict
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import sys
import tempfile

from reference.engine import load_config, trace_rows
from reference.ledger import REQUIRED as LEDGER_REQUIRED, build_setups, summarize as summarize_setups
from reference.preflight import inspect
from reference.compare_trace import compare_detailed, read_requirements

MAX_INPUT = 8 * 1024 * 1024
MAX_DETAILS = 50
MAX_CELL_DISPLAY = 250


def snapshot(path):
    # Bound memory use, then hash exactly the bytes supplied to every check.
    with open(path, 'rb') as f:
        data = f.read(MAX_INPUT + 1)
    if len(data) > MAX_INPUT:
        raise ValueError(f'{Path(path).name}: input exceeds 8 MiB')
    return data


def parse_bundle(data):
    """Decode the array-only capture bundle; callers validate CSV content separately."""
    try:
        bundle = json.loads(data.decode('utf-8-sig'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-standard JSON constant')))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError('invalid evidence bundle JSON') from exc
    if (not isinstance(bundle, list) or len(bundle) != 4 or bundle[0] != 'retest-evidence'
            or type(bundle[1]) is not int or bundle[1] != 1
            or not isinstance(bundle[2], str) or not isinstance(bundle[3], str)):
        raise ValueError('unsupported or malformed evidence bundle')
    try:
        return bundle[2].encode('utf-8'), bundle[3].encode('utf-8')
    except UnicodeError as exc:
        raise ValueError('evidence bundle contains invalid Unicode') from exc


def e(value):
    text = str(value)
    if len(text) > MAX_CELL_DISPLAY:
        text = text[:MAX_CELL_DISPLAY] + '… [truncated]'
    return escape(text, quote=True)


def render_report(result):
    bars = result['bars']
    warnings = result['warnings']
    comparison = result['comparison']
    checklist = result['checklist']
    findings = []
    for message, indexes in warnings:
        shown = ', '.join(str(i) for i in indexes[:10])
        more = ', …' if len(indexes) > 10 else ''
        findings.append(f'<li><strong>{e(message)}</strong><br><span>{len(indexes)} affected bars · indexes {e(shown + more)}</span></li>')
    if not findings:
        findings.append('<li>No preflight warnings reported. This does not establish data accuracy or model correctness.</li>')
    warning_html = ''.join(findings)
    cadence_note = (f'<p class="cadence"><strong>Advisory cadence: {result["expected_seconds"]} seconds.</strong> Only adjacent offset-aware timestamps are assessed. Market closures and session breaks may be normal; no exchange schedule is checked.</p>' if result.get('expected_seconds') is not None else '<p class="small">Cadence check: not requested.</p>')
    bundle_note = ('<p class="small"><strong>Evidence bundle:</strong> the audit checked that recorded cells are included in its checklist. The bundle cannot establish source, truth or completeness.</p>' if result.get('bundle') else '')
    if comparison is None:
        compare_card = '<p class="banner neutral"><strong>Not run.</strong> No observation file was supplied. Unobserved cells are not passes.</p>'
        diff_html = ''
    else:
        count, differences, indexes, seen = comparison
        missing = result['missing']
        compare_card = (f'<div class="metrics"><div><b>{count}</b><span>recorded cells</span></div>'
                        f'<div><b>{len(differences)}</b><span>differences</span></div>'
                        f'<div><b>{len(missing) if checklist else "—"}</b><span>missing planned cells</span></div></div>'
                        f'<p>Observations cover {len({i for i, _ in seen})} of {len(indexes)} trace bars. '
                        'Presence does not prove accuracy or completeness. A blank observed value is a recorded blank, not an absent observation.</p>')
        if checklist:
            compare_card += f'<p>Checklist: {len(checklist)-len(missing)} of {len(checklist)} planned cells recorded. The plan itself may be incomplete.</p>'
        else:
            compare_card += '<p>No checklist supplied; planned coverage was not assessed.</p>'
        details = []
        for index, field, expected, observed in differences[:MAX_DETAILS]:
            details.append(f'<li><b>Bar {e(index)} · {e(field)}</b><br>Reference: <code>{e(expected) or "(blank)"}</code><br>Observed: <code>{e(observed) or "(blank)"}</code></li>')
        for index, field in missing[:MAX_DETAILS]:
            details.append(f'<li><b>Missing planned observation</b> · bar {e(index)}, {e(field)}</li>')
        if not details: details.append('<li>No differences or missing planned cells were reported for the supplied observations. This is not proof of parity.</li>')
        diff_html = '<h3>Comparison details</h3><ul class="items">' + ''.join(details) + '</ul>'
        if len(differences) > MAX_DETAILS or len(missing) > MAX_DETAILS:
            diff_html += '<p class="small">Details limited to the first 50 differences and first 50 missing cells. Use the comparator CLI for the full list.</p>'
    fingerprints = ''.join(f'<tr><th scope="row">{e(label)}</th><td>{e(info["name"])}</td><td><code>{info["hash"]}</code></td></tr>' for label,info in result['sources'].items())
    event_rows = [r for r in bars if r['events']]
    ambiguous_rows = [r for r in bars if str(r.get('order_ambiguity') or '').strip()]
    trace_preview = ''.join(f'<tr><td>{e(r["index"])}</td><td>{e(r["timestamp"]) or "—"}</td><td>{e(r["state_before"])} → {e(r["state"])}</td><td>{e(r["events"])}</td><td>{e(r["cancel_reason"]) or "—"}</td><td>{e(r.get("order_ambiguity") or "") or "—"}</td><td>{e(r.get("reject_reason") or "") or "—"}</td></tr>' for r in event_rows[:25])
    if not trace_preview: trace_preview = '<tr><td colspan="7">No event rows in this trace.</td></tr>'
    ambiguity_note = f'<p class="small">{len(ambiguous_rows)} of {len(bars)} bar(s) have intrabar order ambiguity (OHLC spans several levels whose order is unknown). A flagged outcome is a modelling convention, not an observed sequence. See ORDER_AMBIGUITY.html.</p>'
    from collections import Counter as _Counter
    _labels = _Counter()
    for _r in ambiguous_rows:
        for _lab in str(_r.get('order_ambiguity') or '').split('|'):
            if _lab.strip():
                _labels[_lab.strip()] += 1
    _amb_fills = sum(1 for _r in ambiguous_rows if 'modeled_fill' in str(_r.get('events') or ''))
    _amb_stops = sum(1 for _r in ambiguous_rows if 'stop' in str(_r.get('events') or '').split('|'))
    _clean_events = len(event_rows) - len([_r for _r in event_rows if str(_r.get('order_ambiguity') or '').strip()])
    _label_rows = ''.join(f'<li><b>{e(_lab)}</b> — {_n} bar(s)</li>' for _lab, _n in sorted(_labels.items())) or '<li>No ambiguity labels recorded.</li>'
    _rejects = _Counter(str(_r.get('reject_reason') or '').strip() for _r in bars if str(_r.get('reject_reason') or '').strip())
    _reject_rows = ''.join(f'<li><b>{e(_lab)}</b> — {_n} bar(s)</li>' for _lab, _n in sorted(_rejects.items())) or '<li>No rejection reason recorded.</li>'
    _rejected_total = sum(_rejects.values())
    _top_reject = sorted(_rejects.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if _rejects else ''
    _reject_line = (f'<p>Rejected while idle: {_rejected_total} bar(s)' + (f', most common reason: {_top_reject}.' if _top_reject else '.') + ' A reason is recorded only on bars that started idle; bars already armed or active carry none.</p>')
    ambiguity_summary = (
        f'<div class="metrics"><div><b>{len(ambiguous_rows)}</b><span>ambiguous bars</span></div>'
        f'<div><b>{_amb_fills}</b><span>ambiguous modeled fills</span></div>'
        f'<div><b>{_amb_stops}</b><span>ambiguous stops</span></div></div>'
        f'<p>Event-bearing bars: {len(event_rows)} total, {_clean_events} clean and {len(ambiguous_rows)} flagged. '
        'Flagged bars are excluded from any win/loss-like count in this report — this report calculates no win rate, and a flagged outcome must not be counted as a win or a loss without finer data.</p>'
        f'{_reject_line}'
        f'<h3>Ambiguity labels</h3><ul class="items">{_label_rows}</ul>'
        f'<h3>Rejection reasons</h3><p class="small">Why bars with a prepared candidate did not arm a setup (first failing check; see REJECT_GUIDE.html). Warmup bars have no prepared prior values.</p><ul class="items">{_reject_rows}</ul>')
    _ledger_available = bool(bars) and LEDGER_REQUIRED.issubset(bars[0])
    _setups = build_setups(bars) if _ledger_available else []
    _setup_summary = summarize_setups(_setups)
    if _setups:
        _setup_rows = ''.join(f'<tr><th scope="row">{e(s["setup"])}</th><td>{e(s["day"])}</td><td>{e(s["direction"])}</td><td>{e(s["armed_index"])}</td><td>{e(s["end_index"]) or "—"}</td><td>{e(s["bars_held"])}</td><td>{e(s["fill_index"]) or "—"}</td><td>{e(s["targets_hit"]) or "—"}</td><td>{e(s["outcome"])}{(" / " + e(s["cancel_reason"])) if s["cancel_reason"] else ""}</td><td>{e(s["ambiguous_bars"])}</td></tr>' for s in _setups)
        _setup_table = f'<div class="scroll" tabindex="0" role="region" aria-label="Setup outcomes, scroll horizontally"><table><thead><tr><th scope="col">Setup</th><th scope="col">Day</th><th scope="col">Direction</th><th scope="col">Armed</th><th scope="col">Ended</th><th scope="col">Bars held</th><th scope="col">Fill</th><th scope="col">Targets hit</th><th scope="col">Outcome</th><th scope="col">Ambiguous bars</th></tr></thead><tbody>{_setup_rows}</tbody></table></div>'
    else:
        _setup_table = '<p>No setups were armed in this trace.</p>' if _ledger_available else '<p>Setup outcomes are unavailable for this trace.</p>'
    setup_html = (
        f'<div class="metrics"><div><b>{_setup_summary["total"]}</b><span>setups</span></div>'
        f'<div><b>{_setup_summary["filled"]}</b><span>modeled fills</span></div>'
        f'<div><b>{_setup_summary["all_targets"]}</b><span>reached all targets</span></div></div>'
        f'<p>{_setup_summary["all_targets"]} reached all targets, {_setup_summary["stop"]} stopped, '
        f'{_setup_summary["cancelled"]} cancelled, {_setup_summary["open"]} still open. '
        f'{_setup_summary["ambiguous_bars"]} ambiguous bar(s) fall inside these setups; a flagged outcome is a modelling convention, not an observed sequence, and must not be counted as a win or a loss. See SETUP_LEDGER.md.</p>'
        f'{_setup_table}')
    # Configuration JSON is known model data but can exceed the generic per-cell
    # display limit, so escape it in full (rather than truncating the text).
    config = escape(json.dumps(result['config'], indent=2, sort_keys=True))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>Replay audit report | Retest Lab</title><style>
:root{{color-scheme:light dark;--bg:#f3f6f4;--paper:#fff;--text:#19302e;--muted:#526763;--line:#cfddd6;--accent:#155c53;--soft:#e8f3ed;--warn:#fff4e7;--wt:#704516}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,sans-serif}}.wrap{{max-width:1100px;margin:auto;padding:0 32px}}header{{border-bottom:1px solid var(--line);background:var(--paper)}}nav{{min-height:72px;display:flex;align-items:center;gap:12px;font-weight:750}}.mark{{display:grid;place-items:center;width:36px;height:36px;border-radius:8px;background:var(--accent);color:var(--paper);font-size:13px}}.hero{{padding:48px 0 32px}}.eyebrow{{font-size:13px;font-weight:750;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin:0 0 10px}}h1{{font-size:clamp(2.2rem,5vw,3.3rem);line-height:1.1;letter-spacing:-.04em;margin:0 0 16px}}h2{{font-size:1.5rem;line-height:1.2;margin:0 0 12px}}h3{{font-size:1.1rem;margin:24px 0 12px}}p{{margin:0 0 14px}}.lead{{font-size:1.1rem;color:var(--muted);max-width:750px}}.banner{{padding:18px 20px;border-radius:10px;background:var(--warn);color:var(--wt);border:1px solid #e8cda8}}.banner p{{margin:4px 0 0}}.cadence{{padding:16px 18px;background:var(--soft);border:1px solid var(--line);border-radius:8px;margin:16px 0 0}}.neutral{{background:var(--soft);border-color:var(--line);color:var(--text)}}.section{{padding:32px 0;border-bottom:1px solid var(--line)}}.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:20px 0}}.metrics div{{padding:18px;background:var(--soft);border-radius:8px}}.metrics b{{display:block;font-size:1.75rem;line-height:1.1}}.metrics span{{display:block;margin-top:6px;font-size:14px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:24px}}.items{{margin:0;padding-left:22px}}.items li+li{{margin-top:14px}}.items span,.small{{color:var(--muted);font-size:14px}}.scroll{{overflow:auto;border:1px solid var(--line);border-radius:8px}}table{{border-collapse:collapse;width:100%;min-width:720px}}th,td{{padding:12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top;font-size:14px;overflow-wrap:anywhere}}thead th{{background:var(--soft);white-space:nowrap}}th[scope=row]{{white-space:nowrap}}tr:last-child td,tr:last-child th{{border-bottom:0}}code,pre{{font-family:ui-monospace,Consolas,monospace;font-size:14px;overflow-wrap:anywhere}}pre{{background:var(--soft);padding:16px;border-radius:8px;white-space:pre-wrap}}footer{{padding:24px 0 36px;color:var(--muted);font-size:14px}}@media(max-width:760px){{.wrap{{padding:0 20px}}.hero{{padding:36px 0 28px}}.section{{padding:26px 0}}.panel{{padding:20px}}.metrics{{grid-template-columns:1fr}}}}@media(prefers-color-scheme:dark){{:root{{--bg:#191f1d;--paper:#222b28;--text:#eef7f1;--muted:#bdcdc5;--line:#465951;--accent:#a2dfc7;--soft:#29463c;--warn:#3d3121;--wt:#ffe3ba}}.banner{{border-color:#806643}}.mark{{color:#142c24}}}}
</style></head><body><header><nav class="wrap"><span class="mark" aria-hidden="true">RL</span> Retest Lab · offline audit</nav></header><main class="wrap"><section class="hero"><p class="eyebrow">Research workspace / v0.25.0</p><h1>Evidence, in context.</h1><p class="lead">A snapshot of prepared inputs, model warnings and any manually recorded comparisons. This report was generated locally.</p></section><aside class="banner"><strong>Not a trading result or Pine validation.</strong><p>The reference trace and preflight share one model. Observations are user supplied; the report does not verify their source, establish execution or calculate returns.</p></aside><section class="section"><p class="eyebrow">01 / Overview</p><h2>What was checked</h2><div class="metrics"><div><b>{len(bars)}</b><span>modeled bars</span></div><div><b>{len(warnings)}</b><span>warning categories</span></div><div><b>{"Run" if comparison is not None else "Not run"}</b><span>observation comparison</span></div></div><p class="small">Warnings may be expected; a clear report is not proof of correct data or trading performance. Tick-grid check: {"enabled" if result["check_tick"] else "not requested"}. Strict mode: {"enabled" if result["strict"] else "not requested"}.</p>{cadence_note}</section><section class="section"><p class="eyebrow">02 / Input review</p><h2>Preflight warnings</h2><div class="panel"><ul class="items">{warning_html}</ul><p class="small">Up to 10 example indexes per category. Inspect the input and run the preflight CLI for full context. Inputs and configuration are not corrected.</p></div></section><section class="section"><p class="eyebrow">03 / Comparison</p><h2>Recorded observations</h2><div class="panel">{compare_card}{bundle_note}{diff_html}</div></section><section class="section"><p class="eyebrow">03b / Ambiguity &amp; rejection</p><h2>Flagged bars, counted separately</h2><div class="panel">{ambiguity_summary}</div></section><section class="section"><p class="eyebrow">04 / Modeled timeline</p><h2>Events from the reference trace</h2><p class="small">First {min(25,len(event_rows))} of {len(event_rows)} event-bearing bars. Threshold events are not confirmed broker fills. Scroll horizontally when needed.</p>{ambiguity_note}<div class="scroll" tabindex="0" role="region" aria-label="Modeled events, scroll horizontally"><table><thead><tr><th scope="col">Index</th><th scope="col">Timestamp</th><th scope="col">State before → after</th><th scope="col">Events</th><th scope="col">Cancel reason</th><th scope="col">Order ambiguity</th><th scope="col">Reject reason</th></tr></thead><tbody>{trace_preview}</tbody></table></div></section><section class="section"><p class="eyebrow">04b / Setup outcomes</p><h2>What happened to each setup</h2><p class="small">One row per armed setup, from the setup ledger. A setup that never filled is still a setup; an open setup has no end yet. No win rate is calculated here.</p><div class="panel">{setup_html}</div></section><section class="section"><p class="eyebrow">05 / Provenance</p><h2>Input fingerprints</h2><p class="small">SHA-256 hashes identify the exact bytes read for this report. Inputs are read sequentially, not simultaneously. Hashes do not authenticate the source or fingerprint the executed code; record the software ZIP hash separately. Filenames and recorded values may be sensitive; review before sharing. No input files were modified.</p><div class="scroll" tabindex="0" role="region" aria-label="Input fingerprints, scroll horizontally"><table><thead><tr><th scope="col">Input</th><th scope="col">Filename</th><th scope="col">SHA-256</th></tr></thead><tbody>{fingerprints}</tbody></table></div><h3>Effective reference configuration</h3><pre>{config}</pre><p class="small">Defaults were used for any omitted configuration fields. This captures the Python reference settings, not chart or broker settings.</p></section></main><footer class="wrap">Retest Lab · independent research prototype · no broker connection</footer></body></html>'''


def build(args):
    bundle_path = getattr(args, 'bundle', None)
    expected_seconds = getattr(args, 'expected_seconds', None)
    if bundle_path and (args.required or args.observations):
        raise ValueError('--bundle cannot be combined with --observations or --required')
    if args.required and not args.observations:
        raise ValueError('--required needs --observations (an empty observations CSV is allowed)')
    paths = [('Bars', args.bars), ('Configuration', args.config), ('Observations', args.observations), ('Checklist', args.required), ('Evidence bundle', bundle_path)]
    copies, sources = {}, {}
    # Reading once avoids hash/check mismatches caused by later source edits.
    for label, path in paths:
        if path is not None:
            data = snapshot(path)
            copies[label] = data
            sources[label] = {'name':Path(path).name, 'hash':sha256(data).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='retest-audit-') as temp:
        directory = Path(temp)
        tmpfiles = {}
        for number,(label,data) in enumerate(copies.items()):
            p = directory / f'input{number}'; p.write_bytes(data); tmpfiles[label] = p
        if bundle_path:
            required_bytes, observed_bytes = parse_bundle(copies['Evidence bundle'])
            tmpfiles['Bundle checklist'] = directory / 'bundle-checklist.csv'
            tmpfiles['Bundle observations'] = directory / 'bundle-observations.csv'
            tmpfiles['Bundle checklist'].write_bytes(required_bytes)
            tmpfiles['Bundle observations'].write_bytes(observed_bytes)
        cfg = load_config(tmpfiles.get('Configuration'))
        _, warnings = inspect(tmpfiles['Bars'], tmpfiles.get('Configuration'), check_tick=args.check_tick, expected_seconds=expected_seconds)
        with tmpfiles['Bars'].open(newline='', encoding='utf-8-sig') as f:
            trace = trace_rows(csv.DictReader(f, strict=True), cfg)
        tracefile = directory / 'trace.csv'
        with tracefile.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(trace[0])); writer.writeheader(); writer.writerows(trace)
        comparison = None; checklist = set(); missing = []
        if args.observations or bundle_path:
            obsfile = tmpfiles['Bundle observations'] if bundle_path else tmpfiles['Observations']
            comparison = compare_detailed(tracefile, obsfile, allow_empty_observations=bool(args.required or bundle_path))
            if args.required or bundle_path:
                reqfile = tmpfiles['Bundle checklist'] if bundle_path else tmpfiles['Checklist']
                checklist = read_requirements(reqfile, comparison[2])
                if bundle_path and comparison[3] - checklist:
                    raise ValueError('evidence bundle contains observations not present in its checklist')
                missing = sorted(checklist - comparison[3])
        result = {'bars':trace,'warnings':warnings,'comparison':comparison,'checklist':checklist,'missing':missing,'config':asdict(cfg),'sources':sources,'check_tick':args.check_tick,'strict':args.strict,'bundle':bool(bundle_path),'expected_seconds':expected_seconds}
        report = render_report(result)
    # The destination is never overwritten, including symlinks and hard links.
    # Build in the destination directory, then atomically link a new filename.
    out = Path(args.output)
    fd, tempname = tempfile.mkstemp(prefix='.retest-audit-', suffix='.tmp', dir=out.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(report)
        os.link(tempname, out)
    finally:
        if os.path.exists(tempname): os.unlink(tempname)
    issues = bool(args.strict and warnings) or bool(comparison and comparison[1]) or bool(missing)
    return 1 if issues else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Build an offline replay audit report; does not validate Pine or performance.')
    parser.add_argument('--bars', required=True, help='prepared bar CSV')
    parser.add_argument('--output', required=True, help='new HTML file; never overwritten')
    parser.add_argument('--config', help='optional reference config JSON')
    parser.add_argument('--expected-seconds', type=int, help='optional expected adjacent-bar interval in seconds (1 to 31536000); advisory only')
    parser.add_argument('--bundle', help='single-snapshot evidence bundle JSON from capture worksheet; not with --observations or --required')
    parser.add_argument('--observations', help='optional manually recorded observations CSV')
    parser.add_argument('--required', help='optional planned-observation checklist; requires --observations')
    parser.add_argument('--check-tick', action='store_true', help='include advisory OHLC grid checks')
    parser.add_argument('--strict', action='store_true', help='return status 1 for preflight warnings')
    args = parser.parse_args(argv)
    try:
        code = build(args)
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError, csv.Error, json.JSONDecodeError) as exc:
        print('Audit error: '+str(exc), file=sys.stderr); return 2
    print(f'Report created: {args.output}. Exit {code}; no source or performance validation implied.')
    return code

if __name__ == '__main__':
    raise SystemExit(main())
