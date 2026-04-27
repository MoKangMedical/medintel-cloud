"""
分子生成引擎 — 整合自 medi-pharma
靶点信息 → 生成+优化 → 候选分子
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .generators import SMILESGenerator
from .optimizer import MoleculeOptimizer

logger = logging.getLogger(__name__)


@dataclass
class GenerationReport:
    target: str
    total_generated: int
    valid_molecules: int
    top_candidates: list[dict]
    method: str
    summary: str


class MolecularGenerationEngine:
    """分子生成引擎"""

    def __init__(self, seed: int = 42):
        self.generator = SMILESGenerator(seed=seed)
        self.optimizer = MoleculeOptimizer()

    def generate_candidates(self, target_name: str = "", scaffold: Optional[str] = None,
                            n_generate: int = 200, n_optimize: int = 50,
                            target_properties: Optional[dict] = None, top_n: int = 20) -> GenerationReport:
        props = target_properties or {"mw": 400, "logp": 2.5, "hbd": 2, "hba": 5}
        logger.info(f"=== Molecular Generation: {target_name or 'de novo'} ===")

        generated = self.generator.generate(n_molecules=n_generate, target_properties=props, scaffold=scaffold)
        if not generated:
            return GenerationReport(target=target_name, total_generated=0, valid_molecules=0,
                                    top_candidates=[], method="de novo", summary="分子生成失败")

        sorted_mols = sorted(generated, key=lambda m: m.qed, reverse=True)
        initial = [m.smiles for m in sorted_mols[:min(50, len(sorted_mols))]]

        if n_optimize > 0 and len(initial) > 5:
            optimized = self.optimizer.genetic_optimize(initial, target_props=props)
            all_smiles = list(set([m.smiles for m in generated] + optimized))
        else:
            all_smiles = [m.smiles for m in generated]

        candidates = []
        seen = set()
        for smiles in all_smiles:
            if smiles in seen:
                continue
            seen.add(smiles)
            valid, props_dict = self.generator._validate_and_properties(smiles)
            if valid:
                candidates.append({"smiles": smiles, **props_dict})

        candidates.sort(key=lambda c: c.get("qed", 0), reverse=True)
        top = candidates[:top_n]

        return GenerationReport(
            target=target_name, total_generated=len(generated), valid_molecules=len(candidates),
            top_candidates=top, method="de_novo_generation + genetic_optimization",
            summary=f"生成{len(generated)}个分子，{len(candidates)}个有效，Top {top_n}已选出",
        )

    def scaffold_hop(self, reference_smiles: str, n_variants: int = 50) -> GenerationReport:
        generated = self.generator.generate(n_molecules=n_variants)
        candidates = [{"smiles": m.smiles, "qed": m.qed, "sa_score": m.sa_score,
                       "logp": m.logp, "mw": m.mw} for m in generated if m.validity]
        return GenerationReport(
            target=f"scaffold_hop:{reference_smiles[:30]}", total_generated=len(generated),
            valid_molecules=len(candidates), top_candidates=candidates[:n_variants],
            method="scaffold_hopping", summary=f"骨架跃迁生成{len(candidates)}个新骨架",
        )
