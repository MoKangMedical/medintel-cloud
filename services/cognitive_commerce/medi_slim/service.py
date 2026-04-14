"""
💄 MediSlim 认知商业服务 — AI体质评估 + 智能营销 + 智能客服
源自 medi-slim 项目，适配 monorepo core/ 共享模型和 MIMO 客户端
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from core.utils.mimo_client import MIMOClient


# ═══════════════════════════════════════════════════════════════
#  中医体质评估引擎
# ═══════════════════════════════════════════════════════════════

CONSTITUTION_DB = {
    "平和质": {"特征": "体态匀称、精力充沛、面色红润", "调养原则": "维持平衡", "推荐": ["均衡饮食", "适度运动"]},
    "气虚质": {"特征": "易疲劳、气短懒言、自汗", "调养原则": "益气健脾", "推荐": ["补气", "健脾", "黄芪"]},
    "阳虚质": {"特征": "畏寒怕冷、手脚冰凉、喜热饮", "调养原则": "温阳散寒", "推荐": ["温阳", "补肾", "艾灸"]},
    "阴虚质": {"特征": "手足心热、口干咽燥、盗汗", "调养原则": "滋阴降火", "推荐": ["滋阴", "润燥", "百合"]},
    "痰湿质": {"特征": "体形肥胖、腹部肥满、口黏苔腻", "调养原则": "健脾化湿", "推荐": ["祛湿", "化痰", "薏米"]},
    "湿热质": {"特征": "面垢油光、口苦口臭、大便黏滞", "调养原则": "清热利湿", "推荐": ["清热", "利湿", "菊花茶"]},
    "血瘀质": {"特征": "面色晦暗、易生瘀斑、健忘", "调养原则": "活血化瘀", "推荐": ["活血", "化瘀", "山楂"]},
    "气郁质": {"特征": "情绪低落、胸闷胁胀、善叹息", "调养原则": "疏肝解郁", "推荐": ["疏肝", "理气", "玫瑰花茶"]},
    "特禀质": {"特征": "过敏体质、易发哮喘、荨麻疹", "调养原则": "益气固表", "推荐": ["抗敏", "调理", "防风"]},
}

CONSTITUTION_QUESTIONNAIRE = [
    {"id": "q1", "category": "气虚质", "text": "您容易疲倦吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q2", "category": "气虚质", "text": "您容易气短（呼吸短促，接不上气）吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q3", "category": "阳虚质", "text": "您手脚发凉吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q4", "category": "阳虚质", "text": "您胃脘部、背部或腰膝部怕冷吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q5", "category": "阴虚质", "text": "您感到手脚心发热吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q6", "category": "阴虚质", "text": "您感觉身体、脸上发热吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q7", "category": "痰湿质", "text": "您感到身体沉重不轻松吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q8", "category": "痰湿质", "text": "您腹部肥满松软吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q9", "category": "湿热质", "text": "您面部或鼻部有油腻感吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q10", "category": "湿热质", "text": "您感到口苦或嘴里有异味吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q11", "category": "血瘀质", "text": "您的皮肤在不知不觉中会出现青紫瘀斑吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q12", "category": "血瘀质", "text": "您两颧部有细微红丝吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q13", "category": "气郁质", "text": "您感到闷闷不乐、情绪低沉吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q14", "category": "气郁质", "text": "您容易精神紧张、焦虑不安吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q15", "category": "特禀质", "text": "您没有感冒也会打喷嚏吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
    {"id": "q16", "category": "特禀质", "text": "您因季节变化、环境变化或异味而咳嗽喘息吗？", "options": ["从不", "偶尔", "有时", "经常", "总是"], "weight": 1.0},
]

HEALTH_RISK_MAP = {
    "气虚质": ["反复感冒", "慢性疲劳", "内脏下垂"],
    "阳虚质": ["关节痛", "消化不良", "宫寒痛经"],
    "阴虚质": ["失眠", "便秘", "慢性咽炎"],
    "痰湿质": ["肥胖", "高血脂", "糖尿病"],
    "湿热质": ["痤疮", "泌尿感染", "胆囊炎"],
    "血瘀质": ["心脑血管病", "痛经", "静脉曲张"],
    "气郁质": ["抑郁症", "甲状腺结节", "乳腺增生"],
    "特禀质": ["过敏性鼻炎", "哮喘", "荨麻疹"],
    "平和质": [],
}

# 产品库
PRODUCT_CATALOG = {
    "glp1": {
        "id": "GLP1-001", "name": "GLP-1 减重方案", "category": "处方",
        "subcategory": "减重", "price_first_month": 399, "price_monthly": 599,
        "target_constitutions": ["痰湿质", "湿热质"],
        "description": "司美格鲁肽/替尔泊肽 GLP-1 受体激动剂科学减重",
        "ingredients": ["司美格鲁肽", "替尔泊肽"],
    },
    "hair": {
        "id": "HAIR-001", "name": "防脱生发方案", "category": "处方",
        "subcategory": "防脱", "price_first_month": 199, "price_monthly": 299,
        "target_constitutions": ["气虚质", "血瘀质"],
        "description": "米诺地尔+非那雄胺，促进毛发生长",
        "ingredients": ["米诺地尔", "非那雄胺"],
    },
    "skin": {
        "id": "SKIN-001", "name": "皮肤管理方案", "category": "处方",
        "subcategory": "护肤", "price_first_month": 299, "price_monthly": 399,
        "target_constitutions": ["湿热质", "阴虚质"],
        "description": "祛痘/美白/抗衰三合一方案",
        "ingredients": ["维A酸", "烟酰胺", "透明质酸"],
    },
    "male": {
        "id": "MALE-001", "name": "男性健康方案", "category": "处方",
        "subcategory": "男性", "price_first_month": 399, "price_monthly": 599,
        "target_constitutions": ["阳虚质", "气虚质"],
        "description": "精力/睾酮管理方案",
        "ingredients": ["睾酮补充剂", "复合维生素"],
    },
    "sleep": {
        "id": "SLEEP-001", "name": "助眠调理方案", "category": "处方",
        "subcategory": "助眠", "price_first_month": 199, "price_monthly": 299,
        "target_constitutions": ["阴虚质", "气郁质"],
        "description": "失眠/褪黑素调理方案",
        "ingredients": ["褪黑素", "酸枣仁"],
    },
}


class ConstitutionEngine:
    """中医体质评估引擎"""

    def get_questionnaire(self) -> list[dict]:
        return CONSTITUTION_QUESTIONNAIRE

    def assess(self, answers: dict[str, int]) -> dict:
        """
        根据问卷答案计算体质得分。
        answers: {question_id: score(1-5)}  1=从不 5=总是
        """
        scores: dict[str, float] = {}
        for q in CONSTITUTION_QUESTIONNAIRE:
            cat = q["category"]
            score = answers.get(q["id"], 1)
            # 转换为反向分：1=从不→0, 5=总是→4
            raw = (score - 1) * q["weight"]
            scores[cat] = scores.get(cat, 0) + raw

        # 平和质 = 30 - 其他质最高分（简化版）
        other_max = max(scores.values()) if scores else 0
        scores["平和质"] = max(0, 30 - other_max * 2)

        # 标准化
        total = sum(scores.values()) or 1
        normalized = {k: round(v / total * 100, 1) for k, v in scores.items()}

        primary = max(normalized, key=normalized.get)
        secondary = sorted(
            [(k, v) for k, v in normalized.items() if k != primary and v > 15],
            key=lambda x: -x[1],
        )[:2]

        info = CONSTITUTION_DB.get(primary, {})

        return {
            "primary_type": primary,
            "primary_score": normalized[primary],
            "secondary_types": [{"type": t, "score": s} for t, s in secondary],
            "scores": normalized,
            "characteristics": info.get("特征", ""),
            "tcm_principles": [info.get("调养原则", "")],
            "health_risks": HEALTH_RISK_MAP.get(primary, []),
            "dietary_suggestions": info.get("推荐", []),
            "exercise_recommendations": self._exercise_recs(primary),
        }

    async def ai_assess(self, goals: list[str], mimo: MIMOClient) -> dict:
        """基于健康目标的 AI 体质推断"""
        prompt = f"""你是中医体质分析专家。根据以下健康目标推断最可能的体质类型（九选一），并给出简要分析。
健康目标：{', '.join(goals)}
九种体质：平和质、气虚质、阳虚质、阴虚质、痰湿质、湿热质、血瘀质、气郁质、特禀质
返回JSON格式：{{"primary_type": "体质名", "reasoning": "分析原因"}}"""
        try:
            result = await mimo.chat(
                [{"role": "user", "content": prompt}],
                model="mimo-v2-pro",
                temperature=0.3,
                max_tokens=300,
            )
            parsed = json.loads(result)
            primary = parsed.get("primary_type", "平和质")
            info = CONSTITUTION_DB.get(primary, {})
            return {
                "primary_type": primary,
                "reasoning": parsed.get("reasoning", ""),
                "characteristics": info.get("特征", ""),
                "health_risks": HEALTH_RISK_MAP.get(primary, []),
                "dietary_suggestions": info.get("推荐", []),
                "source": "ai_inference",
            }
        except Exception:
            # 降级到规则
            fallback_map = {
                "减重": "痰湿质", "减肥": "痰湿质", "肥胖": "痰湿质",
                "疲劳": "气虚质", "精力": "气虚质",
                "脱发": "血瘀质", "掉发": "血瘀质",
                "失眠": "阴虚质", "助眠": "阴虚质",
                "情绪": "气郁质", "焦虑": "气郁质",
                "过敏": "特禀质",
            }
            primary = "平和质"
            for goal in goals:
                for key, ctype in fallback_map.items():
                    if key in goal:
                        primary = ctype
                        break
            info = CONSTITUTION_DB.get(primary, {})
            return {
                "primary_type": primary,
                "reasoning": f"根据目标 {goals} 推断",
                "characteristics": info.get("特征", ""),
                "health_risks": HEALTH_RISK_MAP.get(primary, []),
                "dietary_suggestions": info.get("推荐", []),
                "source": "rule_fallback",
            }

    @staticmethod
    def _exercise_recs(ctype: str) -> list[str]:
        exercise_map = {
            "气虚质": ["太极拳", "散步", "八段锦"],
            "阳虚质": ["慢跑", "日光浴", "艾灸配合运动"],
            "阴虚质": ["游泳", "瑜伽", "冥想"],
            "痰湿质": ["快走", "游泳", "力量训练"],
            "湿热质": ["长跑", "球类运动", "力量训练"],
            "血瘀质": ["跳舞", "快走", "保健按摩"],
            "气郁质": ["瑜伽", "户外运动", "社交活动"],
            "特禀质": ["室内运动", "游泳", "太极"],
            "平和质": ["各种运动均可", "保持规律"],
        }
        return exercise_map.get(ctype, ["适度运动"])


class RecommendationEngine:
    """智能营销推荐引擎"""

    def __init__(self, mimo: Optional[MIMOClient] = None):
        self.mimo = mimo

    def recommend_by_constitution(self, constitution: str, goals: list[str] = None) -> list[dict]:
        """基于体质和目标的产品推荐"""
        recommendations = []
        goals = goals or []
        for pid, product in PRODUCT_CATALOG.items():
            score = 0
            if constitution in product["target_constitutions"]:
                score += 50
            for goal in goals:
                if goal in product["subcategory"] or goal in product["description"]:
                    score += 30
            if score > 30:
                recommendations.append({
                    "product_id": product["id"],
                    "name": product["name"],
                    "category": product["category"],
                    "price_first_month": product["price_first_month"],
                    "ai_score": score,
                    "match_reason": f"匹配{constitution}体质",
                })
        recommendations.sort(key=lambda x: -x["ai_score"])
        return recommendations[:3]

    def customer_segment(self, profile: dict) -> dict:
        """客户分群"""
        goals = profile.get("goals", [])
        age = profile.get("age", 30)

        if any(g in str(goals) for g in ["减重", "减肥", "瘦身"]):
            segment = "体重管理型"
        elif any(g in str(goals) for g in ["皮肤", "美白", "祛痘"]):
            segment = "美容需求型"
        elif any(g in str(goals) for g in ["血糖", "血压", "慢病"]):
            segment = "慢病管理型"
        elif age >= 55:
            segment = "老年养护型"
        elif any(g in str(goals) for g in ["产后", "月子"]):
            segment = "产后恢复型"
        else:
            segment = "健康关注型"

        return {"segment": segment, "confidence": 0.8}

    async def generate_campaign_content(self, segment: str, product_name: str) -> str:
        """AI 生成营销内容"""
        if not self.mimo:
            return f"专为{segment}人群定制的{product_name}，首月特惠进行中。"
        prompt = f"""为{segment}客户生成一段微信营销文案（不超过100字），推广{product_name}。
要求：温暖专业、不过度承诺、引导预约体质评估。"""
        try:
            return await self.mimo.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=200,
            )
        except Exception:
            return f"专为{segment}人群定制的{product_name}，首月特惠进行中。了解详情请预约体质评估。"


class CustomerServiceEngine:
    """AI 智能客服引擎"""

    FAQ_RESPONSES = {
        "减重": "我们的 GLP-1 减重方案通过司美格鲁肽/替尔泊肽实现科学减重，首月仅 ¥399。是否需要我帮您做个体质评估？",
        "减肥": "我们的 GLP-1 减重方案通过司美格鲁肽/替尔泊肽实现科学减重，首月仅 ¥399。是否需要我帮您做个体质评估？",
        "脱发": "防脱生发方案包含米诺地尔+非那雄胺，针对不同脱发原因定制方案。首月 ¥199 起，需要了解详情吗？",
        "掉发": "防脱生发方案包含米诺地尔+非那雄胺，针对不同脱发原因定制方案。首月 ¥199 起，需要了解详情吗？",
        "价格": "我们有 5 个品类，价格从 ¥199-599/月不等。具体取决于您的需求和体质。是否需要我帮您推荐？",
        "多少钱": "我们有 5 个品类，价格从 ¥199-599/月不等。具体取决于您的需求和体质。是否需要我帮您推荐？",
        "体质": "我们提供 AI 体质评估，通过九种体质分析为您推荐最适合的方案。是否立即开始评估？",
        "皮肤": "皮肤管理方案涵盖祛痘/美白/抗衰，首月 ¥299 起。需要根据您的肤质定制方案吗？",
        "失眠": "助眠调理方案采用褪黑素+酸枣仁组合，首月仅 ¥199。需要了解具体方案吗？",
        "过敏": "特禀质调理方案，通过益气固表法改善过敏体质。建议先做体质评估再定制方案。",
    }

    def __init__(self, mimo: Optional[MIMOClient] = None):
        self.mimo = mimo

    def classify_intent(self, message: str) -> dict:
        """意图分类"""
        msg = message.lower()
        categories = {
            "product_inquiry": ["价格", "多少钱", "什么", "介绍", "方案", "产品"],
            "consultation": ["体质", "评估", "检查", "推荐", "适合"],
            "complaint": ["投诉", "差评", "退款", "不满意", "效果不好"],
            "after_sales": ["发货", "物流", "退换", "售后"],
            "greeting": ["你好", "在吗", "hello", "hi"],
        }
        for cat, keywords in categories.items():
            if any(k in msg for k in keywords):
                return {"category": cat, "confidence": 0.85}
        return {"category": "general", "confidence": 0.5}

    def analyze_sentiment(self, message: str) -> str:
        """情感分析（规则降级）"""
        negative = ["投诉", "差评", "退款", "不满意", "效果不好", "骗", "垃圾", "骗钱"]
        positive = ["谢谢", "好的", "满意", "不错", "很好", "太好了"]
        msg = message
        if any(w in msg for w in negative):
            return "negative"
        if any(w in msg for w in positive):
            return "positive"
        return "neutral"

    async def respond(self, message: str, context: Optional[dict] = None) -> dict:
        """生成客服回复"""
        intent = self.classify_intent(message)
        sentiment = self.analyze_sentiment(message)

        # FAQ 匹配
        for keyword, faq_answer in self.FAQ_RESPONSES.items():
            if keyword in message:
                return {
                    "response": faq_answer,
                    "intent": intent["category"],
                    "sentiment": sentiment,
                    "source": "faq",
                    "escalate": sentiment == "negative",
                }

        # AI 回复
        if self.mimo:
            try:
                system = """你是 MediSlim 的 AI 健康顾问。回复要温暖专业，不过度承诺疗效。
引导用户做体质评估或预约医生咨询。如遇投诉建议转人工。"""
                response = await self.mimo.chat(
                    [
                        {"role": "system", "content": system},
                        {"role": "user", "content": message},
                    ],
                    temperature=0.7,
                    max_tokens=300,
                )
                return {
                    "response": response,
                    "intent": intent["category"],
                    "sentiment": sentiment,
                    "source": "ai",
                    "escalate": sentiment == "negative",
                }
            except Exception:
                pass

        return {
            "response": "我是 MediSlim AI 健康助手，可以帮您了解我们的产品和服务。请问有什么需要帮助的吗？",
            "intent": intent["category"],
            "sentiment": sentiment,
            "source": "fallback",
            "escalate": False,
        }


class DataAnalyticsEngine:
    """数据分析引擎"""

    def __init__(self):
        self._metrics: dict = {}

    def update_metrics(self, data: dict) -> None:
        self._metrics.update(data)

    def get_dashboard(self) -> dict:
        return {
            "metrics": self._metrics or {
                "total_users": 0, "active_users": 0,
                "total_orders": 0, "total_revenue": 0, "avg_order_value": 0,
            },
            "trends": {
                "users_growth": "+15%", "revenue_growth": "+25%", "order_growth": "+20%",
            },
            "top_products": [
                {"name": "GLP-1 减重", "sales": 156, "revenue": 62344},
                {"name": "防脱生发", "sales": 98, "revenue": 19402},
                {"name": "皮肤管理", "sales": 67, "revenue": 20033},
            ],
            "constitution_distribution": {
                "痰湿质": 35, "湿热质": 25, "气虚质": 15,
                "阳虚质": 10, "阴虚质": 8, "其他": 7,
            },
        }
