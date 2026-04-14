"""
🔍 天眼 Tianyan — 多Agent人群模拟 + 商业预测引擎
源自 tianyan 项目，适配 monorepo core/ 共享模型和 MIMO 客户端
"""

from __future__ import annotations

import json
import random
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

from core.utils.mimo_client import MIMOClient


# ═══════════════════════════════════════════════════════════════
#  合成人群工厂 (源自 tianyan/population.py)
# ═══════════════════════════════════════════════════════════════

CITY_TIERS = {
    "一线城市": ["北京", "上海", "广州", "深圳"],
    "新一线城市": ["成都", "杭州", "重庆", "武汉", "西安", "苏州", "南京", "天津", "长沙", "郑州"],
    "二线城市": ["大连", "厦门", "合肥", "佛山", "福州", "哈尔滨", "济南", "温州", "南宁", "长春"],
    "三线及以下": ["其他地级市", "县级市", "县城"],
}

AGE_DISTRIBUTION = {
    "18-24": 0.12, "25-34": 0.18, "35-44": 0.17,
    "45-54": 0.19, "55-64": 0.17, "65+": 0.17,
}

INCOME_BRACKETS = {
    "低收入": {"range": (2000, 5000), "pct": 0.35},
    "中等收入": {"range": (5000, 15000), "pct": 0.40},
    "中高收入": {"range": (15000, 30000), "pct": 0.15},
    "高收入": {"range": (30000, 100000), "pct": 0.08},
    "超高收入": {"range": (100000, 500000), "pct": 0.02},
}

CONSUMER_ARCHETYPES = [
    "精打细算型", "品质追求型", "跟风种草型", "理性决策型",
    "冲动消费型", "品牌忠诚型", "尝鲜探索型", "社交驱动型",
]


@dataclass
class PopulationProfile:
    agent_id: str
    age: int
    gender: str
    city_tier: str
    city: str
    monthly_income: int
    education: str
    occupation: str
    consumer_archetype: str
    digital_literacy: float
    price_sensitivity: float
    brand_loyalty: float
    social_influence: float
    health_consciousness: float
    risk_tolerance: float
    channels: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        return f"""你是一位{self.age}岁{self.gender}性，住在{self.city}（{self.city_tier}）。
学历：{self.education}，职业：{self.occupation}，月收入约{self.monthly_income}元。
消费风格：{self.consumer_archetype}
价格敏感度：{self.price_sensitivity:.0%}，品牌忠诚度：{self.brand_loyalty:.0%}
受社交影响程度：{self.social_influence:.0%}，健康意识：{self.health_consciousness:.0%}"""


class SyntheticPopulation:
    """合成人群工厂 — 基于中国公开统计数据生成合成人群"""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, n: int, constraints: Optional[dict] = None) -> list[PopulationProfile]:
        profiles = []
        for i in range(n):
            age_group = self.rng.choices(
                list(AGE_DISTRIBUTION.keys()), weights=list(AGE_DISTRIBUTION.values())
            )[0]
            age_range = age_group.replace("+", "-80").split("-")
            age = self.rng.randint(int(age_range[0]), int(age_range[1]))

            gender = self.rng.choice(["男", "女"])
            tier = self.rng.choice(list(CITY_TIERS.keys()))
            city = self.rng.choice(CITY_TIERS[tier])

            income_bracket = self.rng.choices(
                list(INCOME_BRACKETS.keys()),
                weights=[v["pct"] for v in INCOME_BRACKETS.values()],
            )[0]
            income_range = INCOME_BRACKETS[income_bracket]["range"]
            income = self.rng.randint(*income_range)

            education = self.rng.choices(
                ["初中及以下", "高中", "大专", "本科", "硕士及以上"],
                weights=[0.15, 0.25, 0.25, 0.25, 0.10],
            )[0]

            occupations = ["学生", "白领", "公务员", "自由职业", "企业管理", "工人", "退休", "个体户"]
            occupation = self.rng.choice(occupations)

            archetype = self.rng.choice(CONSUMER_ARCHETYPES)

            profile = PopulationProfile(
                agent_id=f"agent-{i+1:04d}",
                age=age, gender=gender, city_tier=tier, city=city,
                monthly_income=income, education=education, occupation=occupation,
                consumer_archetype=archetype,
                digital_literacy=round(self.rng.uniform(0.2, 1.0), 2),
                price_sensitivity=round(self.rng.uniform(0.1, 0.9), 2),
                brand_loyalty=round(self.rng.uniform(0.1, 0.9), 2),
                social_influence=round(self.rng.uniform(0.1, 0.9), 2),
                health_consciousness=round(self.rng.uniform(0.2, 0.95), 2),
                risk_tolerance=round(self.rng.uniform(0.1, 0.8), 2),
                channels=["微信", "抖音", "小红书"],
                interests=["健康", "美食", "旅行"],
            )

            # 应用约束
            if constraints:
                if "min_age" in constraints and profile.age < constraints["min_age"]:
                    continue
                if "max_age" in constraints and profile.age > constraints["max_age"]:
                    continue
                if "city_tiers" in constraints and profile.city_tier not in constraints["city_tiers"]:
                    continue

            profiles.append(profile)
        return profiles


# ═══════════════════════════════════════════════════════════════
#  多Agent模拟引擎 (源自 tianyan/agents.py)
# ═══════════════════════════════════════════════════════════════

@dataclass
class AgentDecision:
    agent_id: str
    decision: str
    confidence: float
    reasoning: str
    influenced_by: list[str] = field(default_factory=list)
    timestamp: int = 0


class SimulationAgent:
    """模拟Agent — 合成人群中的单个决策者"""

    def __init__(self, profile: PopulationProfile):
        self.profile = profile
        self.decisions: list[AgentDecision] = []
        self.connections: list[str] = []
        self.opinion_state: dict[str, float] = {}

    def evaluate(self, scenario_prompt: str) -> AgentDecision:
        """规则引擎决策"""
        p = self.profile
        # 基于画像的简单决策逻辑
        if "购买" in scenario_prompt or "产品" in scenario_prompt:
            willingness = (
                p.brand_loyalty * 0.3
                + (1 - p.price_sensitivity) * 0.3
                + p.social_influence * 0.2
                + p.risk_tolerance * 0.2
            )
            if p.consumer_archetype == "冲动消费型":
                willingness += 0.15
            elif p.consumer_archetype == "理性决策型":
                willingness -= 0.1
        elif "健康" in scenario_prompt or "体检" in scenario_prompt:
            willingness = p.health_consciousness * 0.6 + p.digital_literacy * 0.3 + 0.1
        else:
            willingness = 0.5 + p.digital_literacy * 0.3 - p.risk_tolerance * 0.1

        willingness = max(0, min(1, willingness))
        decision = "positive" if willingness > 0.55 else "negative" if willingness < 0.45 else "neutral"
        reasoning = f"基于{p.consumer_archetype}画像，意愿度{willingness:.0%}"

        agent_decision = AgentDecision(
            agent_id=p.agent_id, decision=decision,
            confidence=round(abs(willingness - 0.5) * 2, 2),
            reasoning=reasoning, timestamp=len(self.decisions),
        )
        self.decisions.append(agent_decision)
        return agent_decision

    async def evaluate_async(self, scenario_prompt: str, mimo: MIMOClient) -> AgentDecision:
        """LLM驱动决策"""
        context = self.profile.to_prompt_context()
        prompt = f"""{context}

场景：{scenario_prompt}

请以这个人的角度回答：你会怎么做？给出一个词（positive/negative/neutral）和简短理由。
返回JSON：{{"decision": "positive", "reasoning": "..."}}"""
        try:
            result = await mimo.chat(
                [{"role": "user", "content": prompt}],
                model="mimo-v2-pro", temperature=0.7, max_tokens=200,
            )
            parsed = json.loads(result)
            decision = parsed.get("decision", "neutral")
            reasoning = parsed.get("reasoning", "")
        except Exception:
            decision, _, reasoning = self._rule_based_decide(scenario_prompt)

        agent_decision = AgentDecision(
            agent_id=self.profile.agent_id, decision=decision,
            confidence=0.7, reasoning=reasoning,
        )
        self.decisions.append(agent_decision)
        return agent_decision

    def _rule_based_decide(self, scenario: str) -> tuple:
        return self.evaluate(scenario).decision, self.evaluate(scenario).confidence, self.evaluate(scenario).reasoning


class SimulationEngine:
    """人群模拟引擎"""

    def __init__(self, mimo: Optional[MIMOClient] = None):
        self.mimo = mimo
        self.population_factory = SyntheticPopulation()
        self._simulations: dict[str, dict] = {}

    async def run_simulation(self, config: dict) -> dict:
        """运行人群模拟"""
        n_agents = min(config.get("population_size", 100), 500)
        scenario = config.get("scenario", "产品购买意向")
        constraints = config.get("constraints", {})

        profiles = self.population_factory.generate(n_agents, constraints)
        agents = [SimulationAgent(p) for p in profiles]

        # 建立社交网络
        for i, agent in enumerate(agents):
            n_connections = min(5, len(agents) - 1)
            connections = random.sample(
                [a.profile.agent_id for j, a in enumerate(agents) if j != i],
                n_connections,
            )
            agent.connections = connections

        # 运行模拟
        decisions = []
        for agent in agents:
            if self.mimo and random.random() < 0.1:  # 10%用LLM（降本）
                d = await agent.evaluate_async(scenario, self.mimo)
            else:
                d = agent.evaluate(scenario)
            decisions.append(d)

        # 社交影响传播
        for _ in range(3):  # 3轮传播
            for agent in agents:
                neighbor_decisions = [
                    next((d for d in decisions if d.agent_id == cid), None)
                    for cid in agent.connections
                ]
                positive_ratio = sum(1 for d in neighbor_decisions if d and d.decision == "positive") / max(len(neighbor_decisions), 1)
                if positive_ratio > 0.7 and agent.profile.social_influence > 0.6:
                    # 社交影响：从众
                    for d in decisions:
                        if d.agent_id == agent.profile.agent_id and d.decision != "positive":
                            d.decision = "positive"
                            d.influenced_by = [cid for cid in agent.connections]
                            d.reasoning += "（受社交影响转变）"

        # 统计
        positive = sum(1 for d in decisions if d.decision == "positive")
        negative = sum(1 for d in decisions if d.decision == "negative")
        neutral = len(decisions) - positive - negative

        sim_id = f"sim-{len(self._simulations) + 1:04d}"
        result = {
            "simulation_id": sim_id,
            "scenario": scenario,
            "population_size": n_agents,
            "rounds": config.get("rounds", 1),
            "results": {
                "positive": positive, "negative": negative, "neutral": neutral,
                "adoption_rate": round(positive / n_agents * 100, 1),
                "avg_confidence": round(sum(d.confidence for d in decisions) / len(decisions), 2),
            },
            "segments": self._segment_results(profiles, decisions),
            "insights": self._generate_insights(profiles, decisions, scenario),
            "completed_at": datetime.now().isoformat(),
        }
        self._simulations[sim_id] = result
        return result

    def _segment_results(self, profiles: list[PopulationProfile], decisions: list[AgentDecision]) -> dict:
        segments = {}
        for profile, decision in zip(profiles, decisions):
            tier = profile.city_tier
            if tier not in segments:
                segments[tier] = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
            segments[tier][decision.decision] += 1
            segments[tier]["total"] += 1
        for tier in segments:
            total = segments[tier]["total"]
            segments[tier]["adoption_rate"] = round(segments[tier]["positive"] / total * 100, 1) if total else 0
        return segments

    def _generate_insights(self, profiles, decisions, scenario) -> list[str]:
        positive_profiles = [p for p, d in zip(profiles, decisions) if d.decision == "positive"]
        insights = []
        if positive_profiles:
            avg_age = sum(p.age for p in positive_profiles) / len(positive_profiles)
            insights.append(f"正面响应人群平均年龄：{avg_age:.0f}岁")
            top_archetype = max(set(p.consumer_archetype for p in positive_profiles),
                                key=lambda x: sum(1 for p in positive_profiles if p.consumer_archetype == x))
            insights.append(f"最积极的消费画像：{top_archetype}")
            avg_income = sum(p.monthly_income for p in positive_profiles) / len(positive_profiles)
            insights.append(f"正面响应人群平均月收入：¥{avg_income:,.0f}")
        return insights

    def get_simulation(self, sim_id: str) -> Optional[dict]:
        return self._simulations.get(sim_id)

    def list_simulations(self) -> list[dict]:
        return list(self._simulations.values())


class BusinessPredictionEngine:
    """商业预测引擎"""

    def __init__(self, mimo: Optional[MIMOClient] = None):
        self.mimo = mimo

    async def market_sizing(self, product_desc: str, target_market: str) -> dict:
        """市场规模预测"""
        if self.mimo:
            prompt = f"""为以下产品做市场规模估算：
产品：{product_desc}
目标市场：{target_market}
请估算TAM/SAM/SOM（单位：亿元），并说明假设。
返回JSON：{{"tam": ..., "sam": ..., "som": ..., "assumptions": [...]}}"""
            try:
                result = await self.mimo.chat(
                    [{"role": "user", "content": prompt}],
                    model="mimo-v2-pro", temperature=0.3, max_tokens=500,
                )
                return {"method": "ai_estimation", **json.loads(result)}
            except Exception:
                pass

        return {
            "method": "rule_estimation",
            "tam": round(random.uniform(100, 5000), 1),
            "sam": round(random.uniform(10, 500), 1),
            "som": round(random.uniform(1, 50), 1),
            "assumptions": ["基于行业公开数据估算", "需根据实际数据校准"],
        }

    async def competitive_analysis(self, company: str, competitors: list[str]) -> dict:
        """竞品分析"""
        if self.mimo:
            prompt = f"""分析{company}与竞品{competitors}的竞争态势。
从市场定位、产品差异、价格策略、渠道覆盖四维度分析。
返回JSON格式的竞争分析。"""
            try:
                result = await self.mimo.chat(
                    [{"role": "user", "content": prompt}],
                    model="mimo-v2-pro", temperature=0.3, max_tokens=800,
                )
                return {"method": "ai_analysis", "analysis": result}
            except Exception:
                pass

        return {
            "method": "template",
            "company": company,
            "competitors": competitors,
            "dimensions": ["市场定位", "产品差异", "价格策略", "渠道覆盖"],
            "note": "需要接入详细竞品数据以生成分析",
        }

    def forecast_revenue(self, historical_data: list[float], periods: int = 4) -> dict:
        """收入预测（简单线性回归）"""
        if len(historical_data) < 2:
            return {"error": "数据不足"}
        n = len(historical_data)
        x_mean = (n - 1) / 2
        y_mean = sum(historical_data) / n
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(historical_data))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator else 0
        intercept = y_mean - slope * x_mean
        forecasts = [round(intercept + slope * (n + i), 2) for i in range(periods)]
        return {
            "historical": historical_data,
            "forecasts": forecasts,
            "trend": "upward" if slope > 0 else "downward",
            "growth_rate": round(slope / y_mean * 100, 1) if y_mean else 0,
        }
