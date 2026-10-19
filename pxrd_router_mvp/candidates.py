"""Pinned candidate CIF registry; a deliberately restricted hypothesis set."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .crystal import Crystal, parse_cif

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Candidate:
    id: str
    name: str
    formula: str
    crystal_system: str
    cif: Path
    source_url: str
    source_record: str
    source_license: str
    lattice_tolerance: float
    expected_sha256: str

    def load(self) -> Crystal:
        if self.sha256 != self.expected_sha256:
            raise ValueError(f"{self.id}: CIF SHA-256 does not match the pinned source snapshot")
        crystal = parse_cif(self.cif)
        if crystal.crystal_system != self.crystal_system:
            raise ValueError(f"{self.id}: CIF system disagrees with registry")
        return crystal

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.cif.read_bytes()).hexdigest()


CANDIDATES = (
    Candidate("batio3_p4mm_cod9014273", "Barium titanate (tetragonal P4mm)", "BaTiO3", "tetragonal",
              ROOT / "candidates" / "BaTiO3_COD_9014273_P4mm.cif",
              "https://www.crystallography.net/cod/9014273.cif", "COD 9014273; Shirane et al., Phys. Rev. 105 (1957) 856–860, doi:10.1103/PhysRev.105.856",
              "Use with attribution to the source journal article per CIF header", 0.035,
              "e880d6f9df10ad4a2bb347dbbeae2712817d95e2f16df9390784d916a0c02f9c"),
    Candidate("mgo_rocksalt_cod9000505", "Magnesium oxide (rocksalt Fm-3m)", "MgO", "cubic",
              ROOT / "candidates" / "MgO_COD_9000505.cif",
              "https://www.crystallography.net/cod/9000505.cif", "COD 9000505; Hazen, Am. Mineral. 61 (1976) 266–271; 23 C, 1 atm",
              "COD public-domain/CC0 database; attribution to source article retained", 0.035,
              "73e348f73ec4e2e41f2ea08cbe5f393366e7cfeb55285eebbb185ace7ec94923"),
    Candidate("ceo2_fluorite_cod9009008", "Cerium dioxide (fluorite Fm-3m)", "CeO2", "cubic",
              ROOT / "candidates" / "CeO2_COD_9009008.cif",
              "https://www.crystallography.net/cod/9009008.cif", "COD 9009008; Wyckoff, Crystal Structures vol. 1 (1963), 239–444",
              "COD public domain / CC0; attribution retained", 0.035,
              "cfb862ebff35ab342a254a267eff4d94a86a18ae284142289e7b56d8d7b8e099"),
)


def candidate_by_id(candidate_id: str) -> Candidate:
    for candidate in CANDIDATES:
        if candidate.id == candidate_id:
            return candidate
    raise KeyError(candidate_id)


def available_candidates() -> tuple[Candidate, ...]:
    return tuple(candidate for candidate in CANDIDATES if candidate.cif.is_file())
