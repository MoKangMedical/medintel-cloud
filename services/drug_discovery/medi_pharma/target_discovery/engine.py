"""
靶点发现引擎 — 整合自 medi-pharma 项目
PubMed文献挖掘 + 知识图谱查询 + 多维靶点评分
"""

import logging
import re
import time
from dataclasses import dataclass, asdict
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"
UNIPROT_API = "https://rest.uniprot.org"
OPENTARGETS_API = "https://api.platform.opentargets.org/api/v4/graphql"

GENE_PATTERN = re.compile(r'\b([A-Z][A-Z0-9]{1,10})\b')
GENE_STOPWORDS = {"DNA", "RNA", "PCR", "MRI", "CT", "FDA", "USA", "COVID", "SARS",
                  "HIV", "WHO", "THE", "AND", "FOR", "WITH", "FROM", "THIS", "THAT"}


@dataclass
class TargetReport:
    """靶点评估报告"""
    disease: str
    total_candidates: int
    top_targets: list[dict]
    methodology: str
    summary: str


class PubMedMiner:
    """PubMed文献挖掘器"""

    def __init__(self, email: str = "medintel@example.com", api_key: Optional[str] = None):
        self.email = email
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def search_disease_genes(self, disease: str, max_results: int = 50, min_year: int = 2015) -> list[dict]:
        query = f'({disease}[Title/Abstract]) AND (gene OR target) AND {min_year}:2026[PDAT]'
        params = {"db": "pubmed", "term": query, "retmax": max_results,
                  "retmode": "json", "sort": "relevance", "email": self.email}
        if self.api_key:
            params["api_key"] = self.api_key
        try:
            resp = self.client.get(f"{EUTILS_BASE}/esearch.fcgi", params=params)
            id_list = resp.json().get("esearchresult", {}).get("idlist", [])
            logger.info(f"PubMed '{disease}': {len(id_list)} results")
            return self._fetch_details(id_list) if id_list else []
        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return []

    def _fetch_details(self, pmids: list[str]) -> list[dict]:
        params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml",
                  "rettype": "abstract", "email": self.email}
        try:
            resp = self.client.get(f"{EUTILS_BASE}/efetch.fcgi", params=params)
            return self._parse_xml(resp.text, pmids)
        except Exception as e:
            logger.error(f"Fetch details failed: {e}")
            return [{"pmid": p, "title": "", "abstract": "", "year": 2024} for p in pmids]

    def _parse_xml(self, xml_text: str, pmids: list[str]) -> list[dict]:
        articles = []
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_text)
            for article in root.findall(".//PubmedArticle"):
                pmid_el = article.find(".//PMID")
                title_el = article.find(".//ArticleTitle")
                abstract_el = article.find(".//AbstractText")
                year_el = article.find(".//PubDate/Year")
                articles.append({
                    "pmid": pmid_el.text if pmid_el is not None else "",
                    "title": "".join(title_el.itertext()) if title_el is not None else "",
                    "abstract": ("".join(abstract_el.itertext())[:2000]) if abstract_el is not None else "",
                    "year": int(year_el.text) if year_el is not None else 2024,
                })
        except Exception as e:
            logger.warning(f"XML parse failed: {e}")
            for p in pmids:
                articles.append({"pmid": p, "title": "", "abstract": "", "year": 2024})
        return articles

    def extract_genes(self, articles: list[dict], llm_client=None, model: str = "mimo-v2-pro") -> list[dict]:
        """从文献中提取基因靶点"""
        if not articles:
            return []

        if llm_client:
            return self._llm_extract(articles, llm_client, model)
        return self._keyword_extract(articles)

    def _keyword_extract(self, articles: list[dict]) -> list[dict]:
        gene_counts: dict[str, int] = {}
        for article in articles:
            text = f"{article['title']} {article['abstract']}"
            for g in GENE_PATTERN.findall(text):
                if g not in GENE_STOPWORDS and len(g) > 2:
                    gene_counts[g] = gene_counts.get(g, 0) + 1
        results = []
        for gene, count in sorted(gene_counts.items(), key=lambda x: x[1], reverse=True)[:30]:
            strength = "strong" if count > 10 else "moderate" if count > 3 else "weak"
            results.append({
                "gene_symbol": gene, "total_papers": count,
                "evidence_strength": strength, "disease_associations": [],
            })
        return results

    def _llm_extract(self, articles: list[dict], llm_client, model: str) -> list[dict]:
        all_genes: dict[str, list] = {}
        batch_size = 10
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batch_text = "\n\n".join(
                f"[PMID:{a['pmid']}] {a['title']}\n{a['abstract']}"
                for a in batch if a['abstract']
            )
            if not batch_text.strip():
                continue
            try:
                resp = llm_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "从文献摘要中提取基因/靶点符号，返回JSON: [{gene:'SYMBOL',diseases:['...'],relevance:0-1}]"},
                        {"role": "user", "content": batch_text},
                    ],
                    temperature=0.1,
                )
                genes_data = self._parse_json(resp.choices[0].message.content)
                for g in genes_data:
                    gene = g.get("gene", "").upper()
                    if gene:
                        all_genes.setdefault(gene, []).append({
                            "diseases": g.get("diseases", []),
                            "relevance": g.get("relevance", 0.5),
                        })
            except Exception as e:
                logger.warning(f"LLM extraction failed (batch {i}): {e}")
            time.sleep(0.3)

        results = []
        for gene, ev_list in all_genes.items():
            avg_rel = sum(e["relevance"] for e in ev_list) / len(ev_list)
            strength = "strong" if avg_rel > 0.7 and len(ev_list) > 3 else "moderate" if avg_rel > 0.4 else "weak"
            results.append({
                "gene_symbol": gene, "total_papers": len(ev_list),
                "evidence_strength": strength, "disease_associations": list(set(d for e in ev_list for d in e["diseases"])),
            })
        results.sort(key=lambda x: x["total_papers"], reverse=True)
        return results

    @staticmethod
    def _parse_json(text: str) -> list[dict]:
        import json
        try:
            m = re.search(r'\[.*\]', text, re.DOTALL)
            return json.loads(m.group()) if m else json.loads(text)
        except (json.JSONDecodeError, AttributeError):
            return []


class KnowledgeGraphQuery:
    """多数据源靶点关联查询"""

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def query_uniprot(self, gene_symbol: str) -> dict:
        try:
            resp = self.client.get(f"{UNIPROT_API}/uniprotkb/search", params={
                "query": f"gene:{gene_symbol} AND organism_id:9606 AND reviewed:true",
                "format": "json", "size": 1,
            })
            results = resp.json().get("results", [])
            if results:
                e = results[0]
                return {
                    "uniprot_id": e.get("primaryAccession", ""),
                    "protein_name": (e.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "")),
                }
        except Exception as e:
            logger.warning(f"UniProt query failed ({gene_symbol}): {e}")
        return {}

    def query_chembl(self, gene_symbol: str) -> dict:
        try:
            resp = self.client.get(f"{CHEMBL_API}/target/search.json", params={"q": gene_symbol, "limit": 3})
            targets = resp.json().get("targets", [])
            if targets:
                t = targets[0]
                tid = t.get("target_chembl_id", "")
                act_resp = self.client.get(f"{CHEMBL_API}/activity.json", params={"target_chembl_id": tid, "limit": 1})
                return {
                    "chembl_id": tid, "target_type": t.get("target_type", ""),
                    "total_activities": act_resp.json().get("page_meta", {}).get("total_count", 0),
                }
        except Exception as e:
            logger.warning(f"ChEMBL query failed ({gene_symbol}): {e}")
        return {}

    def query_opentargets(self, gene_symbol: str) -> dict:
        try:
            resp = self.client.post(OPENTARGETS_API, json={
                "query": """query($q:String!){search(queryString:$q,entityNames:["target"],page:{size:1}){hits{id name}}}""",
                "variables": {"q": gene_symbol},
            })
            hits = resp.json().get("data", {}).get("search", {}).get("hits", [])
            if hits:
                eid = hits[0]["id"]
                resp2 = self.client.post(OPENTARGETS_API, json={
                    "query": """query($id:String!){target(ensemblId:$id){associatedDiseases(page:{size:5,index:0}){rows{disease{name}score}}knownDrugs{uniqueDrugs}}}""",
                    "variables": {"id": eid},
                })
                t = resp2.json().get("data", {}).get("target", {})
                diseases = [r["disease"]["name"] for r in t.get("associatedDiseases", {}).get("rows", [])]
                return {"diseases": diseases, "known_drugs": t.get("knownDrugs", {}).get("uniqueDrugs", 0)}
        except Exception as e:
            logger.warning(f"OpenTargets query failed ({gene_symbol}): {e}")
        return {}

    def batch_target_profile(self, gene_symbols: list[str]) -> list[dict]:
        results = []
        for gene in gene_symbols:
            try:
                profile = {"gene_symbol": gene}
                profile.update(self.query_uniprot(gene))
                profile.update(self.query_chembl(gene))
                profile.update(self.query_opentargets(gene))
                results.append(profile)
                time.sleep(0.3)
            except Exception as e:
                results.append({"gene_symbol": gene, "error": str(e)})
        return results


class TargetScorer:
    """靶点多维评分"""

    WEIGHTS = {"evidence": 0.25, "druggability": 0.25, "novelty": 0.20, "safety": 0.15, "commercial": 0.15}

    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or self.WEIGHTS

    def score_target(self, gene_symbol: str, evidence_strength: str = "moderate",
                     total_papers: int = 0, known_drugs: int = 0,
                     has_3d_structure: bool = False, is_essential_gene: bool = False,
                     disease_burden: float = 0.5, unmet_need: float = 0.5) -> dict:
        ev_map = {"strong": 0.9, "moderate": 0.5, "weak": 0.2}
        evidence = min(ev_map.get(evidence_strength, 0.3) + (0.1 if total_papers > 50 else 0), 1.0)

        drug = 0.5 + (0.2 if has_3d_structure else 0) + (0.2 if known_drugs > 0 else 0) + (0.1 if known_drugs > 10 else 0)
        drug = min(drug, 1.0)

        novelty = max(0.1, 1.0 - min(known_drugs / 100, 0.9))
        safety = max(0.1, min(0.7 - (0.2 if is_essential_gene else 0) + (0.2 if known_drugs > 5 else 0), 1.0))
        commercial = disease_burden * 0.5 + unmet_need * 0.5

        total = sum([
            evidence * self.weights["evidence"],
            drug * self.weights["druggability"],
            novelty * self.weights["novelty"],
            safety * self.weights["safety"],
            commercial * self.weights["commercial"],
        ])

        rec = "strong" if total > 0.7 else "moderate" if total > 0.5 else "weak" if total > 0.3 else "reject"

        return {
            "gene_symbol": gene_symbol,
            "evidence_score": round(evidence, 3),
            "druggability_score": round(drug, 3),
            "novelty_score": round(novelty, 3),
            "safety_score": round(safety, 3),
            "commercial_score": round(commercial, 3),
            "total_score": round(total, 3),
            "recommendation": rec,
        }

    def rank_targets(self, targets_data: list[dict]) -> list[dict]:
        scores = [self.score_target(**{k: v for k, v in t.items() if k in [
            "gene_symbol", "evidence_strength", "total_papers", "known_drugs",
            "has_3d_structure", "is_essential_gene", "disease_burden", "unmet_need",
        ]}) for t in targets_data]
        scores.sort(key=lambda x: x["total_score"], reverse=True)
        for i, s in enumerate(scores):
            s["rank"] = i + 1
        return scores


class TargetDiscoveryEngine:
    """
    靶点发现引擎
    疾病名称 → PubMed文献挖掘 + 知识图谱 + 多维评分 → 靶点评估报告
    """

    def __init__(self, llm_client=None, llm_model: str = "mimo-v2-pro", email: str = "medintel@example.com"):
        self.miner = PubMedMiner(email=email)
        self.kg = KnowledgeGraphQuery()
        self.scorer = TargetScorer()
        self.llm = llm_client
        self.model = llm_model

    def discover_targets(self, disease: str, max_papers: int = 50, top_n: int = 10,
                         disease_burden: float = 0.8, unmet_need: float = 0.8) -> TargetReport:
        logger.info(f"=== Target Discovery: {disease} ===")

        # Step 1: PubMed mining
        articles = self.miner.search_disease_genes(disease, max_results=max_papers)
        evidence_list = self.miner.extract_genes(articles, self.llm, self.model)

        # Step 2: Knowledge graph profiles
        gene_symbols = [e["gene_symbol"] for e in evidence_list[:20]]
        target_profiles = self.kg.batch_target_profile(gene_symbols)

        # Step 3: Merge and score
        profile_map = {p["gene_symbol"]: p for p in target_profiles if "gene_symbol" in p}
        merged = []
        for e in evidence_list:
            gene = e["gene_symbol"]
            profile = profile_map.get(gene, {})
            merged.append({
                "gene_symbol": gene,
                "evidence_strength": e.get("evidence_strength", "moderate"),
                "total_papers": e.get("total_papers", 0),
                "known_drugs": profile.get("known_drugs", 0),
                "has_3d_structure": bool(profile.get("uniprot_id")),
                "is_essential_gene": False,
                "disease_burden": disease_burden,
                "unmet_need": unmet_need,
            })

        ranked = self.scorer.rank_targets(merged)
        top_targets = ranked[:top_n]

        summary = self._generate_summary(disease, top_targets)
        return TargetReport(
            disease=disease,
            total_candidates=len(ranked),
            top_targets=top_targets,
            methodology="PubMed文献挖掘 + 多源知识图谱 + 多维评分",
            summary=summary,
        )

    def _generate_summary(self, disease: str, top_targets: list[dict]) -> str:
        if not top_targets:
            return f"未找到与{disease}相关的候选靶点。"
        if self.llm:
            try:
                targets_text = "\n".join(
                    f"- {t['gene_symbol']}: 综合分{t['total_score']}, 推荐{t['recommendation']}"
                    for t in top_targets[:5]
                )
                resp = self.llm.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是药物研发专家。根据靶点评分结果撰写简洁报告摘要（200字内）。"},
                        {"role": "user", "content": f"疾病：{disease}\n\nTop靶点：\n{targets_text}"},
                    ],
                    temperature=0.3,
                )
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"LLM summary failed: {e}")

        top_gene = top_targets[0]["gene_symbol"]
        strong_count = sum(1 for t in top_targets if t["recommendation"] == "strong")
        return f"针对{disease}，共分析{len(top_targets)}个候选靶点。Top推荐：{top_gene}（{top_targets[0]['total_score']}分）。其中{strong_count}个获strong推荐。"
