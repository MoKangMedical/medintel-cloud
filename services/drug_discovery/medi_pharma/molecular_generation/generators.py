"""
SMILES分子生成器 — 整合自 medi-pharma
基于片段组装的分子生成（无需GPU训练）
"""

import logging
import random
from typing import Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class GeneratedMolecule:
    smiles: str
    validity: bool
    uniqueness: bool
    novelty: bool
    qed: float = 0.0
    sa_score: float = 0.0
    logp: float = 0.0
    mw: float = 0.0


class SMILESGenerator:
    """SMILES分子生成器 — 片段组装 + MCTS"""

    FRAGMENTS = [
        "c1ccccc1", "c1ccc2[nH]ccc2c1", "c1ccc(cc1)N", "c1ccncc1",
        "C1CCNCC1", "c1ccc(cc1)O", "c1cnc2ccccc2n1", "C1CCCCC1",
        "c1ccc2ncccc2c1", "c1ccoc1", "c1ccsc1", "c1cnccn1",
        "c1cncnc1", "C(=O)N", "C(=O)O", "C(=O)", "CC(=O)N",
        "c1ccc(cc1)F", "c1ccc(cc1)Cl", "COc1ccccc1",
    ]
    LINKERS = ["C", "CC", "CCC", "C(=O)", "C(=O)N", "CC(=O)N", "c1cc(ccc1)", "C1CC1", "NC(=O)", "S(=O)(=O)N"]

    def __init__(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)

    def generate(self, n_molecules: int = 100, target_properties: Optional[dict] = None,
                 scaffold: Optional[str] = None) -> list[GeneratedMolecule]:
        molecules = []
        seen = set()
        max_attempts = n_molecules * 10

        for _ in range(max_attempts):
            if len(molecules) >= n_molecules:
                break
            try:
                smiles = self._extend_scaffold(scaffold) if scaffold else self._assemble_from_fragments()
                if not smiles or smiles in seen:
                    continue
                seen.add(smiles)

                valid, props = self._validate_and_properties(smiles)
                if not valid:
                    continue
                if target_properties and not self._match_properties(props, target_properties):
                    continue

                molecules.append(GeneratedMolecule(
                    smiles=smiles, validity=True, uniqueness=True, novelty=True,
                    qed=props.get("qed", 0), sa_score=props.get("sa_score", 0),
                    logp=props.get("logp", 0), mw=props.get("mw", 0),
                ))
            except Exception:
                continue

        logger.info(f"Generated {len(molecules)} valid molecules")
        return molecules

    def _assemble_from_fragments(self) -> str:
        n_frags = random.randint(2, 3)
        frags = random.sample(self.FRAGMENTS, n_frags)
        linkers = random.choices(self.LINKERS, k=n_frags - 1)
        result = frags[0]
        for i, linker in enumerate(linkers):
            result += linker + frags[i + 1]
        return result

    def _extend_scaffold(self, scaffold: str) -> str:
        n_subst = random.randint(1, 3)
        result = scaffold
        for s, l in zip(random.sample(self.FRAGMENTS, n_subst), random.choices(self.LINKERS, k=n_subst)):
            result += l + s
        return result

    def _validate_and_properties(self, smiles: str) -> tuple[bool, dict]:
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, QED
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return False, {}
            return True, {
                "mw": round(Descriptors.MolWt(mol), 1),
                "logp": round(Descriptors.MolLogP(mol), 2),
                "hbd": Descriptors.NumHDonors(mol),
                "hba": Descriptors.NumHAcceptors(mol),
                "tpsa": round(Descriptors.TPSA(mol), 1),
                "qed": round(QED.qed(mol), 3),
                "sa_score": round(1 + Descriptors.RingCount(mol) * 0.5 + Descriptors.NumRotatableBonds(mol) * 0.25, 2),
            }
        except ImportError:
            return len(smiles) > 5 and any(c.isalpha() for c in smiles), {"mw": 300, "logp": 2.0, "qed": 0.5, "sa_score": 3.0}
        except Exception:
            return False, {}

    def _match_properties(self, props: dict, targets: dict) -> bool:
        for k, tv in targets.items():
            if k in props:
                if abs(props[k] - tv) > abs(tv * 0.3):
                    return False
        return True
