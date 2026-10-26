"""Provider protocol cr-provider/1 (steward hep-computing, core/OWNERS.json): the runner that calls a propagation
provider as a subprocess, its JSON Lines session, the provider-side entrypoint loop, the registry the caller passes in,
the point hash and its cache, and the conformance checks every provider passes. Standard library only.

Modules: protocol (the rules of the request, response and declaration, mirrored by the contract schema
cr_provider.json), hashing (the point hash), registry (loading the registry file the caller names), entrypoint (the
provider side: --request/--response and --serve), runner (the caller side: refusals, domain, cache, subprocess) and
conformance (the checks of PRV-1 and PRV-2). This package never searches for providers and holds no path to one: the
registry file names every entrypoint that may run.
"""
