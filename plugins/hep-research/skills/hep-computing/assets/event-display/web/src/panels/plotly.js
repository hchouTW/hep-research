// Plotly panel: draws precomputed bars and error bars. Nothing here derives a number.
import Plotly from 'plotly.js-basic-dist-min';

const TRACE_KEYS = new Set(['type', 'x', 'y', 'width', 'name', 'error_y', 'marker']);
const LAYOUT_KEYS = new Set(['title', 'xaxis', 'yaxis', 'bargap', 'showlegend']);
const TOP_KEYS = new Set(['integration', 'data', 'layout', 'flow', 'errors']);

function only(obj, allowed, where) {
  for (const k of Object.keys(obj)) if (!allowed.has(k)) throw new Error(`${where}: '${k}' is not allowed`);
}

export function validate(p) {
  only(p, TOP_KEYS, 'plotly payload');
  if (p.integration !== 'plotly' || !Array.isArray(p.data)) throw new Error('not a plotly payload');
  for (const t of p.data) {
    only(t, TRACE_KEYS, 'plotly trace');
    if (t.type !== 'bar') throw new Error(`plotly trace type '${t.type}' is not allowed`); // no histogram*: they bin in the browser
    if (t.error_y) {
      only(t.error_y, new Set(['type', 'array', 'visible']), 'error_y');
      if (t.error_y.type !== 'data') throw new Error("error_y.type must be 'data' (no sqrt/percent/constant)");
    }
  }
  only(p.layout || {}, LAYOUT_KEYS, 'plotly layout');                                   // no barmode stack/relative, barnorm
}

export function note(p) {
  const parts = [];
  if (p.flow && (p.flow.underflow !== 0 || p.flow.overflow !== 0)) {
    parts.push(`not drawn: underflow ${p.flow.underflow}, overflow ${p.flow.overflow}`);
  }
  if (p.errors === 'disabled') parts.push('error bars disabled (weighted, no Sumw2)');
  return parts.join('; ');
}

export async function mount(el, p) {
  await Plotly.react(el, structuredClone(p.data), structuredClone(p.layout),
                     { displaylogo: false, responsive: true });
  return {
    // what Plotly actually holds, for the readback test
    readback: () => el.data.map((t) => ({ x: t.x, y: t.y, width: t.width,
                                          error: t.error_y ? t.error_y.array : null })),
    dispose: () => Plotly.purge(el),
  };
}
