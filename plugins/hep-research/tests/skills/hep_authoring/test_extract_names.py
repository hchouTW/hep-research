"""skills/hep-authoring/scripts/extract_names.py (semantic naming N14, N15): labels, label references, macros,
included figure and table files with their N2 targets, BibTeX keys with their record ids and citations."""
from __future__ import annotations

import unittest

from tests.skills.naming_extractor_helpers import ProjectCase

TEX = r"""\newcommand{\fluxunit}{m^{-2}}
\begin{figure}\includegraphics[width=1\linewidth]{figs/spectrum}\label{fig:spectrum}\end{figure}
See \cref{fig:spectrum,fig:missing}; \input{tables/yields} in \fluxunit. \citep[p.~3]{A2015,B2015}
% \label{fig:commented}
"""
BIB = """@article{A2015,
  doi = {10.1103/PhysRevLett.114.171103},
}
@article{B2015, eprint = "1503.04245"}
@string{journal = "PRL"}
"""


class AuthoringTests(ProjectCase):
    SKILL = "hep-authoring"

    def setUp(self):
        super().setUp()
        self.write("paper/main.tex", TEX)
        self.write("paper/figs/spectrum.pdf", "x")
        self.write("paper/refs.bib", BIB)

    def test_n14(self):
        _, inv = self.extract("N14")
        self.assertEqual(self.names(inv, "label"), ["fig:spectrum"])  # the commented label is left out
        self.assertEqual(self.names(inv, "label_reference"), ["fig:spectrum", "fig:missing"])
        self.assertEqual(self.names(inv, "macro"), ["fluxunit"])
        self.assertEqual(self.entity(inv, "fluxunit")["references"], [{"from": "paper/main.tex:3", "kind": "uses"}])
        fig = self.entity(inv, "figs/spectrum")
        self.assertEqual(fig["targets"], [{"surface": "N2", "name": "spectrum.pdf", "kind": "includes",
                                           "file": "paper/figs/spectrum.pdf"}])
        self.assertNotIn("file", self.entity(inv, "tables/yields")["targets"][0])  # not in the project

    def test_n15(self):
        _, inv = self.extract("N15")
        self.assertEqual(self.names(inv), ["A2015", "B2015"])
        a, b = self.entity(inv, "A2015"), self.entity(inv, "B2015")
        self.assertEqual(a["meaning"]["concept_id"], "doi:10.1103/physrevlett.114.171103")
        self.assertEqual(b["meaning"]["concept_id"], "arxiv:1503.04245")
        self.assertEqual(a["references"], [{"from": "paper/main.tex:3", "kind": "cites"}])


if __name__ == "__main__":
    unittest.main()
