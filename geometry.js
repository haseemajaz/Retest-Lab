/* Retest Lab geometry calculator. Independent educational tool; no orders. */
(function (root) {
  'use strict';
  const SCALE = 100000000n;
  const MAX_PRICE = 1000000000n * SCALE;
  const MAX_R = 1000n * SCALE;
  function parse(value, label) {
    const text = String(value == null ? '' : value).trim();
    if (!/^\d{1,10}(?:\.\d{1,8})?$/.test(text)) throw new Error(`${label}: enter a non-negative decimal with up to 8 decimal places (no exponent).`);
    const [whole, fraction = ''] = text.split('.');
    return { value: BigInt(whole) * SCALE + BigInt((fraction + '00000000').slice(0, 8)), digits: fraction.length };
  }
  function format(value, digits) {
    const whole = value / SCALE;
    if (!digits) return whole.toString();
    return whole + '.' + (value % SCALE).toString().padStart(8, '0').slice(0, digits);
  }
  function calculate(input) {
    if (!input || !['long', 'short'].includes(input.direction)) throw new Error('Choose long or short.');
    const entry = parse(input.entry, 'Entry').value;
    const stop = parse(input.stop, 'Stop').value;
    const tickData = parse(input.tick, 'Tick size');
    const tick = tickData.value;
    if (entry > MAX_PRICE || stop > MAX_PRICE) throw new Error('Entry and stop must not exceed 1,000,000,000.');
    if (tick <= 0n || tick > MAX_PRICE) throw new Error('Tick size must be greater than zero and not exceed 1,000,000,000.');
    if (entry % tick !== 0n || stop % tick !== 0n) throw new Error('Entry and stop must be exact multiples of tick size.');
    const long = input.direction === 'long';
    if ((long && stop >= entry) || (!long && stop <= entry)) throw new Error(long ? 'For a long example, stop must be below entry.' : 'For a short example, stop must be above entry.');
    if (!Array.isArray(input.rs) || input.rs.length !== 4) throw new Error('Enter four R multiples.');
    const rs = input.rs.map((r, i) => parse(r, `Target ${i + 1} R`).value);
    if (rs.some(r => r <= 0n || r > MAX_R) || rs.some((r, i) => i > 0 && r <= rs[i-1])) throw new Error('R multiples must be positive, increasing and at most 1000.');
    const entryTicks = entry / tick;
    const riskTicks = long ? (entry - stop) / tick : (stop - entry) / tick;
    const targets = rs.map(r => {
      // Rounding target PRICE to nearest tick, ties toward the greater price.
      const numerator = riskTicks * r;
      const roundedDistance = long ? (numerator + SCALE / 2n) / SCALE : (numerator + SCALE / 2n - 1n) / SCALE;
      return (long ? entryTicks + roundedDistance : entryTicks - roundedDistance) * tick;
    });
    if (targets.some(t => t < 0n || t > MAX_PRICE)) throw new Error('A target is outside the supported non-negative price range.');
    let previous = entry;
    for (const t of targets) {
      if ((long && t <= previous) || (!long && t >= previous)) throw new Error('Tick rounding makes targets collapse or move to the wrong side. Change the inputs.');
      previous = t;
    }
    const digits = tickData.digits;
    return {
      direction: input.direction,
      entry: format(entry, digits), stop: format(stop, digits), tick: format(tick, digits),
      risk: format(riskTicks * tick, digits), riskTicks: riskTicks.toString(),
      rs: rs.map(r => format(r, 8).replace(/\.?0+$/, '')),
      targets: targets.map(t => format(t, digits))
    };
  }
  const api = { calculate };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.RetestGeometry = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
