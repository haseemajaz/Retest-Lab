"""Independent executable specification, not a broker/backtesting engine.
ATR and prior rolling levels are supplied by caller. Pine is the chart runtime.
Python >=3.10; standard library only. See tests for synthetic examples.
"""
from dataclasses import dataclass, field
from math import floor

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
    vol_mult: float = 1.0
    longs: bool = True
    shorts: bool = True
    def __post_init__(self):
        assert 0 < self.edge < .5 and self.tick > 0 and self.body_mult > 0 and self.vol_mult > 0
        assert 0 < self.min_risk <= self.max_risk and self.stop_buffer >= 0
        assert self.expiry >= 1 and self.cooldown >= 0 and self.cap >= 1
        assert len(self.targets) == 4 and 0 < self.targets[0]
        assert all(a < b for a, b in zip(self.targets, self.targets[1:]))

@dataclass(frozen=True)
class Setup:
    direction: int
    entry: float
    stop: float
    targets: tuple

def rounded(x, tick):
    # Nearest tick, ties toward positive infinity, matching intended Pine rule.
    return round(floor(x / tick + .5 + 1e-10) * tick, 10)

def detect(bar, prior_high, prior_low, prior_atr, cfg, ema=None, volume=None, prior_volume_avg=None):
    """Caller must supply fully warmed-up PREVIOUS-bar ATR and prior range."""
    if not bar.confirmed or prior_atr <= 0 or bar.high <= bar.low:
        return None
    if cfg.use_volume and (volume is None or prior_volume_avg is None or prior_volume_avg <= 0 or volume < cfg.vol_mult * prior_volume_avg):
        return None
    span = bar.high - bar.low
    body = abs(bar.close - bar.open)
    bull = (cfg.longs and (not cfg.use_ema or (ema is not None and bar.close > ema)) and bar.close > prior_high and bar.close > bar.open
            and body >= cfg.body_mult * prior_atr
            and (bar.high - bar.close) / span <= cfg.edge)
    bear = (cfg.shorts and (not cfg.use_ema or (ema is not None and bar.close < ema)) and bar.close < prior_low and bar.close < bar.open
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

    def step(self, b: Bar, candidate: Setup | None = None):
        if not b.confirmed:
            return []
        assert b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high
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
                self.state, self.last_end = 'idle', b.index
                events.append('cancelled')
            elif b.index > self.armed_bar and b.low <= s.entry <= b.high:
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
