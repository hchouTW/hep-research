// Panel manager: layout, binding (event / dataset / static), lifecycle and stale-result protection.
// It never looks inside a payload; each chart library has its own module with validate / mount / readback / dispose.
import { fetchObject } from './objects.js';

const MODULES = {                     // one lazy chunk per library
  jsroot: () => import('./panels/jsroot.js'),
  plotly: () => import('./panels/plotly.js'),
  echarts: () => import('./panels/echarts.js'),
};
const MOUNT_TIMEOUT_MS = 15000;

function withTimeout(promise, ms, what) {
  let timer;
  return Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${what}: timed out after ${ms} ms`)), ms);
  })]).finally(() => clearTimeout(timer));
}

export class PanelManager {
  constructor(container, bundle) {
    this.container = container;
    this.panels = bundle.panels.map((spec) => ({ spec, generation: 0, handle: null, state: 'loading', el: null }));
  }

  async mountAll() {
    for (const p of this.panels) {
      const box = document.createElement('section');
      box.className = 'panel';
      box.dataset.panel = p.spec.id;
      box.innerHTML = '<h2></h2><div class="plot"></div><div class="note"></div>';
      box.querySelector('h2').textContent = p.spec.title + (p.spec.binding === 'static' ? ' (reference)' : '');
      this.container.append(box);
      p.el = box;
      if (!MODULES[p.spec.integration]) { this.setState(p, 'error', `unknown integration ${p.spec.integration}`); continue; }
      if (p.spec.binding === 'event') { this.setState(p, 'loading', 'waiting for an event'); continue; }
      await this.show(p, p.spec.payload, p.spec.sha256);   // dataset and static: drawn once
    }
  }

  // Called with every envelope from the EventController.
  onEnvelope(env) {
    for (const p of this.panels) {
      if (p.spec.binding !== 'event') continue;
      if (env.status !== 'committed') { this.clear(p); this.setState(p, 'error', `event ${env.event_key} failed`); continue; }
      const entry = p.spec.per_event[env.event_key];
      if (!entry) { this.clear(p); this.setState(p, 'unavailable', `no result for event ${env.event_key}`); continue; }
      this.show(p, entry.payload, entry.sha256);
    }
  }

  clear(p) {
    p.generation += 1;
    if (p.handle) { p.handle.dispose(); p.handle = null; }
    p.el.querySelector('.plot').replaceChildren();
  }

  async show(p, path, sha256) {
    this.clear(p);
    const generation = p.generation;
    this.setState(p, 'loading', 'loading…');
    try {
      const [mod, payload] = await Promise.all([MODULES[p.spec.integration](), fetchObject(path, sha256)]);
      if (generation !== p.generation) return;            // superseded while loading
      mod.validate(payload);                               // allowlist: refuse anything that computes in the browser
      const plot = p.el.querySelector('.plot');
      const handle = await withTimeout(mod.mount(plot, payload), MOUNT_TIMEOUT_MS, p.spec.id);
      if (generation !== p.generation) { handle.dispose(); return; }   // late mount after a newer request
      p.handle = handle;
      this.setState(p, 'ready', mod.note ? mod.note(payload) : '');
    } catch (e) {
      if (generation === p.generation) this.setState(p, 'error', e.message);
    }
  }

  setState(p, state, note) {
    p.state = state;
    p.el.className = `panel ${state}`;
    p.el.querySelector('.note').textContent = note;
  }

  readback(id) {
    const p = this.panels.find((q) => q.spec.id === id);
    return p && p.handle ? { state: p.state, data: p.handle.readback() } : { state: p ? p.state : 'missing', data: null };
  }
}
