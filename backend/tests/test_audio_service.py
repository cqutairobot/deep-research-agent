import pytest
import asyncio
from app.services.audio_service import clean_text_for_tts, extract_podcast_script, generate_audio_bytes


def test_audio_text_cleaning():
    """断言：音频合成前必须彻底清除 Markdown 语法标号、表格与 Mermaid 代码块，避免杂音。"""
    raw_md = """
    # 核心大标题
    本方案经过实测验证。详见对比表：
    | 方案 | 达标率 |
    |---|---|
    | A | 95% |
    
    ```mermaid
    graph LR
        A --> B
    ```
    
    公式参考：$$E = mc^2$$ 以及 $P(y|x)$，另外见引用 [^cite:1] 与 [2]。
    综上所述，建议加速量产。
    """
    clean_text = clean_text_for_tts(raw_md)
    assert "#" not in clean_text
    assert "|" not in clean_text
    assert "mermaid" not in clean_text
    assert "graph LR" not in clean_text
    assert "$$" not in clean_text
    assert "cite:1" not in clean_text
    assert "本方案经过实测验证" in clean_text
    assert "建议加速量产" in clean_text


def test_podcast_script_extraction():
    """断言：广播脚本提取包含课题大标题、核心发现与感谢收听结语"""
    report_md = """
    # 2026 低空经济深度研究
    
    ## 执行摘要
    低空空域适航审定加速推进，各主机厂进入规模化验证期。
    
    ## 第 1 章：产业政策
    政策大力扶持低空空域开放。
    
    ## 第 2 章：商业化路线
    优先探索景区观光与城际物流。
    """
    script = extract_podcast_script("2026 低空经济深度研究", report_md)
    assert "低空经济" in script
    assert "执行摘要" in script or "核心发现" in script or "适航审定" in script
    assert "感谢" in script
    assert "#" not in script


@pytest.mark.asyncio
async def test_audio_generation_mock_or_cached(monkeypatch):
    """测试音频二进制流生成与本地缓存"""
    # 模拟 edge_tts.Communicate 行为，避免受外网波动干扰测试稳定性
    class MockCommunicate:
        def __init__(self, text, voice):
            self.text = text
            self.voice = voice
            
        async def stream(self):
            yield {"type": "audio", "data": b"ID3\x03\x00\x00\x00fake_mp3_data_payload_stream"}
            
    monkeypatch.setattr("edge_tts.Communicate", MockCommunicate)
    audio_data = await generate_audio_bytes("这是一段播客测试音频", voice="zh-CN-YunxiNeural")
    assert isinstance(audio_data, bytes)
    assert len(audio_data) > 0
    assert b"ID3" in audio_data or b"fake_mp3" in audio_data
