// JSROOT panel: rebuilds the ROOT histogram from copied members and lets JSROOT draw it natively.
// JSROOT computes bin positions and error bars from these members (ROOT's own semantics); we only copy values.
// Imported from the same 'jsroot' package Phoenix uses, so there is a single JSROOT instance.
import { cleanup, createHistogram, draw } from 'jsroot';

const DRAW_OPTIONS = new Set(['e1 nostat', 'hist nostat']);   // stats box off: it is not checked against the source

export function validate(p) {
  if (p.integration !== 'jsroot' || p.typename !== 'TH1D' || !p.members) throw new Error('not a jsroot TH1D payload');
  if (!DRAW_OPTIONS.has(p.draw_option)) throw new Error(`jsroot draw option '${p.draw_option}' is not allowed`);
  const m = p.members;
  if (m.fArray.length !== m.fXaxis.fNbins + 2) throw new Error('fArray must hold nbins + 2 cells (with flow)');
  if (m.fSumw2.length && m.fSumw2.length !== m.fArray.length) throw new Error('fSumw2 length mismatch');
}

export function note(p) {
  return p.errors === 'disabled' ? 'error bars disabled (weighted, no Sumw2)' : '';
}

export async function mount(el, p) {
  const m = p.members;
  const h = createHistogram('TH1D', m.fXaxis.fNbins);
  h.fName = m.fName;
  h.fTitle = m.fTitle;
  Object.assign(h.fXaxis, { fXmin: m.fXaxis.fXmin, fXmax: m.fXaxis.fXmax, fXbins: [...m.fXaxis.fXbins],
                            fTitle: m.fXaxis.fTitle });
  h.fYaxis.fTitle = m.fYaxis.fTitle;
  h.fArray.set(m.fArray);
  h.fSumw2 = [...m.fSumw2];
  for (const k of ['fEntries', 'fTsumw', 'fTsumw2', 'fTsumwx', 'fTsumwx2']) if (m[k] !== null) h[k] = m[k];
  await draw(el, h, p.draw_option);
  return {
    // fXaxis.fFirst/fLast are left out: the JSROOT painter may change them while drawing
    readback: () => ({ fArray: Array.from(h.fArray), fSumw2: Array.from(h.fSumw2), fXbins: Array.from(h.fXaxis.fXbins),
                       fXmin: h.fXaxis.fXmin, fXmax: h.fXaxis.fXmax, fEntries: h.fEntries }),
    dispose: () => cleanup(el),
  };
}
