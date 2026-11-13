"""Independent executable specification, not a broker/backtesting engine.
ATR and prior rolling levels are supplied by caller. Pine is the chart runtime.
Python >=3.10; standard library only. See tests for synthetic examples.
"""
from dataclasses import dataclass, field
from math import floor, isfinite
from decimal import Decimal

@dataclass(frozen=True)
class Bar:
    index: int
    day: str
    open: float
    high: float
    low: float
    close: float
    in_session: bool = True
    confirmed: bool = True

@dataclass(frozen=True)
class Config:
    body_mult: float = .8
    edge: float = .25
    stop_buffer: float = .1
    min_risk: float = .25
    max_risk: float = 3.
    expiry: int = 10
    cooldown: int = 5
    cap: int = 3
    targets: tuple = (.6, 1., 1.5, 2.)
    tick: float = .01
    use_ema: bool = False
    use_volume: bool = False
    use_vwap: bool = False
    vol_mult: float = 1.0
    min_break_atr: float = 0.0
    confirm_retest: bool = False
    longs: bool = True
    shorts: bool = True
    def __post_init__(self):
        # Explicit validation remains active under python -O; the CLI applies
        # the same checks after parsing its JSON overrides.
        floats = ('body_mult','edge','stop_buffer','min_risk','max_risk','tick','vol_mult','min_break_atr')
        for name in floats:
            value = getattr(self, name)
            if type(value) not in (int, float) or not isfinite(value):
                raise ValueError(f'{name} must be a finite number')
        for name in ('expiry','cooldown','cap'):
            if type(getattr(self, name)) is not int:
                raise ValueError(f'{name} must be an integer')
        for name in ('use_ema','use_volume','use_vwap','confirm_retest','longs','shorts'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f'{name} must be boolean')
        if not (0 < self.edge < .5 and self.tick > 0 and self.body_mult > 0 and self.vol_mult > 0):
            raise ValueError('invalid edge, tick, body or volume constraint')
        # The reference rounds to ten decimal places. Refuse ticks it cannot
        # faithfully represent rather than silently collapsing prices.
        if Decimal(str(self.tick)).normalize().as_tuple().exponent < -10:
            raise ValueError('tick must be representable at 10 decimal places or fewer')
        if not (0 < self.min_risk <= self.max_risk and self.stop_buffer >= 0 and self.min_break_atr >= 0):
            raise ValueError('invalid risk or breakout constraint')
        if not (self.expiry >= 1 and self.cooldown >= 0 and self.cap >= 1):
            raise ValueError('invalid expiry, cooldown or cap')
        if not isinstance(self.targets, (tuple, list)) or len(self.targets) != 4:
            raise ValueError('targets must contain four increasing finite numbers')
        if any(type(x) not in (int, float) or not isfinite(x) for x in self.targets) or not (0 < self.targets[0]) or not all(a < b for a, b in zip(self.targets, self.targets[1:])):
            raise ValueError('targets must contain four increasing finite numbers')

@dataclass(frozen=True)
class Setup:
    direction: int
    entry: float
    stop: float
    targets: tuple

def rounded(x, tick):
    # Nearest tick, ties toward positive infinity, matching intended Pine rule.
    return round(floor(x / tick + .5 + 1e-10) * tick, 10)

def detect(bar, prior_high, prior_low, prior_atr, cfg, ema=None, volume=None, prior_volume_avg=None, vwap=None):
    """Caller must supply fully warmed-up PREVIOUS-bar ATR and prior range."""
    if not bar.confirmed or prior_atr <= 0 or bar.high <= bar.low:
        return None
    if cfg.use_volume and (volume is None or prior_volume_avg is None or prior_volume_avg <= 0 or volume < cfg.vol_mult * prior_volume_avg):
        return None
    span = bar.high - bar.low
    body = abs(bar.close - bar.open)
    bull = (cfg.longs and (not cfg.use_vwap or (vwap is not None and bar.close > vwap)) and (not cfg.use_ema or (ema is not None and bar.close > ema)) and bar.close > prior_high and bar.close - prior_high >= cfg.min_break_atr * prior_atr and bar.close > bar.open
            and body >= cfg.body_mult * prior_atr
            and (bar.high - bar.close) / span <= cfg.edge)
    bear = (cfg.shorts and (not cfg.use_vwap or (vwap is not None and bar.close < vwap)) and (not cfg.use_ema or (ema is not None and bar.close < ema)) and bar.close < prior_low and prior_low - bar.close >= cfg.min_break_atr * prior_atr and bar.close < bar.open
            and body >= cfg.body_mult * prior_atr
            and (bar.close - bar.low) / span <= cfg.edge)
    if not (bull or bear):
        return None
    d = 1 if bull else -1
    e = rounded(prior_high if bull else prior_low, cfg.tick)
    s = rounded(bar.low - cfg.stop_buffer * prior_atr if bull else
                bar.high + cfg.stop_buffer * prior_atr, cfg.tick)
    risk = d * (e - s)
    if not (cfg.min_risk * prior_atr <= risk <= cfg.max_risk * prior_atr
            and risk >= cfg.tick):
        return None
    targets = tuple(rounded(e + d * risk * r, cfg.tick) for r in cfg.targets)
    sequence = (e,) + targets
    if not all(d * (b - a) > 0 for a, b in zip(sequence, sequence[1:])):
        return None
    return Setup(d, e, s, targets)

@dataclass
class Engine:
    cfg: Config = field(default_factory=Config)
    state: str = 'idle'
    setup: Setup | None = None
    armed_bar: int | None = None
    last_end: int | None = None
    day: str | None = None
    fills_today: int = 0
    hit: set = field(default_factory=set)
    last_cancel_reason: str | None = None

    def step(self, b: Bar, candidate: Setup | None = None):
        if not b.confirmed:
            return []
        if not b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high:
            raise ValueError('invalid OHLC')
        events = []
        filled_this_bar = False
        new_day = self.day is not None and b.day != self.day
        if self.day is None or new_day:
            self.fills_today = 0
            self.day = b.day
        idle_at_start = self.state == 'idle'
        if self.state == 'armed':
            s = self.setup
            invalid = b.low <= s.stop if s.direction == 1 else b.high >= s.stop
            if new_day or not b.in_session or b.index - self.armed_bar > self.cfg.expiry or invalid:
                self.last_cancel_reason = ('day_rollover' if new_day else 'outside_session' if not b.in_session else 'expired' if b.index - self.armed_bar > self.cfg.expiry else 'stop_before_fill')
                self.state, self.last_end = 'idle', b.index
                events.append('cancelled')
            elif b.index > self.armed_bar and b.low <= s.entry <= b.high and (not self.cfg.confirm_retest or (b.close >= s.entry if s.direction == 1 else b.close <= s.entry)):
                self.state = 'active'
                self.fills_today += 1
                events.append('modeled_fill')
                filled_this_bar = True
        if self.state == 'active':
            s = self.setup
            stop = b.low <= s.stop if s.direction == 1 else b.high >= s.stop
            if stop:
                self.state, self.last_end = 'idle', b.index
                events.append('stop')
            elif not filled_this_bar:
                for i, target in enumerate(s.targets, 1):
                    touched = b.high >= target if s.direction == 1 else b.low <= target
                    if touched and i not in self.hit:
                        self.hit.add(i)
                        events.append(f'target_{i}')
                if 4 in self.hit:
                    self.state, self.last_end = 'idle', b.index
        cooled = self.last_end is None or b.index - self.last_end > self.cfg.cooldown
        if idle_at_start and self.state == 'idle' and b.in_session and self.fills_today < self.cfg.cap and cooled and candidate:
            self.state, self.setup, self.armed_bar = 'armed', candidate, b.index
            self.hit.clear()
            events.append('armed_long' if candidate.direction == 1 else 'armed_short')
        return events

# Command-line diagnostic trace. It uses this same reference model; it is not
# an independent Pine parity test or an order/execution simulator.
def _optional_float(raw, field, row_number):
    from math import isfinite
    if raw is None or not str(raw).strip():
        return None
    try:
        n = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'row {row_number}: {field} must be a number') from exc
    if not isfinite(n):
        raise ValueError(f'row {row_number}: {field} must be finite')
    return n

def _boolean(raw, field, row_number, default=True):
    if raw is None or not str(raw).strip():
        return default
    value = str(raw).strip().lower()
    if value in ('true', '1'): return True
    if value in ('false', '0'): return False
    raise ValueError(f'row {row_number}: {field} must be true/false or 1/0')

def load_config(path=None):
    import json
    from dataclasses import fields
    from math import isfinite
    if path is None: return Config()
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError(f'duplicate config key: {key}')
            result[key] = value
        return result
    with open(path, encoding='utf-8') as f: data = json.load(f, object_pairs_hook=unique_object)
    if not isinstance(data, dict): raise ValueError('config must be a JSON object')
    unknown = set(data) - {f.name for f in fields(Config)}
    if unknown: raise ValueError('unknown config keys: ' + ', '.join(sorted(unknown)))
    base = Config()
    for key, value in data.items():
        default = getattr(base, key)
        if isinstance(default, bool):
            if type(value) is not bool: raise ValueError(f'config {key} must be boolean')
        elif isinstance(default, int):
            if type(value) is not int: raise ValueError(f'config {key} must be an integer')
        elif isinstance(default, float):
            if type(value) not in (int, float) or not isfinite(value): raise ValueError(f'config {key} must be a finite number')
        elif key == 'targets':
            if not isinstance(value, list) or len(value) != 4 or any(type(x) not in (int, float) or not isfinite(x) for x in value):
                raise ValueError('config targets must be four finite numbers')
            data[key] = tuple(value)
    try: return Config(**data)
    except (AssertionError, TypeError, ValueError) as exc: raise ValueError('invalid config constraints') from exc

def trace_rows(rows, cfg=None):
    """Trace chronological confirmed bars supplied with prepared values.

    Starts idle. `day` must be the same local calendar day used by Pine. Prior
    high/low/ATR may all be blank during warm-up. This doesn't compute them.
    """
    from datetime import date, datetime
    engine = Engine(cfg or Config())
    previous_index = previous_day = None
    output = []
    for i, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f'row {i}: malformed CSV row (wrong number of fields)')
        raw_index = (row.get('index') or '').strip()
        if not raw_index.isdigit(): raise ValueError(f'row {i}: index must be a nonnegative integer')
        index = int(raw_index)
        if previous_index is not None and index != previous_index + 1:
            raise ValueError(f'row {i}: indexes must be consecutive and increasing')
        raw_day = (row.get('day') or '').strip()
        try:
            day = date.fromisoformat(raw_day)
            if day.isoformat() != raw_day: raise ValueError()
        except ValueError as exc: raise ValueError(f'row {i}: day must be YYYY-MM-DD') from exc
        if previous_day is not None and day < previous_day: raise ValueError(f'row {i}: days must be nondecreasing')
        timestamp = (row.get('timestamp') or '').strip()
        if timestamp:
            try: datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError as exc: raise ValueError(f'row {i}: timestamp must be ISO 8601') from exc
        numbers = {name: _optional_float(row.get(name), name, i) for name in ('open','high','low','close','prior_high','prior_low','prior_atr','ema','volume','prior_volume_avg','vwap')}
        if any(numbers[k] is None for k in ('open','high','low','close')): raise ValueError(f'row {i}: OHLC is required')
        o,h,l,c = (numbers[k] for k in ('open','high','low','close'))
        if not l <= min(o,c) <= max(o,c) <= h: raise ValueError(f'row {i}: invalid OHLC')
        prepared = [numbers[k] for k in ('prior_high','prior_low','prior_atr')]
        if any(v is not None for v in prepared) and any(v is None for v in prepared): raise ValueError(f'row {i}: prior high, low and ATR must all be present or all blank')
        if all(v is not None for v in prepared) and (prepared[0] < prepared[1] or prepared[2] < 0): raise ValueError(f'row {i}: invalid prior range or ATR')
        if numbers['volume'] is not None and numbers['volume'] < 0: raise ValueError(f'row {i}: volume cannot be negative')
        if numbers['prior_volume_avg'] is not None and numbers['prior_volume_avg'] < 0: raise ValueError(f'row {i}: prior volume average cannot be negative')
        if not _boolean(row.get('confirmed'), 'confirmed', i): raise ValueError(f'row {i}: trace accepts confirmed bars only')
        bar = Bar(index, raw_day, o,h,l,c, _boolean(row.get('in_session'),'in_session',i))
        candidate = None if prepared[0] is None else detect(bar, *prepared, engine.cfg, ema=numbers['ema'], volume=numbers['volume'], prior_volume_avg=numbers['prior_volume_avg'], vwap=numbers['vwap'])
        before = engine.state
        events = engine.step(bar, candidate)
        setup = engine.setup if before != 'idle' or engine.state != 'idle' else None
        output.append({'index':index,'timestamp':timestamp,'day':raw_day,'state_before':before,'state':engine.state,'events':'|'.join(events),'cancel_reason':engine.last_cancel_reason if 'cancelled' in events else '', 'direction':setup.direction if setup else '', 'entry':setup.entry if setup else '', 'stop':setup.stop if setup else '', **{f't{j}': setup.targets[j-1] if setup else '' for j in range(1,5)}, 'fills_today':engine.fills_today,'targets_hit':'|'.join(map(str,sorted(engine.hit))) if setup else ''})
        previous_index, previous_day = index, day
    return output

def main(argv=None):
    import argparse, csv, json, sys
    from pathlib import Path
    parser=argparse.ArgumentParser(description='Trace prepared closed bars with the Retest Lab Python model; not a backtest or Pine validation.')
    parser.add_argument('input', help='input CSV with OHLC and prepared indicators')
    parser.add_argument('--config', help='optional JSON overrides for Python Config')
    parser.add_argument('--output', help='new output CSV (default stdout); existing files require --force')
    parser.add_argument('--force', action='store_true', help='replace an existing regular output file, never input/config')
    args=parser.parse_args(argv)
    try:
        if args.force and not args.output: raise ValueError('--force requires --output')
        if args.output:
            output = Path(args.output)
            if output.is_symlink(): raise ValueError('output must not be a symlink')
            for label, source in (('input', args.input), ('config', args.config)):
                if source is None: continue
                source_path = Path(source)
                if output.resolve() == source_path.resolve() or (output.exists() and source_path.exists() and output.samefile(source_path)):
                    raise ValueError(f'output must not overwrite {label}')
            if output.exists() and not args.force: raise ValueError('output already exists; choose a new file or use --force')
            if output.exists() and not output.is_file(): raise ValueError('output must be a regular file')
        cfg=load_config(args.config)
        with open(args.input, newline='', encoding='utf-8-sig') as f:
            reader=csv.DictReader(f, strict=True)
            required={'index','day','open','high','low','close','prior_high','prior_low','prior_atr'}
            if not reader.fieldnames or not required.issubset(reader.fieldnames): raise ValueError('CSV missing required columns: '+', '.join(sorted(required-set(reader.fieldnames or []))))
            if len(reader.fieldnames) != len(set(reader.fieldnames)): raise ValueError('duplicate CSV headers')
            result=trace_rows(reader,cfg)
        if not result: raise ValueError('CSV has no bars')
        fields=list(result[0])
        if args.output:
            # Write beside the destination, then atomically link a new file or
            # replace only when explicitly requested. The link step fails if a
            # file appeared concurrently; it never clobbers that file.
            import os, tempfile
            fd, temp_name = tempfile.mkstemp(prefix='.retest-trace-', suffix='.tmp', dir=output.parent)
            try:
                with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
                    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(result)
                if output.is_symlink(): raise ValueError('output must not be a symlink')
                if args.force:
                    if output.exists() and not output.is_file(): raise ValueError('output must be a regular file')
                    os.replace(temp_name, output)
                else:
                    os.link(temp_name, output)
            finally:
                if os.path.exists(temp_name): os.unlink(temp_name)
        else:
            writer=csv.DictWriter(sys.stdout,fieldnames=fields);writer.writeheader();writer.writerows(result)
        return 0
    except (OSError,ValueError,TypeError,UnicodeError,OverflowError,csv.Error,json.JSONDecodeError) as exc:
        print('Trace error: '+str(exc),file=sys.stderr);return 2

if __name__ == '__main__':
    raise SystemExit(main())
