"""
AI 智能课题推荐服务 (Open-Ended Research Topic Recommendation Engine)
完全放开领域限制，由大模型在全人类知识图谱（人文历史、宏观社会、前沿科学、艺术哲学、前沿技术等）中自由发散推荐。
"""

import json
import re
import random
from typing import List, Dict, Optional, Any
from app.core.config import call_llm, CustomLLMConfig

# 全学科、跨领域多元优质课题备份池（涵盖人文、社会、宏观经济、哲学、气候、生命与科技）
DIVERSE_FALLBACK_TOPICS: List[Dict[str, str]] = [
    # 人文历史与考古文明
    {"title": "🏛️ 青铜时代晚期崩溃", "text": "公元前1200年地中海东部多重文明体系（迈锡尼/赫梯/埃及）同时崩溃的气候与社会成因研究"},
    {"title": "📜 轴心时代思想突破", "text": "公元前800-前200年欧亚大陆多文明独立诞生哲学与伦理体系的地理环境与社会结构动因"},
    {"title": "🏺 三星堆与古蜀文明", "text": "三星堆青铜器铸造工艺、外来文化因子与古蜀国神权社会体系的最新考古学推演"},

    # 宏观社会、经济与人口
    {"title": "📉 银发经济与代际转移", "text": "全球深度老龄化背景下养老金收支缺口、银发消费产业与家庭代际财富转移模式分析"},
    {"title": "🏙️ 韧性城市与微气候", "text": "应对极端高温与暴雨内涝的现代超级城市韧性基础设施改造成本与生态防灾效益评估"},
    {"title": "🌾 全球粮食供应地缘博弈", "text": "全球化肥原料（磷/钾矿）地缘垄断格局、极端气候波动对全球主粮价格传导机制测算"},
    {"title": "💼 数字游民与远程工作", "text": "后疫情时代全球数字游民签证政策、跨国个税合规与居住国当地租金物价外部性影响"},

    # 哲学、认知与心智科学
    {"title": "🧠 意识起源两大假说", "text": "意识的神经科学基础：整合信息理论 (IIT) 与全局神经工作空间理论 (GNW) 的实验证伪对比"},
    {"title": "⏳ 主观时间感知机制", "text": "人类大脑多巴胺神经递质、注意力分配与心理时间加速效应的认知神经科学机制"},
    {"title": "🤖 强人工智能道德主体地位", "text": "若具备自主反思意识的智能体出现，其法权人格、刑责主体资格与人类道德责任界定"},

    # 气候变化、深海与生态环境
    {"title": "🌊 南大洋深层环流变缓", "text": "南极冰架加速融化导致全球深海温盐环流减速的观测证据、气候多米诺骨牌效应与长期反馈"},
    {"title": "🐝 传粉昆虫生物多样性衰退", "text": "新烟碱类农药、栖息地破碎化对全球蜜蜂与野生传粉者的毒理效应及全球农业产量冲击"},
    {"title": "🌲 亚马孙雨林临界点研判", "text": "森林砍伐与区域降水循环互锁机制：亚马孙雨林向稀树草原退化的临界阈值测算"},

    # 前沿交叉科技与工程
    {"title": "⚡ 全固态电池产业商业化", "text": "全球全固态电池商业化量产时间表、主流技术路线（硫化物 vs 氧化物）及主要厂商竞争壁垒对比"},
    {"title": "🤖 具身智能与灵巧手", "text": "人形机器人高自由度灵巧手触觉传感器选型、腱绳驱动 vs 直驱方案及 Sim2Real 强化学习泛化进展"},
    {"title": "🧬 mRNA 肿瘤疫苗靶向递送", "text": "针对泛癌种的个性化新抗原 mRNA 治疗性疫苗：LNP 脂质纳米颗粒靶向器官分布与临床三期转化"},
    {"title": "🚀 可回收火箭发射经济性", "text": "不锈钢热防护瓦 vs 碳纤维箭体回收寿命、全流量分级燃烧循环甲烷发动机复用成本核算"},
    {"title": "❄️ 超导量子比特退相干", "text": "超导量子计算表面码 Surface Code 量子纠错阈值、两量子比特门保真度与稀释制冷机扩展瓶颈"},
    {"title": "💡 硅光集成与数据中心互联", "text": "1.6T 硅光收发器异质集成、微环调制器热漂移补偿与传统铜缆直连的成本功耗博弈"},

    # 文化媒介与数字社会学
    {"title": "📱 短视频时代的注意力碎片化", "text": "短视频算法强化回路对青少年深度长文本阅读能力、工作记忆容量与多巴胺阈值的重塑"},
    {"title": "🎮 游戏化社会与虚拟身份认同", "text": "沉浸式虚拟世界中的数字资产私有产权、虚拟劳工公会与现实社会阶层投射机制"}
]


def generate_recommendations(
    custom_llm_config: Optional[CustomLLMConfig] = None,
    count: int = 4
) -> List[Dict[str, str]]:
    """
    智能课题推荐引擎（完全开放无预设约束）：
    允许大模型自由驰骋于人文社科、自然科学、前沿技术、历史哲学等全领域。
    """
    safe_count = max(2, min(count, 8))
    
    prompt = (
        f"请生成 {safe_count} 个极具研究深度、适合展开系统性专业调研与论证的精选命题。\n"
        "【完全开放与多元化要求】：\n"
        "1. 绝不要局限于特定理工科或狭隘的某一两个工科领域！选题可自由取材于：人文历史、宏观社会、国际地缘与经济、心理认知与哲学、气候生态、前沿科技、艺术文化等任何人类重要探索方向；\n"
        "2. 每一个命题都应当具有深刻的内在矛盾、推演张力或前沿探索价值，避免浅显通俗的泛泛之谈；\n"
        "3. 输出格式必须为严格合法的 JSON 数组，严禁包含任何前言、后记或 Markdown 代码块外的文字。\n\n"
        "格式示例：\n"
        '[\n'
        '  {"title": "🏛️ 青铜时代晚期崩溃", "text": "公元前1200年地中海东部多重文明体系同时崩溃的气候与社会成因研究"},\n'
        '  {"title": "🧠 意识起源两大假说", "text": "意识的神经科学基础：整合信息理论 (IIT) 与全局神经工作空间理论 (GNW) 的实验证伪对比"}\n'
        ']'
    )

    system_prompt = (
        "你是一个学识渊博、贯通古今中西全学科的思想智库课题总监。"
        "你的任务是跳出狭隘的领域壁垒，为用户推荐充满好奇心、思想深度与前沿研究价值的跨学科课题。"
        "输出必须且只能是一个纯 JSON 数组，严禁携带任何其他无关字符。"
    )

    try:
        response = call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            custom_llm_config=custom_llm_config
        )
        
        cleaned = re.sub(r'^```(?:json)?\s*', '', response.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()
        
        match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', cleaned)
        if match:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list) and len(parsed) >= 2:
                valid_topics = []
                for item in parsed:
                    if isinstance(item, dict) and "title" in item and "text" in item:
                        t = str(item["title"]).strip()
                        x = str(item["text"]).strip()
                        if len(t) >= 2 and len(x) >= 6:
                            valid_topics.append({"title": t, "text": x})
                if len(valid_topics) >= 2:
                    return valid_topics[:safe_count]
    except Exception as e:
        print(f"[RecommendationService] 大模型生成课题失败，平滑从跨学科题库随机洗牌: {e}")

    # 兜底洗牌逻辑：从全学科题材库中随机抽取 count 个无重复项目
    sampled = random.sample(DIVERSE_FALLBACK_TOPICS, min(safe_count, len(DIVERSE_FALLBACK_TOPICS)))
    return sampled
