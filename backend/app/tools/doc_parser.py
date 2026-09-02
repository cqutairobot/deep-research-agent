import io
import re
from typing import List, Dict, Any

def parse_uploaded_document(file_name: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    解析用户上传的本地文档 (.pdf, .docx, .txt, .md)，提取纯文本与语义切片
    """
    ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
    full_text = ""

    try:
        if ext in ['txt', 'md']:
            full_text = file_bytes.decode('utf-8', errors='ignore')
        elif ext == 'pdf':
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    pages_text.append(f"[第 {i+1} 页] {txt.strip()}")
            full_text = "\n\n".join(pages_text)
        elif ext in ['docx', 'doc']:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs)
        else:
            full_text = file_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[DocParser Error] 解析文件 {file_name} 失败: {e}")
        full_text = f"（文件 {file_name} 解析部分异常）"

    # 清洗文本
    clean_text = re.sub(r'\r\n', '\n', full_text)
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()

    # 语义切片
    chunks = chunk_text(clean_text, chunk_size=500)

    return {
        "file_name": file_name,
        "extension": ext,
        "char_count": len(clean_text),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "full_text": clean_text
    }

def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """
    按段落、标点或固定步长进行语义切片
    """
    if not text:
        return []
    
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
            
        if len(current_chunk) + len(p) <= chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + p
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
                
            if len(p) > chunk_size:
                # 尝试按标点断句
                sentences = re.split(r'([。！？\.\!\?\n])', p)
                sub_chunk = ""
                for s in sentences:
                    if not s:
                        continue
                    if len(sub_chunk) + len(s) <= chunk_size:
                        sub_chunk += s
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        if len(s) > chunk_size:
                            # 极端长字符串按固定窗口强行切分
                            for i in range(0, len(s), chunk_size):
                                chunks.append(s[i:i+chunk_size])
                            sub_chunk = ""
                        else:
                            sub_chunk = s
                if sub_chunk:
                    current_chunk = sub_chunk
            else:
                current_chunk = p

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
