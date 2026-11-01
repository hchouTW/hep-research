// Entry point: read bundle.json, set Phoenix up safely, load geometry, mount panels, show the default event.
import { EventDisplay, PhoenixLoader } from 'phoenix-event-display';
import { EventController } from './controller.js';
import { fetchObject } from './objects.js';
import { PanelManager } from './panels.js';

const statusEl = document.getElementById('status');
function setStatus(text, failed) {
  statusEl.textContent = text;
  statusEl.className = failed ? 'failed' : '';
}

async function start() {
  const response = await fetch('bundle.json', { cache: 'no-cache' });
  const bundle = await response.json();
  if (bundle.schema !== 'event-display-bundle/1') throw new Error(`unsupported bundle schema ${bundle.schema}`);
  document.title = bundle.title;
  document.getElementById('title').textContent = bundle.title;
  document.getElementById('labels').textContent = (bundle.labels || []).join(' · ');

  const ed = new EventDisplay();
  ed.init({
    elementId: 'eventDisplay',
    eventDataLoader: new PhoenixLoader(),   // without it buildEventDataFromJSON draws nothing
    allowUrlOptions: false,                  // no loading of files or options from the URL
    enableDatGUIMenu: true,                  // collection and geometry toggles without Angular
    defaultView: bundle.view?.camera ?? [4000, 2500, 4000, 0, 0, 0],   // [x, y, z, target x, y, z] in mm
  });
  delete window.EventDisplay;                // console hooks that could load files or change the scene

  const select = document.getElementById('eventSelect');
  const panels = new PanelManager(document.getElementById('panels'), bundle);
  const controller = new EventController(ed, bundle, {
    onEnvelope: (env) => {
      panels.onEnvelope(env);
      select.value = env.status === 'committed' ? env.event_key : (env.kept_event_key ?? select.value);
    },
    onStatus: setStatus,
  });

  // geometry first: events are committed only once the geometry is in place
  for (const g of bundle.geometry || []) {
    if (g.format !== 'obj') throw new Error(`geometry format ${g.format} is not supported by this template`);
    const text = await fetchObject(g.object, g.sha256, 'text');
    ed.parseOBJGeometry(text, g.name, 'Detector', true);
  }

  for (const e of bundle.events) {
    const option = document.createElement('option');
    option.value = e.key;
    option.textContent = `run ${e.id.run} · event ${e.id.event}`;
    select.append(option);
  }
  select.addEventListener('change', () => controller.select(select.value));

  await panels.mountAll();
  controller.select(bundle.default_event);

  // hooks for the page test (test_page.py): committed() and panel() only read; select() goes through the
  // controller exactly like the event selector, so it cannot bypass the digest check or the stale-response rule
  window.__eventDisplayTest = {
    committed: () => ({ key: controller.committedKey, revision: controller.revision,
                        integrityErrors: controller.integrityErrors }),
    select: (key) => controller.select(key),
    panel: (id) => panels.readback(id),
  };
}

start().catch((e) => setStatus(`failed to start: ${e.message}`, true));
