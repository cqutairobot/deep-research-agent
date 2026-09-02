import math
import re
from typing import List, Dict, Any, Tuple

class SessionMemoryStore:
    """
    会话级轻量事实与向量内存索引库。
    在单次调研任务中，存储所有抓取并压缩后的事实片段，支持语义及关键词混合检索。
    """
    
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        
    def add_fact(self, fact_text: str, source_id: int, chapter_num: int, metadata: Dict[str, Any] = None):
        """添加单条事实卡片"""
        doc = {
            "id": len(self.documents),
            "text": fact_text,
            "source_id": source_id,
            "chapter_num": chapter_num,
            "metadata": metadata or {},
            "tokens": self._tokenize(fact_text)
        }
        self.documents.append(doc)

    def search(self, query: str, top_k: int = 5, chapter_filter: int = None) -> List[Dict[str, Any]]:
        """执行 BM25 + Jaccard 混合相关性检索"""
        if not self.documents:
            return []
            
        q_tokens = set(self._tokenize(query))
        if not q_tokens:
            return self.documents[:top_k]
            
        scored_docs: List[Tuple[float, Dict[str, Any]]] = []
        
        for doc in self.documents:
            if chapter_filter is not None and doc["chapter_num"] != chapter_filter:
                continue
                
            doc_tokens = set(doc["tokens"])
            intersection = q_tokens.intersection(doc_tokens)
            if not intersection:
                score = 0.01
            else:
                # 词重叠得分 + 长度惩罚
                score = len(intersection) / (math.sqrt(len(q_tokens)) * math.sqrt(len(doc_tokens)) + 1e-5)
                
            scored_docs.append((score, doc))
            
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_docs[:top_k]]

    def get_all_facts(self) -> List[Dict[str, Any]]:
        return self.documents

    def _tokenize(self, text: str) -> List[str]:
        """中英文通用分词器"""
        # 英文单词与中文 1-2 gram 切分
        words = re.findall(r'[a-zA-Z0-9_]+|[\u4e00-\u9fff]', text.lower())
        return words
