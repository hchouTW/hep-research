"""Synthetic documents for the reconstruction sidecar tests (contract witnesses W1-W7 of plan Section 12, conditions
payloads of R32). Each builder returns a fresh valid document; a test changes one field to make its negative case.
Every number is artificial, and passing proves the stated contract behaviour only (Section 12.1)."""


def code_list(report) -> list:
    return [finding.code for finding in report.errors]


def quantity(kind="energy-deposited", unit="MeV", basis="surface:cell-grid", hypothesis="none", level="reconstructed") -> dict:
    return {"kind": kind, "unit": unit, "basis": basis, "reference_hypothesis": hypothesis, "observation_level": level}


def port(direction="output", role="reconstruction-input", **fields) -> dict:
    document = {"schema": "reconstruction-port/1", "port_id": f"port.{direction}", "direction": direction,
                "native": {"type": "synthetic::CellCollection", "schema_ref": "synthetic/cells/1"},
                "quantity": quantity(), "role": role, "cardinality": "many",
                "presence": ["present", "valid-empty"], "required_extensions": []}
    document.update(fields)
    return document


def reference(product_id, key=None, row=None, revision=1, collection="measurements") -> dict:
    target = {"product_id": product_id, "collection": collection, "revision": revision}
    target.update({"key": key} if row is None else {"row": row})
    return target


def product(product_id="product.hits-a", objects=None, presence="present", revision=1, **fields) -> dict:
    document = {"schema": "reconstruction-product/1", "product_id": product_id, "revision": revision, "collection": "measurements",
                "native": {"type": "synthetic::MeasurementCollection"}, "presence": presence, "role": "reconstruction-input",
                "conditions_used": [], "required_extensions": []}
    if objects is not None:
        document["objects"] = objects
    document.update(fields)
    return document


def consumer(*records) -> dict:
    """A product that consumed these payload records."""
    return product(conditions_used=list(records))


def measurement(key, surface="surface:plane-1", state="measured", links=None) -> dict:
    return {"key": key, "surface": surface, "state_type": state, "native_ref": f"native:{key}", "source_links": links or []}


def collection_witness() -> dict:
    """W1: two products with distinct identities, both holding key 0, and a reordered subset of the first."""
    first = product("product.hits-a", [measurement(0), measurement(1), measurement(2)])
    second = product("product.hits-b", [measurement(0, surface="surface:plane-2", state="filtered")])
    subset = product("product.hits-a-subset", [measurement(2, links=[reference("product.hits-a", key=2)]),
                                               measurement(0, links=[reference("product.hits-a", key=0)])])
    return {"first": first, "second": second, "subset": subset}


def extended(document: dict, *extensions) -> dict:
    document["required_extensions"] = sorted(set(document["required_extensions"]) | set(extensions))
    return document


def identity_matrix(size: int) -> list:
    return [[int(row == column) for column in range(size)] for row in range(size)]


def pulse_estimate() -> dict:
    """W2, full rank: dimensionless artificial model with parameters ordered amplitude, baseline; not a pulse shape."""
    return {"parameters": ["amplitude", "baseline"],
            "model": {"design": [[1, 1], [0, 1], [0, 1]], "noise_covariance": identity_matrix(3), "shape": "fixed-template"},
            "observation": [5, 2, 2], "solution": [3, 2],
            "covariance": {"matrix": [[1.5, -0.5], [-0.5, 0.5]], "scope": "fixed-model", "includes": []},
            "identifiability": {"rank": 2, "status": "full", "unidentifiable": []},
            "regularization": "none", "status": "fit", "optimal_claim": True, "comparator": {"relative_tolerance": 1e-12}}


def truncated_pulse_estimate() -> dict:
    """W2 with the first sample removed: the amplitude column is all zeros, so only the baseline is delivered."""
    estimate = pulse_estimate()
    estimate.update({"model": {"design": [[0, 1], [0, 1]], "noise_covariance": identity_matrix(2), "shape": "fixed-template"},
                     "observation": [2, 2], "solution": None, "covariance": {"matrix": None, "scope": "fixed-model", "includes": []},
                     "identifiability": {"rank": 1, "status": "rank-deficient", "unidentifiable": ["amplitude"],
                                         "components": [{"weights": [0, 1], "value": 2, "variance": 0.5}]},
                     "status": "rank-deficient", "optimal_claim": False})
    return estimate


def pulse_product(estimate=None) -> dict:
    document = product("product.pulse", native={"type": "synthetic::PulseEstimate"})
    document["estimate"] = estimate or pulse_estimate()
    document["sampling"] = {"interval": {"value": 1, "unit": "ns"}, "time_origin": "trigger", "time_system": "digitizer-clock",
                            "channels": ["channel-0"], "window": [0, 3], "missing_samples": []}
    document["retention"] = {"raw": "removed", "waveform": "kept", "truth": "removed", "candidates": "not-applicable",
                             "conditions_snapshot": "kept", "lost_recalibrations": ["pedestal"]}
    return extended(document, "reconstruction:estimate-v1")


NOMINAL_GEOMETRY = "a" * 64
OTHER_GEOMETRY = "b" * 64


def sealed(payload: dict) -> dict:
    """Stamp a payload with the identity of its content."""
    from contracts.conditions import payload_identity
    payload["payload_id"] = payload_identity(payload)
    return payload


def iov(start=0, end=100, coordinate="position-key", closure="half-open") -> dict:
    return {"predicates": [{"coordinate": coordinate, "start": start, "end": end, "closure": closure}]}


def calibration_payload(content="1", upstream=(), start=0, end=100, tag="synthetic_gain_tag", **fields) -> dict:
    """A calibration payload holds a digest of native content, never constants: every value here is a placeholder."""
    payload = {"schema": "conditions-payload/1", "payload_id": "", "tag": tag, "kind": "calibration-constants",
               "producer": {"kind": "step", "step_id": "step.synthetic-gain"}, "iov": iov(start, end),
               "parametrization": {"name": "synthetic-per-channel", "version": "1"}, "frame": {"name": "channel", "kind": "local"},
               "derived_against": {"upstream_payloads": list(upstream)}, "constraints_used": [], "unconstrained_modes": [],
               "independent_validation": [], "origin": "measured", "content_sha256": content * 64, "required_extensions": []}
    payload.update(fields)
    return sealed(payload)


def alignment_payload(geometry=NOMINAL_GEOMETRY, content="2", **fields) -> dict:
    payload = {"schema": "conditions-payload/1", "payload_id": "", "tag": "synthetic_alignment_tag", "kind": "alignment-parameters",
               "producer": {"kind": "external", "source": "synthetic source"}, "iov": iov(),
               "parametrization": {"name": "synthetic-rigid", "version": "1"}, "frame": {"name": "structure", "kind": "local"},
               "alignment": {"degrees_of_freedom": [{"structure": "plane-1", "parameters": ["shift-u"], "frame": "local", "level": "sensor"}]},
               "derived_against": {"geometry_id": geometry}, "constraints_used": ["constraint.track-straightness"],
               "unconstrained_modes": ["mode.global-shear"], "independent_validation": ["validation.survey"], "origin": "measured",
               "content_sha256": content * 64, "required_extensions": []}
    payload.update(fields)
    return sealed(payload)


def used_payload(payload: dict, slot="gain") -> dict:
    return {"slot": slot, "tag": payload["tag"], "payload_id": payload["payload_id"], "origin": payload["origin"],
            "round": payload["loop"]["round"] if "loop" in payload else None}


def bound_payload(payload: dict, slot="gain") -> dict:
    return {"slot": slot, "tag": payload["tag"], "payload_id": payload["payload_id"], "origin": payload["origin"]}


def payload_valid_over(interval: dict) -> dict:
    return sealed(calibration_payload(iov=interval))


def frame_payloads() -> dict:
    return {"before": calibration_payload("1", start=0, end=5), "after": calibration_payload("2", start=5, end=10)}


def frame_window(key: int, missing=(7,), radius=1, keys=range(10)) -> str:
    neighbours = [key + step for step in range(-radius, radius + 1) if step]
    if any(neighbour not in keys for neighbour in neighbours):
        return "edge-incomplete"
    return "gap-adjacent" if any(neighbour in missing for neighbour in neighbours) else "complete"


def frame_witness(gap=7) -> dict:
    """W3: keys 0..9, cores [0,5) and [5,10), halo 1, a conditions change at key 5 and one original gap, at key 7 by default."""
    payloads = frame_payloads()
    windows = {key: frame_window(key, (gap,)) for key in range(10) if key != gap}
    outputs = [{"key": key, "owner": "core-a" if key < 5 else "core-b",
                "payload_id": payloads["before" if key < 5 else "after"]["payload_id"], "window": window}
               for key, window in windows.items()]
    return {"domain": [0, 10], "key_coordinate": "position-key",
            "partitions": [{"partition_id": "core-a", "core": [0, 5], "halo": 1, "halo_keys": [key for key in (5,) if key != gap]},
                           {"partition_id": "core-b", "core": [5, 10], "halo": 1, "halo_keys": [key for key in (4,) if key != gap]}],
            "missing_keys": [gap], "outputs": outputs,
            "accounts": {"observed": 9, "owned": 9, "missing": 1,
                         "edge_incomplete": [key for key, window in windows.items() if window == "edge-incomplete"],
                         "gap_adjacent": [key for key, window in windows.items() if window == "gap-adjacent"]}}


def frame_product(frames=None) -> dict:
    payloads = frame_payloads()
    document = product("product.frames", conditions_used=[used_payload(payloads["before"], "gain-before"), used_payload(payloads["after"], "gain-after")])
    document["frames"] = frames or frame_witness()
    return extended(document, "reconstruction:frames-v1")


def hypothesis(identity, revision, state, keys, group="group-1", **fields) -> dict:
    record = {"hypothesis_id": identity, "revision": revision, "state": state, "exclusive_group": group,
              "measurements": [reference("product.hits-a", key=key) for key in keys]}
    record.update(fields)
    return record


def candidate_witness() -> dict:
    """W4: H1 and H2 share measurement 0; H1 goes from revision 1 to 2 after reclustering."""
    return {"hypotheses": [hypothesis("H1", 1, "superseded", [0, 1]), hypothesis("H1", 2, "committed", [0, 2]),
                           hypothesis("H2", 1, "committed", [0, 1])],
            "selection_policy": {"kind": "declared-rule", "selected": {"group-1": "H1"}},
            "consumers": [{"consumer": "final-count", "hypothesis_id": "H1", "revision": 2, "use": "count"}],
            "memory_owner": {"type": "synthetic::CandidateStore"}, "pruning": []}


def candidate_product(candidates=None) -> dict:
    document = product("product.candidates")
    document["candidates"] = candidates or candidate_witness()
    return extended(document, "reconstruction:candidates-v1")


def inversion_witness() -> dict:
    """W5: A defines an artificial linear quantity, not a migration probability; x1 and x2 both give y."""
    return {"operator": {"matrix": [[1, 0, 1], [0, 1, 1]], "interpretation": "linear-quantity",
                         "input_quantity": quantity("linear-quantity", "1", "basis:source-grid"),
                         "output_quantity": quantity("linear-quantity", "1", "basis:detector-grid"),
                         "normalization": {"kind": "none", "basis": "declared"}, "native": {"type": "synthetic::LinearOperator"}},
            "observed": [1, 1], "solutions": [[1, 1, 0], [0, 0, 1]], "null_directions": [[1, 1, -1]], "uniqueness_claim": False,
            "prior": None, "selected_solution": None, "undetermined_components": [], "native_image": {"type": "synthetic::Image"},
            "response_ref": "native:operator", "background_ref": "native:background", "handoff": "hep-statistics",
            "comparator": {"relative_tolerance": 1e-12}}


def inversion_product(inversion=None) -> dict:
    document = product("product.image", native={"type": "synthetic::Image"})
    document["inversion"] = inversion or inversion_witness()
    return extended(document, "reconstruction:inversion-v1")


def seconds(value) -> dict:
    return {"value": value, "unit": "s"}


def count_witness() -> dict:
    """W6: a valid zero, an unread interval, and two channels with different valid exposure."""
    return {"capability": "counting", "observables": ["count"], "per_event_energy": False,
            "count_model": {"kind": "declared-sampling", "premises": ["fixed window", "dead time inside the valid exposure"], "inferred_from": None},
            "run_time": seconds(100),
            "selections": [{"selection_id": "selection.threshold-low", "kind": "threshold", "threshold": {"value": 3, "unit": "adc"}},
                           {"selection_id": "selection.threshold-high", "kind": "threshold", "threshold": {"value": 9, "unit": "adc"}}],
            "channels": [{"channel": "channel-a", "valid_exposure": seconds(80), "response_ref": "native:response-a", "selection_ref": "selection.threshold-low"},
                         {"channel": "channel-b", "valid_exposure": seconds(50), "response_ref": "native:response-b", "selection_ref": "selection.threshold-high"}],
            "intervals": [{"interval_id": "interval-1", "channel": "channel-a", "presence": "present", "count": 0},
                          {"interval_id": "interval-2", "channel": "channel-a", "presence": "absent"},
                          {"interval_id": "interval-3", "channel": "channel-b", "presence": "present", "count": 3}],
            "rates": [{"channel": "channel-a", "denominator": {"source": "valid-exposure", "value": 80, "unit": "s"}, "response_ref": "native:response-a", "selection_ref": "selection.threshold-low"},
                      {"channel": "channel-b", "denominator": {"source": "valid-exposure", "value": 50, "unit": "s"}, "response_ref": "native:response-b", "selection_ref": "selection.threshold-high"}]}


def coincidence_witness() -> dict:
    """A23, contract part: windows, accidentals, capture and escape, and denominators are retained."""
    return {"prompt_window": {"start": 0, "end": 1, "unit": "us"}, "delayed_window": {"start": 2, "end": 200, "unit": "us"},
            "accidentals": {"method": "off-time window", "reference": "native:accidentals"},
            "capture_escape": {"capture_reference": "native:capture", "escape_reference": "native:escape"},
            "denominators": ["prompt candidates", "valid exposure"]}


def count_product(counts=None) -> dict:
    document = product("product.counts", native={"type": "synthetic::CountTable"})
    document["counts"] = counts or count_witness()
    return extended(document, "reconstruction:counts-v1")


def scan_common(subcase, axis, kind, unit, merging, noise="declared-noise") -> dict:
    return {"subcase": subcase, "source_ref": "native:source", "coordinates": [{"axis": axis, "kind": kind, "unit": unit}],
            "conditions_ref": "native:conditions", "response_ref": "native:response", "noise_model": {"kind": noise, "premises": ["stated"]},
            "merging": {"kind": merging}, "unidentifiable": []}


def radio_frequency_scan() -> dict:
    """W7: two settings map to one physical-frequency interval through different local oscillators and share raw data."""
    setting = lambda name, oscillator, intermediate, segments: {  # noqa: E731
        "setting_id": name, "local_oscillator": {"value": oscillator, "unit": "MHz"}, "sideband_sign": 1, "interval_unit": "MHz",
        "intermediate_interval": intermediate, "physical_interval": [1010, 1030], "raw_segments": segments}
    scan = scan_common("rf-scan", "physical-frequency", "frequency", "MHz", "keep-settings")
    scan.update({"settings": [setting("setting-1", 1000, [10, 30], ["raw-1", "raw-2"]), setting("setting-2", 1010, [0, 20], ["raw-2", "raw-3"])],
                 "overlaps": [{"settings": ["setting-1", "setting-2"], "raw_segments": ["raw-2"], "shared_noise": True, "independent_exposure": False}]})
    return scan


def retarding_scan() -> dict:
    """W7: one setting revisited with a different dwell, keeping setting, time, count and transmission."""
    scan = scan_common("retarding-scan", "retarding-setting", "setting", "V", "keep-visits")
    scan["visits"] = [{"setting": "setting-1", "dwell": seconds(10), "count": 4, "transmission_ref": "native:transmission-1", "conditions_ref": "native:conditions-1"},
                      {"setting": "setting-1", "dwell": seconds(20), "count": 9, "transmission_ref": "native:transmission-2", "conditions_ref": "native:conditions-2"}]
    return scan


def global_scan() -> dict:
    """W7: y_i = s + b; both observations constrain only the sum of the shared sky quantity and the offset."""
    scan = scan_common("global", "observation-index", "index", "1", "joint-model")
    scan.update({"model": {"parameters": ["sky", "offset"], "design": [[1, 1], [1, 1]], "observation": [3, 3]},
                 "reported": [{"weights": [1, 1], "value": 3}], "constraint": None, "regularization": "none", "uniqueness_claim": False,
                 "unidentifiable": ["sky", "offset"]})
    return scan


def scan_product(scan) -> dict:
    document = product("product.scan", native={"type": "synthetic::ScanRecord"})
    document["scan"] = scan
    return extended(document, "reconstruction:scan-v1")


def recipe(**fields) -> dict:
    """A reconstruction recipe that refers to its method card and binds a synthetic profile's conditions."""
    gain = calibration_payload()
    document = {"schema": "reconstruction-recipe/1", "recipe_id": "recipe.linear-pulse", "status": "development",
                "method": {"card_ref": "method-card.linear-pulse", "card_sha256": "c" * 64},
                "implementation": {"backend": "synthetic-backend", "version": "1.0.0", "native_entrypoint": "synthetic-entry"},
                "inputs": [port("input")], "outputs": [port()], "converters": [], "independent_inputs": [],
                "profile_binding": {"profile_id": "synthetic-profile-a", "conditions": [bound_payload(gain)],
                                    "support_domain": {"rate": {"min": 0, "max": 10}}, "request": {"rate": 5}},
                "reproducibility": {"form": "numerical", "comparators": ["amplitude within a stated tolerance"]},
                "preconditions": ["design has full column rank"], "dependencies": ["input product", "effective configuration"],
                "execution": {"concurrency": "serialized", "slots": 1}, "checks": ["witness.linear-pulse"], "tool_contract": None,
                "evidence_ref": None, "command": ["synthetic-entry", "--config", "synthetic.json"], "runtime_evidence": None,
                "required_extensions": []}
    document.update(fields)
    return document


def proposal_recipe() -> dict:
    document = recipe(status="proposal", command=None)
    document["implementation"] = {"backend": None, "version": None, "native_entrypoint": None}
    return document


def evidence_check(check_id="witness.linear-pulse", state="pass", constructible=True) -> dict:
    return {"check_id": check_id, "state": state, "constructible": constructible}


def binding_evidence(state="passed", checks=None, stage="simulation-pilot", tested=(0, 10)) -> dict:
    from contracts.reconstruction import recipe_identity
    return {"schema": "binding-evidence/1", "evidence_id": "evidence.linear-pulse", "recipe_id": "recipe.linear-pulse", "recipe_sha256": recipe_identity(recipe()),
            "stage": stage, "state": state,
            "scope": {"statement": "synthetic fixture only", "tested_domain": {"rate": {"min": tested[0], "max": tested[1]}}},
            "checks": [evidence_check()] if checks is None else checks,
            "deployment_guarantee": False, "required_extensions": []}


def selection_record(**decision) -> dict:
    """The shape of plan Section 8.7: nothing is selected while the required semantics are unknown."""
    chosen = {"state": "needs-evidence", "chosen_recipe": None, "reason": "a waveform shape is insufficient", "decision_record_ref": None}
    chosen.update(decision)
    return {"schema": "selection-record/1", "record_id": "selection.unknown-waveform", "request": {"target": "amplitude", "deliverable": "local estimate"},
            "signature_ref": "signature.unknown-waveform",
            "policy": {"version": "1", "granularity": "dataset", "target": "amplitude", "quality_contract": None, "objective": None, "budgets": None},
            "candidates": [{"recipe": "recipe.linear-pulse", "hard_predicates": "unresolved", "quality_evidence": None,
                            "exclusion_or_probe_reason": "required semantics are not established"}],
            "decision": chosen, "trials": [], "sample_roles": [], "dependencies": ["signature.unknown-waveform"], "required_extensions": []}


def signature_fact(key="representation", value="waveform", kind="reader", method="observed", **fields) -> dict:
    fact = {"key": key, "value": value, "scope": "product.pulse", "source": {"kind": kind, "reference": "reader:synthetic-json/1"},
            "reader_version": "1", "method": method, "validity": "this product"}
    fact.update(fields)
    return fact


def input_signature(facts=None, **fields) -> dict:
    document = {"schema": "input-signature/1", "signature_id": "signature.unknown-waveform", "scope": {"product": "product.pulse", "window": "whole product"},
                "facts": [signature_fact()] if facts is None else facts, "unknown": ["quantity kind", "sampling clock"], "conflicts": [],
                "family_candidates": ["multiple"], "required_extensions": []}
    document.update(fields)
    return document


def constraint_witness(outcome="full", external="missing", internal="qualified", sufficient=True) -> dict:
    """A03, A25: the external constraint is missing; internal and joint alternatives are checked before any restriction."""
    resolution = {"target": "absolute-position", "external": {"name": "external-time-origin", "state": external},
                  "internal": [{"name": "internal-time-constraint", "state": internal, "sufficient": sufficient}], "joint": [],
                  "outcome": outcome, "restriction": None}
    if outcome == "restricted":
        resolution["restriction"] = {"omits": ["absolute position"], "reason": "the qualified constraints are insufficient"}
    return resolution


def constraint_product(resolution=None) -> dict:
    document = product("product.localization")
    document["constraint_resolution"] = resolution or constraint_witness()
    return extended(document, "reconstruction:constraints-v1")


def association_witness() -> dict:
    """A22: two sensor kinds associate through their respective responses, each stating a time base and window."""
    member = lambda name, kind, response, base: {"product_id": name, "sensor_kind": kind, "response_ref": response, "time_base": base,  # noqa: E731
                                                 "time_window": {"start": 0, "end": 10, "unit": "ms"}}
    return {"rule": "declared time matching", "members": [member("product.acoustic", "acoustic", "native:acoustic-response", "acoustic-clock"),
                                                          member("product.optical", "optical", "native:optical-response", "optical-clock")]}


def association_product(association=None) -> dict:
    document = product("product.association")
    document["association"] = association or association_witness()
    return extended(document, "reconstruction:association-v1")
