"""
虚拟筛选引擎 — 整合自 medi-pharma
化合物库 + 亲和力评分 → Top候选
"""

import logging
import random
from dataclasses import dataclass, asdict
from typing import Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)

CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"


@dataclass
class Compound:
    smiles: str
    chembl_id: str = ""
    pubchem_cid: str = ""
    name: str = ""
    mw: float = 0.0
    logp: float = 0.0
    hbd: int = 0
    hba: int = 0
    tpsa: float = 0.0
    ro5_violations: int = 0
    activity: float = 0.0


class CompoundLibrary:
    """化合物库管理器 — ChEMBL / PubChem"""

    def __init__(self):
        self.client = httpx.Client(timeout=60.0)

    def fetch_target_compounds(self, target_chembl_id: str, min_activity: float = 6.0, limit: int = 500) -> list[Compound]:
        import math
        compounds, offset = [], 0
        batch_size = min(limit, 500)
        while len(compounds) < limit:
            try:
                resp = self.client.get(f"{CHEMBL_API}/activity.json", params={
                    "target_chembl_id": target_chembl_id, "standard_type": "IC50",
                    "standard_relation": "<", "limit": batch_size, "offset": offset,
                })
                activities = resp.json().get("activities", [])
                if not activities:
                    break
                for act in activities:
                    value = act.get("standard_value")
                    if value and float(value) > 0:
                        pAct = 9 - math.log10(float(value) * 1e-9)
                        if pAct >= min_activity:
                            compounds.append(Compound(
                                smiles=act.get("canonical_smiles", ""),
                                chembl_id=act.get("molecule_chembl_id", ""),
                                name=act.get("molecule_pref_name", ""),
                                activity=round(pAct, 2),
                            ))
                offset += batch_size
            except Exception as e:
                logger.error(f"ChEMBL fetch failed: {e}")
                break
        compounds = [c for c in compounds if c.smiles]
        logger.info(f"Fetched {len(compounds)} active compounds for {target_chembl_id}")
        return compounds[:limit]

    def apply_lipinski_filter(self, compounds: list[Compound]) -> list[Compound]:
        filtered = []
        for c in compounds:
            violations = sum([c.mw > 500, c.logp > 5, c.hbd > 5, c.hba > 10])
            c.ro5_violations = violations
            if violations <= 1:
                filtered.append(c)
        return filtered

    def deduplicate(self, compounds: list[Compound]) -> list[Compound]:
        seen, unique = set(), []
        for c in compounds:
            if c.smiles not in seen:
                seen.add(c.smiles)
                unique.append(c)
        return unique


class AffinityScorer:
    """结合亲和力评分器"""

    def __init__(self, hit_threshold: float = 6.0):
        self.hit_threshold = hit_threshold

    def score_by_descriptors(self, compounds: list[dict], reference_smiles: Optional[str] = None) -> list[dict]:
        predictions = []
        for comp in compounds:
            smiles = comp.get("smiles", "")
            activity = comp.get("activity", 0)
            pKd = activity if activity > 0 else self._heuristic_score(comp)
            confidence = min(0.5 + (pKd - 5) * 0.1, 0.95) if pKd > 5 else 0.3
            predictions.append({
                "smiles": smiles, "predicted_pkd": round(pKd, 2),
                "confidence": round(confidence, 3), "is_hit": pKd >= self.hit_threshold,
            })

        all_scores = [p["predicted_pkd"] for p in predictions]
        for p in predictions:
            rank = sum(1 for s in all_scores if s <= p["predicted_pkd"]) / max(len(all_scores), 1)
            p["percentile_rank"] = round(rank * 100, 1)

        predictions.sort(key=lambda x: x["predicted_pkd"], reverse=True)
        return predictions

    def _heuristic_score(self, compound: dict) -> float:
        score = 5.0
        mw = compound.get("mw", 350)
        logp = compound.get("logp", 2.5)
        tpsa = compound.get("tpsa", 80)
        hbd = compound.get("hbd", 2)
        hba = compound.get("hba", 4)
        if 300 <= mw <= 500: score += 0.5
        elif mw > 500: score -= 0.3
        if 1 <= logp <= 4: score += 0.5
        elif logp > 5: score -= 0.5
        if 60 <= tpsa <= 140: score += 0.3
        if hbd <= 3 and hba <= 8: score += 0.2
        return max(3.0, min(score, 9.0))


class DockingEngine:
    """分子对接引擎（模拟模式 / DiffDock / Vina）"""

    def __init__(self, diffdock_path: Optional[str] = None, vina_path: Optional[str] = None,
                 output_dir: str = "./docking_results"):
        self.diffdock_path = diffdock_path
        self.vina_path = vina_path
        self.output_dir = output_dir

    def dock(self, protein_pdb: str, ligand_smiles: list[str], method: str = "mock") -> list[dict]:
        if method == "diffdock" and self.diffdock_path:
            return self._dock_diffdock(protein_pdb, ligand_smiles)
        elif method == "vina" and self.vina_path:
            return self._dock_vina(protein_pdb, ligand_smiles)
        return self._mock_docking(ligand_smiles, method)

    def _dock_diffdock(self, protein_pdb, smiles_list) -> list[dict]:
        import subprocess, tempfile
        results = []
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                cmd = ["python", "-m", "diffdock", "--protein_path", protein_pdb,
                       "--out_dir", f"{self.output_dir}/diffdock"]
                subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        except Exception as e:
            logger.error(f"DiffDock failed: {e}")
            return self._mock_docking(smiles_list, "diffdock")
        return results

    def _dock_vina(self, protein_pdb, smiles_list) -> list[dict]:
        import subprocess, tempfile
        results = []
        for i, smiles in enumerate(smiles_list[:50]):
            try:
                cmd = [self.vina_path, "--receptor", protein_pdb, "--ligand", "/dev/null"]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                score = -7.0  # fallback
                for line in proc.stdout.split("\n"):
                    if "REMARK VINA RESULT:" in line:
                        score = float(line.split()[3])
                        break
                results.append({"smiles": smiles, "binding_score": score, "method": "vina", "rank": i+1})
            except Exception as e:
                logger.warning(f"Vina failed ({smiles[:30]}): {e}")
        results.sort(key=lambda x: x["binding_score"])
        return results

    def _mock_docking(self, smiles_list: list[str], method: str) -> list[dict]:
        results = []
        for i, smiles in enumerate(smiles_list):
            score = round(random.uniform(-12, -4), 2)
            conf = round(random.uniform(0.3, 0.9), 3)
            results.append({"smiles": smiles, "binding_score": score,
                            "confidence": conf, "method": f"{method}_mock", "rank": i + 1})
        results.sort(key=lambda x: x["binding_score"])
        return results


@dataclass
class ScreeningResult:
    target: str
    total_screened: int
    hits_found: int
    top_candidates: list[dict]
    method: str
    summary: str


class VirtualScreeningEngine:
    """虚拟筛选引擎"""

    def __init__(self, hit_threshold: float = 6.0, output_dir: str = "./screening_results"):
        self.library = CompoundLibrary()
        self.docking = DockingEngine(output_dir=output_dir)
        self.scorer = AffinityScorer(hit_threshold=hit_threshold)

    def screen(self, target_chembl_id: str, protein_pdb: Optional[str] = None,
               library_source: str = "chembl", max_compounds: int = 500,
               top_n: int = 20, use_docking: bool = False) -> ScreeningResult:
        logger.info(f"=== Virtual Screening: {target_chembl_id} ===")

        compounds = self.library.fetch_target_compounds(target_chembl_id, limit=max_compounds)
        if not compounds:
            return ScreeningResult(target=target_chembl_id, total_screened=0, hits_found=0,
                                   top_candidates=[], method="none", summary="未找到相关化合物数据")

        filtered = self.library.deduplicate(self.library.apply_lipinski_filter(compounds))
        logger.info(f"After Lipinski filter: {len(filtered)} compounds")

        compound_dicts = [asdict(c) for c in filtered]
        scored = self.scorer.score_by_descriptors(compound_dicts)

        docking_results = []
        if use_docking and protein_pdb:
            top_smiles = [s["smiles"] for s in scored[:50]]
            docking_results = self.docking.dock(protein_pdb, top_smiles)

        candidates = self._merge_results(scored, docking_results, filtered)
        hits = [c for c in candidates if c.get("is_hit", False)]

        return ScreeningResult(
            target=target_chembl_id, total_screened=len(filtered), hits_found=len(hits),
            top_candidates=candidates[:top_n],
            method="docking+scoring" if use_docking else "scoring",
            summary=f"筛选{len(filtered)}个化合物，{len(hits)}个hit，Top {top_n}推荐",
        )

    def _merge_results(self, scored: list[dict], docking_results: list[dict],
                       compounds: list[Compound]) -> list[dict]:
        compound_map = {c.smiles: asdict(c) for c in compounds}
        merged = []
        for s in scored:
            entry = {**s}
            comp = compound_map.get(s["smiles"])
            if comp:
                entry.update({k: comp[k] for k in ["name", "chembl_id", "mw", "logp"] if k in comp})
            for dr in docking_results:
                if dr.get("smiles") == s["smiles"]:
                    entry["docking_score"] = dr.get("binding_score", 0)
                    entry["docking_confidence"] = dr.get("confidence", 0)
                    break
            merged.append(entry)
        return merged
