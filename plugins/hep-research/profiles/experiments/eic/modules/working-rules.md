# Working rules: EIC profile

> Method owner: none (profile scope and labels); general methods belong to the skills named in [the placement inventory](placement-inventory.md).

- **Two scopes, never merged.** "EIC" names the facility (beams, polarization, interaction regions). "ePIC" names one experiment, the first at the EIC. A sentence about ePIC says "ePIC"; a sentence about the facility says "EIC". Do not write "the EIC detector".
- **Labels.** Every number is one of: design target (facility or project document), design value (detector concept), simulation projection, test-beam result, measurement. This profile ships only the first two kinds, and each claim's `scope.text` says which. Never call a projection or a design value "measured".
- **Nothing from memory.** A statement about the EIC or ePIC appears in a module only with a claim id (`C01`) whose source was read at the stated level on the stated date. A source published after a claim's verification date is unverified, not nonexistent.
- **Unknown stays unknown.** Beam-direction sign, polarization sign conventions, geometry release, data-format version and every performance number are `unknown` until the user or a cited release states them. Never fill them with a plausible value.
- **Ask before selecting.** A detector question that names the EIC but not the detector concept, geometry release and configuration (energies, species) asks for them. Do not pick ePIC silently; do not pick a configuration silently.
- **General methods live with their owners.** DIS kinematics and QCD (hep-theory), selection and corrections (hep-analysis), tracking, calorimetry and PID methods (detector-response), likelihoods and unfolding (hep-statistics), code and software environments (hep-computing). This profile adds EIC or ePIC application only, with a link to the owner.
- **Project material stays in the project.** Cuts, samples, campaign settings, private conditions, unpublished constants go in `hep-research.project.json`, a local profile or research artifacts, never here.
- **No software is run.** eic-shell, EICrecon, the epic geometry and EDM4eic are documented entry points; nothing here installs, builds or executes them, and no release is pinned.
