import re
import math
from typing import List, Dict, Any, Tuple, Optional

# 核心结论与关键量化特征词库
CONCLUSION_INDICATORS = {
    "结论", "总结", "发现", "核心", "关键", "突破", "瓶颈", "挑战", "优势", "劣势",
    "痛点", "壁垒", "对比", "测算", "预测", "量产", "路线", "商业化", "指标", "参数",
    "标准", "毛利", "出货量", "渗透率", "专利", "厂商", "供应链",
    "conclusion", "summary", "finding", "key", "breakthrough", "bottleneck",
    "challenge", "advantage", "disadvantage", "benchmark", "comparison",
    "forecast", "prediction", "commercialization", "roadmap", "metric", "parameter"
}

def tokenize_text(text: str) -> List[str]:
    """通用中英文分词与关键词抽取"""
    if not text:
        return []
    # 提取英文单词与中文 1-2 gram
    words = re.findall(r'[a-zA-Z0-9_\-\.]+|[\u4e00-\u9fff]', text.lower())
    return words

def chunk_webpage_for_rerank(
    text: str,
    chunk_size: int = 800,
    min_chunk_size: int = 150
) -> List[str]:
    """
    长网页动态语义分块 (Smart Chunking)。
    弃用前部粗暴截取，按 Markdown 标题、表格与段落语义边界切分为 ~800 字符的独立语义段落。
    """
    if not text or not text.strip():
        return []

    # 1. 按连续换行或标题分段
    raw_paragraphs = re.split(r'\n{2,}|\n(?=#{1,4}\s)', text)
    cleaned_paragraphs: List[str] = []
    
    for p in raw_paragraphs:
        p_str = p.strip()
        if not p_str:
            continue
        cleaned_paragraphs.append(p_str)

    chunks: List[str] = []
    current_chunk = ""

    for p in cleaned_paragraphs:
        if not current_chunk:
            current_chunk = p
        elif len(current_chunk) + len(p) + 2 <= chunk_size:
            current_chunk += "\n\n" + p
        else:
            chunks.append(current_chunk)
            if len(p) > chunk_size:
                # 超长段落按句子标点继续细分
                sub_sentences = re.split(r'([。！？\n]|\.\s)', p)
                sub_buf = ""
                for s in sub_sentences:
                    if not s:
                        continue
                    if len(sub_buf) + len(s) <= chunk_size:
                        sub_buf += s
                    else:
                        if len(sub_buf) >= min_chunk_size:
                            chunks.append(sub_buf.strip())
                            sub_buf = s
                        else:
                            sub_buf += s
                if sub_buf.strip():
                    current_chunk = sub_buf.strip()
                else:
                    current_chunk = ""
            else:
                current_chunk = p

    if current_chunk and current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

def score_chunk(chunk: str, query_tokens: set, focus_tokens: set) -> float:
    """计算单个段落的相关性与信息密度综合得分"""
    chunk_lower = chunk.lower()
    chunk_tokens = set(tokenize_text(chunk_lower))
    
    if not chunk_tokens:
        return 0.0

    # 1. 查询词与关注点匹配度 (BM25-like TF-IDF 简化权重)
    q_match = len(query_tokens.intersection(chunk_tokens))
    f_match = len(focus_tokens.intersection(chunk_tokens))
    
    base_overlap = (q_match * 2.5 + f_match * 1.5) / (math.sqrt(len(chunk_tokens)) + 1.0)

    # 2. 量化数据与数字特征加权 (百分比、数值、年份、币种等)
    num_matches = len(re.findall(r'\d+(?:\.\d+)?%?|\$|¥|€|元|亿|万', chunk))
    numeric_bonus = min(num_matches * 0.15, 1.5)

    # 3. 结构化表格加权 (表格通常包含密集指标)
    table_bonus = 1.0 if "|" in chunk and "---" in chunk else 0.0

    # 4. 核心结论与发现指示词加权
    indicator_count = sum(1 for term in CONCLUSION_INDICATORS if term in chunk_lower)
    indicator_bonus = min(indicator_count * 0.2, 1.2)

    # 5. 长度规范化 (过滤过短的噪音片段)
    length_multiplier = 0.5 if len(chunk) < 80 else 1.0

    total_score = (base_overlap + numeric_bonus + table_bonus + indicator_bonus) * length_multiplier
    return total_score

def rerank_chunks(
    chunks: List[str],
    query: str,
    focus: str = "",
    top_k: int = 3
) -> List[str]:
    """
    目标导向段落局部重排序 (Paragraph Reranker)。
    以当前章节 Focus 与 Query 为指引，精准召回最具证据价值与量化密度的 Top-K 核心段落。
    """
    if not chunks:
        return []
    if len(chunks) <= top_k:
        return chunks

    q_tokens = set(tokenize_text(query))
    f_tokens = set(tokenize_text(focus))

    scored_items: List[Tuple[float, int, str]] = []
    for idx, chunk in enumerate(chunks):
        score = score_chunk(chunk, q_tokens, f_tokens)
        scored_items.append((score, idx, chunk))

    # 按相关度降序，若得分相同保留原顺序
    scored_items.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    # 截取 Top-K 并按在原文中出现的相对顺序重新排列，保持阅读连贯性
    selected = scored_items[:top_k]
    selected.sort(key=lambda x: x[1])

    return [item[2] for item in selected]

def compute_rrf_score(
    ranks: Dict[str, Optional[int]],
    weights: Optional[Dict[str, float]] = None,
    k: int = 60
) -> float:
    """
    倒数排名融合算法 (Reciprocal Rank Fusion - RRF)。
    RRF_Score(d) = Σ [ w_s / (k + rank_s(d)) ]
    """
    weights = weights or {}
    total_score = 0.0
    for source_name, rank in ranks.items():
        if rank is not None and rank > 0:
            w = weights.get(source_name, 1.0)
            total_score += w / (k + rank)
    return total_score

def fuse_ranked_lists(
    ranked_lists_with_weights: List[Tuple[List[Dict[str, Any]], float]],
    id_key: str = "id",
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    对多源检索列表（如本地私有切片与全网网络切片）执行 RRF 混合加权融合排序。
    """
    doc_map: Dict[str, Dict[str, Any]] = {}
    doc_ranks: Dict[str, Dict[str, int]] = {}
    source_weights: Dict[str, float] = {}

    for s_idx, (doc_list, weight) in enumerate(ranked_lists_with_weights):
        source_name = f"source_{s_idx}"
        source_weights[source_name] = weight
        for rank_1_based, doc in enumerate(doc_list, start=1):
            doc_id = str(doc.get(id_key, doc.get("text", "")[:40]))
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
                doc_ranks[doc_id] = {}
            doc_ranks[doc_id][source_name] = rank_1_based

    # 计算各文档的 RRF 得分
    scored_docs = []
    for doc_id, doc in doc_map.items():
        ranks = doc_ranks[doc_id]
        score = compute_rrf_score(ranks, weights=source_weights, k=k)
        doc_copy = dict(doc)
        doc_copy["rrf_score"] = score
        scored_docs.append((score, doc_copy))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_docs]
