"""
ADMET预测引擎 — 整合自 medi-pharma
毒性 + PK + 合成可及性 → 综合ADMET报告
"""

import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


class ToxicityPredictor:
    """毒性预测器"""

    def predict_herg(self, smiles: str) -> float:
        risk = self._base_risk(smiles)
        props = self._quick_props(smiles)
        if props.get("logp", 0) > 4: risk += 0.15
        if props.get("mw", 0) > 450: risk += 0.1
        if props.get("psa", 0) < 60: risk += 0.1
        return round(min(max(risk, 0.05), 0.95), 3)

    def predict_ames(self, smiles: str) -> float:
        risk = self._base_risk(smiles)
        for alert in ["N(=O)=O", "[NH2]c1", "Nc1ccc", "c1ccc(N)"]:
            if alert in smiles: risk += 0.3
        return round(min(max(risk, 0.05), 0.95), 3)

    def predict_ld50(self, smiles: str) -> float:
        base = 2.8
        props = self._quick_props(smiles)
        if props.get("mw", 400) < 350: base += 0.3
        if props.get("logp", 3) < 3: base += 0.2
        for p in ["C#N", "N(=O)=O", "c1ccc(cc1)[N+]", "P(=O)"]:
            if p in smiles: base -= 0.5
        return round(max(base, 1.0), 3)

    def predict_dili(self, smiles: str) -> float:
        risk = self._base_risk(smiles)
        props = self._quick_props(smiles)
        if props.get("logp", 0) > 3.5: risk += 0.1
        if props.get("mw", 0) > 500: risk += 0.1
        return round(min(max(risk, 0.05), 0.95), 3)

    def predict_cardiotoxicity(self, smiles: str) -> float:
        return round(self.predict_herg(smiles) * 0.7 + self._base_risk(smiles) * 0.3, 3)

    def predict_cyp_inhibition(self, smiles: str, cyp: str) -> float:
        risk = self._base_risk(smiles)
        props = self._quick_props(smiles)
        if cyp in ["3A4", "2C9"] and props.get("logp", 0) > 3:
            risk += 0.15
        if cyp == "2D6" and "N" in smiles and props.get("logp", 0) > 2:
            risk += 0.1
        return round(min(max(risk, 0.05), 0.95), 3)

    def _base_risk(self, smiles: str) -> float:
        return round(0.2 + len(set(smiles)) / 20 * 0.1, 3)

    def _quick_props(self, smiles: str) -> dict:
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                return {"mw": Descriptors.MolWt(mol), "logp": Descriptors.MolLogP(mol),
                        "psa": Descriptors.TPSA(mol), "hbd": Descriptors.NumHDonors(mol),
                        "hba": Descriptors.NumHAcceptors(mol)}
        except Exception:
            pass
        return {"mw": 350, "logp": 2.5, "psa": 80, "hbd": 2, "hba": 4}


class PKPredictor:
    """药代动力学预测器"""

    def predict_caco2(self, smiles: str) -> float:
        props = self._quick_props(smiles)
        base = -5.0
        logp = props.get("logp", 2)
        if 1 <= logp <= 4: base += 0.3
        elif logp > 5: base -= 0.3
        if props.get("psa", 80) < 80: base += 0.3
        elif props.get("psa", 80) > 140: base -= 0.3
        if props.get("hbd", 2) <= 1: base += 0.2
        return round(base, 3)

    def predict_hia(self, smiles: str) -> float:
        props = self._quick_props(smiles)
        base = 0.5
        if props.get("mw", 350) < 400: base += 0.15
        if 1 <= props.get("logp", 2) <= 4: base += 0.15
        if props.get("psa", 80) < 100: base += 0.1
        if props.get("hbd", 2) <= 3: base += 0.1
        return round(min(max(base, 0.1), 0.99), 3)

    def predict_bioavailability(self, smiles: str) -> float:
        hia = self.predict_hia(smiles)
        base = hia * 0.7
        if self._quick_props(smiles).get("mw", 350) > 500: base -= 0.15
        return round(min(max(base, 0.05), 0.95), 3)

    def predict_bbb(self, smiles: str) -> float:
        props = self._quick_props(smiles)
        base = 0.4
        if props.get("mw", 350) < 400: base += 0.15
        if props.get("psa", 80) < 70: base += 0.2
        if props.get("logp", 2) > 2: base += 0.1
        if props.get("hbd", 2) <= 1: base += 0.15
        return round(min(max(base, 0.05), 0.99), 3)

    def predict_ppbr(self, smiles: str) -> float:
        props = self._quick_props(smiles)
        base = 0.75
        if props.get("logp", 2) > 3: base += 0.1
        if props.get("mw", 350) > 400: base += 0.05
        return round(min(max(base, 0.3), 0.99), 3)

    def predict_vd(self, smiles: str) -> float:
        return round(max(0.5 + self._quick_props(smiles).get("logp", 2) * 0.2, 0.1), 2)

    def predict_pgp(self, smiles: str) -> float:
        props = self._quick_props(smiles)
        base = 0.3
        if props.get("mw", 350) > 400: base += 0.15
        if props.get("hbd", 2) > 3: base += 0.1
        if props.get("psa", 80) > 100: base += 0.1
        return round(min(max(base, 0.1), 0.9), 3)

    def predict_clearance(self, smiles: str) -> float:
        props = self._quick_props(smiles)
        base = 5.0
        if props.get("logp", 2) > 4: base += 5.0
        if props.get("mw", 350) < 300: base += 3.0
        return round(base, 2)

    def predict_half_life(self, smiles: str) -> float:
        cl = self.predict_clearance(smiles) * 60 / 1000
        vd = self.predict_vd(smiles)
        return round(max(0.693 * vd / cl if cl > 0 else 12.0, 0.5), 2)

    def _quick_props(self, smiles: str) -> dict:
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                return {"mw": Descriptors.MolWt(mol), "logp": Descriptors.MolLogP(mol),
                        "psa": Descriptors.TPSA(mol), "hbd": Descriptors.NumHDonors(mol),
                        "hba": Descriptors.NumHAcceptors(mol)}
        except Exception:
            pass
        return {"mw": 350, "logp": 2.5, "psa": 80, "hbd": 2, "hba": 4}


class SAScorer:
    """合成可及性评分器"""

    def score(self, smiles: str) -> dict:
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {"sa_score": 10.0, "accessibility": "invalid", "n_steps": 99, "factors": ["无效SMILES"]}
            score = 1.0
            factors = []
            n_heavy = mol.GetNumHeavyAtoms()
            if n_heavy > 30: score += 1.5; factors.append(f"重原子数多({n_heavy})")
            elif n_heavy > 20: score += 0.8
            n_rings = Descriptors.RingCount(mol)
            if n_rings > 4: score += 1.5; factors.append(f"环数多({n_rings})")
            elif n_rings > 2: score += 0.5
            n_stereo = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))
            if n_stereo > 2: score += 1.0; factors.append(f"手性中心多({n_stereo})")
            n_rot = Descriptors.NumRotatableBonds(mol)
            if n_rot > 8: score += 0.8; factors.append(f"可旋转键多({n_rot})")
            for atom in mol.GetAtoms():
                if atom.GetSymbol() in {"P", "S", "B", "Si", "Se"}:
                    score += 0.3; factors.append(f"含特殊元素({atom.GetSymbol()})")
            score = min(max(score, 1.0), 10.0)
            accessibility = "easy" if score <= 3.5 else "moderate" if score <= 6.0 else "hard"
            return {"sa_score": round(score, 2), "accessibility": accessibility,
                    "n_steps": max(3, int(score * 1.5)), "factors": factors or ["标准药物分子结构"]}
        except ImportError:
            return {"sa_score": 4.0, "accessibility": "moderate", "n_steps": 6, "factors": ["RDKit未安装"]}


@dataclass
class ADMETReport:
    smiles: str
    absorption: dict
    distribution: dict
    metabolism: dict
    excretion: dict
    toxicity: dict
    synthesis: dict
    overall: dict
    pass_filter: bool
    recommendation: str


class ADMETEngine:
    """ADMET预测引擎"""

    THRESHOLDS = {"caco2": 0, "hia": 0.3, "bbb": -0.5, "herg_ic50": 10, "ames": 0.5, "ld50": 2.5, "sa_score": 6}

    def __init__(self):
        self.tox = ToxicityPredictor()
        self.pk = PKPredictor()
        self.sa = SAScorer()

    def predict(self, smiles: str) -> ADMETReport:
        absorption = {
            "caco2_permeability": self.pk.predict_caco2(smiles),
            "hia": self.pk.predict_hia(smiles),
            "oral_bioavailability": self.pk.predict_bioavailability(smiles),
            "pgp_substrate": self.pk.predict_pgp(smiles),
        }
        distribution = {
            "bbb_penetration": self.pk.predict_bbb(smiles),
            "ppbr": self.pk.predict_ppbr(smiles),
            "vd": self.pk.predict_vd(smiles),
        }
        metabolism = {
            "cyp1a2_inhibitor": self.tox.predict_cyp_inhibition(smiles, "1A2"),
            "cyp2c9_inhibitor": self.tox.predict_cyp_inhibition(smiles, "2C9"),
            "cyp2d6_inhibitor": self.tox.predict_cyp_inhibition(smiles, "2D6"),
            "cyp3a4_inhibitor": self.tox.predict_cyp_inhibition(smiles, "3A4"),
            "cyp2c19_inhibitor": self.tox.predict_cyp_inhibition(smiles, "2C19"),
        }
        excretion = {
            "clearance": self.pk.predict_clearance(smiles),
            "half_life": self.pk.predict_half_life(smiles),
        }
        toxicity = {
            "herg_inhibition": self.tox.predict_herg(smiles),
            "ames_mutagenicity": self.tox.predict_ames(smiles),
            "ld50": self.tox.predict_ld50(smiles),
            "dili": self.tox.predict_dili(smiles),
            "cardiotoxicity_risk": self.tox.predict_cardiotoxicity(smiles),
        }
        sa_result = self.sa.score(smiles)
        synthesis = {"sa_score": sa_result["sa_score"], "synthetic_accessibility": sa_result["accessibility"],
                     "n_steps_estimate": sa_result["n_steps"]}

        overall = self._calc_overall(absorption, distribution, metabolism, excretion, toxicity, synthesis)
        pass_filter = self._apply_filters(absorption, toxicity, synthesis)
        recommendation = "pass" if pass_filter else "warning" if overall["total_score"] > 0.4 else "reject"

        return ADMETReport(smiles=smiles, absorption=absorption, distribution=distribution,
                           metabolism=metabolism, excretion=excretion, toxicity=toxicity,
                           synthesis=synthesis, overall=overall, pass_filter=pass_filter,
                           recommendation=recommendation)

    def batch_predict(self, smiles_list: list[str]) -> list[dict]:
        results = []
        for smiles in smiles_list:
            try:
                results.append(asdict(self.predict(smiles)))
            except Exception as e:
                logger.warning(f"ADMET prediction failed ({smiles[:30]}): {e}")
                results.append({"smiles": smiles, "error": str(e)})
        return results

    def _calc_overall(self, abs_, dist, met, exc, tox, synth) -> dict:
        scores = {}
        abs_score = 0.5 + (0.2 if abs_["caco2_permeability"] > -5.15 else 0) + (0.2 if abs_["hia"] > 0.5 else 0) + (0.1 if abs_["oral_bioavailability"] > 0.3 else 0)
        scores["absorption"] = min(abs_score, 1.0)
        scores["distribution"] = min(0.5 + (0.2 if dist["ppbr"] < 0.95 else 0), 1.0)
        met_inhib = sum(1 for k, v in met.items() if v < 0.5)
        scores["metabolism"] = min(0.3 + met_inhib * 0.15, 1.0)
        tox_score = 0.8 - (0.1 if tox["herg_inhibition"] > 0.5 else 0) - (0.2 if tox["ames_mutagenicity"] > 0.5 else 0) - (0.2 if tox["dili"] > 0.5 else 0)
        scores["toxicity"] = max(tox_score, 0.1)
        scores["synthesis"] = max(0, 1 - (synth["sa_score"] - 1) / 9)
        scores["total_score"] = round(scores["absorption"] * 0.25 + scores["distribution"] * 0.15 +
                                      scores["metabolism"] * 0.15 + scores["toxicity"] * 0.30 + scores["synthesis"] * 0.15, 3)
        return {k: round(v, 3) for k, v in scores.items()}

    def _apply_filters(self, abs_, tox, synth) -> bool:
        if abs_["caco2_permeability"] < -5.5: return False
        if tox["herg_inhibition"] > 0.8: return False
        if synth["sa_score"] > 8: return False
        return True
