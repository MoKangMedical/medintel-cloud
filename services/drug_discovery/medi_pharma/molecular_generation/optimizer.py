"""
分子优化器 — 整合自 medi-pharma
支持遗传算法和爬山法的多目标分子优化
"""

import logging
import random
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger(__name__)


class MoleculeOptimizer:
    """分子优化器"""

    MUTATIONS = [
        "add_methyl", "remove_methyl", "add_fluorine", "add_chlorine",
        "add_hydroxyl", "add_amino", "replace_N_with_CH", "replace_CH_with_N",
        "add_ring", "ring_expansion", "ring_contraction", "add_amide",
    ]

    def __init__(self, scoring_fn: Optional[Callable] = None,
                 population_size: int = 50, n_generations: int = 20, mutation_rate: float = 0.3):
        self.scoring_fn = scoring_fn or self._default_score
        self.population_size = population_size
        self.n_generations = n_generations
        self.mutation_rate = mutation_rate

    def optimize(self, smiles: str, n_iterations: int = 100, target_props: Optional[dict] = None) -> list[dict]:
        best_smiles, best_score = smiles, self.scoring_fn(smiles)
        results = []
        for i in range(n_iterations):
            mutant = self._mutate(best_smiles)
            if not mutant:
                continue
            ms = self.scoring_fn(mutant)
            if ms > best_score:
                results.append({"original": best_smiles, "optimized": mutant,
                                "score_delta": round(ms - best_score, 3), "generation": i})
                best_smiles, best_score = mutant, ms
            elif random.random() < 0.1 * (1 - i / n_iterations):
                best_smiles, best_score = mutant, ms
        return results

    def genetic_optimize(self, initial_population: list[str], target_props: Optional[dict] = None) -> list[str]:
        population = initial_population[:self.population_size]
        for gen in range(self.n_generations):
            fitness = [self.scoring_fn(s) for s in population]
            selected = self._tournament_select(population, fitness, max(2, len(population) // 2))
            offspring = []
            for _ in range(self.population_size - len(selected)):
                p1, p2 = random.sample(selected, 2)
                child = self._crossover(p1, p2)
                if child:
                    offspring.append(child)
            for i in range(len(offspring)):
                if random.random() < self.mutation_rate:
                    m = self._mutate(offspring[i])
                    if m:
                        offspring[i] = m
            population = selected + offspring
        final_fitness = [self.scoring_fn(s) for s in population]
        return [s for _, s in sorted(zip(final_fitness, population), reverse=True)]

    def _mutate(self, smiles: str) -> Optional[str]:
        try:
            from rdkit import Chem
            mol = Chem.MolFromSmiles(smiles)
            if mol is None or mol.GetNumAtoms() < 2:
                return None
            mt = random.choice(["add_atom", "change_bond", "substitute"])
            if mt == "add_atom":
                return smiles + random.choice(["C", "N", "O", "F", "S"])
            elif mt == "substitute":
                for old, new in [("c1ccccc1", "c1ccc2[nH]ccc2c1"), ("C", "N"), ("CC", "C(=O)")]:
                    if old in smiles:
                        return smiles.replace(old, new, 1)
                return smiles + "C"
            return smiles + "C"
        except Exception:
            return None

    def _crossover(self, s1: str, s2: str) -> Optional[str]:
        try:
            from rdkit import Chem
            child = s1[:len(s1)//2] + s2[len(s2)//2:]
            mol = Chem.MolFromSmiles(child)
            return Chem.MolToSmiles(mol) if mol else None
        except Exception:
            return None

    def _tournament_select(self, population: list, fitness: list, k: int) -> list:
        selected = []
        for _ in range(k):
            cands = random.sample(range(len(population)), min(3, len(population)))
            selected.append(population[max(cands, key=lambda i: fitness[i])])
        return selected

    def _default_score(self, smiles: str) -> float:
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, QED
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return 0.0
            return round(QED.qed(mol) * 0.4 + min(Descriptors.MolLogP(mol) / 5, 1) * 0.2 +
                         min(Descriptors.MolWt(mol) / 500, 1) * 0.2 +
                         1 / (1 + Descriptors.RingCount(mol) * 0.2) * 0.2, 4)
        except Exception:
            return 0.5
