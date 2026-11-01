// The only place that changes the displayed event. See references/event-display-facts.md for why each rule exists.
import { fetchObject } from './objects.js';

export class EventController {
  constructor(eventDisplay, bundle, { onEnvelope, onStatus }) {
    this.ed = eventDisplay;
    this.events = new Map(bundle.events.map((e) => [e.key, e]));
    this.onEnvelope = onEnvelope;
    this.onStatus = onStatus;
    this.latest = 0;          // id of the most recent request
    this.want = null;         // the request still to be served
    this.running = false;
    this.building = false;    // true only while this controller calls buildEventDataFromJSON
    this.committedKey = null;
    this.revision = 0;
    this.integrityErrors = 0;
    // Last line of defence: any displayed-event change not started here is an integrity error.
    // Phoenix clears these listeners when init() is called again, so attach after every init().
    this.ed.listenToDisplayedEventChange(() => {
      if (!this.building) {
        this.integrityErrors += 1;
        this.onStatus(`integrity error: the displayed event was changed outside the controller`, true);
      }
    });
  }

  select(key) {
    if (!this.events.has(key)) {           // never call loadEvent(): it ignores unknown keys silently
      this.onStatus(`unknown event ${key}`, true);
      return;
    }
    this.latest += 1;
    this.want = { key, request: this.latest };
    this.onStatus(`loading ${key}…`, false);
    if (!this.running) this.run();
  }

  async run() {
    this.running = true;
    while (this.want) {
      const { key, request } = this.want;
      this.want = null;
      const entry = this.events.get(key);
      let data = null;
      let error = null;
      try {
        data = await fetchObject(entry.scene, entry.sha256);
      } catch (e) {
        error = e;
      }
      if (request !== this.latest) continue;   // stale: a newer selection is waiting in this.want
      if (error) {
        // keep the last committed scene; the selector goes back to it
        this.onStatus(`event ${key} failed: ${error.message}`, true);
        this.onEnvelope({ status: 'failed', event_key: key, request_id: request, scene_revision: this.revision,
                          kept_event_key: this.committedKey });
        continue;
      }
      this.commit(key, request, data);
    }
    this.running = false;
  }

  commit(key, request, data) {
    // Phoenix writes uuid and other fields into the object it is given: always pass a deep copy.
    const copy = structuredClone(data);
    this.building = true;
    try {
      this.ed.buildEventDataFromJSON(copy);   // synchronous; needs configuration.eventDataLoader
      this.revision += 1;
      this.committedKey = key;
      this.onStatus(`event ${key}`, false);
      this.onEnvelope({ status: 'committed', event_key: key, request_id: request, scene_revision: this.revision });
    } catch (e) {
      try { this.ed.buildEventDataFromJSON({}); } catch { /* leave whatever Phoenix cleared */ }
      this.revision += 1;
      this.committedKey = null;               // no half-built scene and no stale event is shown
      this.onStatus(`event ${key} could not be drawn: ${e.message}`, true);
      this.onEnvelope({ status: 'failed', event_key: key, request_id: request, scene_revision: this.revision,
                        kept_event_key: null });
    } finally {
      this.building = false;
    }
  }
}
