"""
OCR Fallback 功能测试
测试智能 PDF 识别增强功能
"""

import pytest
from pathlib import Path
from utils.file_ops import should_use_ocr, extract_text_preview_enhanced, is_important_document


class TestOcrFallback:
    """OCR Fallback 功能测试类"""
    
    def test_should_use_ocr_empty_text(self):
        """空文本应触发 OCR"""
        needs_ocr, reason = should_use_ocr("", page_count=1)
        assert needs_ocr is True
        assert "空" in reason or "扫描" in reason
    
    def test_should_use_ocr_low_density(self):
        """低密度文本应触发 OCR"""
        # 50 chars for 5 pages = 10 chars/page (< 100 threshold)
        text = "Page\n" * 10
        needs_ocr, reason = should_use_ocr(text, page_count=5)
        assert needs_ocr is True
        assert "密度" in reason or "字符" in reason
    
    def test_should_use_ocr_whitespace_heavy(self):
        """空白符过多应触发 OCR"""
        # 90% whitespace
        text = " " * 900 + "text" * 25  # 925 chars total, 900 spaces
        needs_ocr, reason = should_use_ocr(text, page_count=1)
        assert needs_ocr is True
        assert "空白" in reason
    
    def test_should_use_ocr_garbage_text(self):
        """乱码比例高应触发 OCR"""
        # Random garbage characters
        text = "��������������" * 100  # 大量乱码
        needs_ocr, reason = should_use_ocr(text, page_count=1)
        assert needs_ocr is True
        assert "乱码" in reason
    
    def test_should_not_use_ocr_normal_pdf(self):
        """正常 PDF 不应触发 OCR"""
        # Normal text with sufficient density
        text = "This is a normal PDF document with plenty of text content. " * 100
        needs_ocr, reason = should_use_ocr(text, page_count=2)
        assert needs_ocr is False
        assert "正常" in reason
    
    def test_is_important_document_with_keyword(self):
        """包含关键词的文档应被标记为重要"""
        # 创建临时文件路径（不需要实际存在）
        test_path = Path("test_invoice_2024.pdf")
        
        # 注意：这个测试需要模拟文件大小和页数
        # 在实际测试中，可能需要创建真实的测试文件
        # 这里只测试逻辑，不测试实际文件操作
        
    def test_is_important_document_without_keyword(self):
        """不包含关键词的文档不应被标记为重要"""
        test_path = Path("random_file_12345.pdf")
        # 同样需要实际文件进行完整测试


class TestExtractTextPreviewEnhanced:
    """增强版文本提取测试"""
    
    @pytest.mark.skipif(
        not Path("inbox/test.pdf").exists(),
        reason="需要测试 PDF 文件"
    )
    def test_extract_with_direct_method(self):
        """测试标准提取方法"""
        test_pdf = Path("inbox/test.pdf")
        if test_pdf.exists():
            result = extract_text_preview_enhanced(test_pdf)
            
            assert "text" in result
            assert "method" in result
            assert "confidence" in result
            assert result["method"] in ["direct", "rapidocr", "vision_llm", "direct_fallback"]
            assert 0 <= result["confidence"] <= 1.0
    
    def test_extract_result_structure(self):
        """测试返回结果的结构"""
        # 这个测试需要一个测试文件
        # 可以使用 pytest 的 tmp_path 创建临时文件
        pass
    
    @pytest.mark.asyncio
    async def test_vision_llm_integration(self):
        """测试 Vision LLM 集成（需要 API Key）"""
        # 这个测试需要配置 API Key 和测试文件
        # 可以使用 pytest.skip 跳过没有 API Key 的情况
        pytest.skip("需要配置 Vision LLM API Key")


class TestIntegration:
    """集成测试"""
    
    def test_full_pipeline_with_scanned_pdf(self):
        """测试完整的扫描 PDF 处理流程"""
        # 1. 准备扫描型 PDF（需要测试资源）
        # 2. 调用 extract_text_preview_enhanced
        # 3. 验证 OCR 被触发
        # 4. 验证文本质量
        pytest.skip("需要准备扫描型 PDF 测试资源")
    
    def test_fallback_chain(self):
        """测试 fallback 链：Vision LLM -> RapidOCR -> Direct"""
        pytest.skip("需要模拟各种失败场景")


# 运行测试的辅助函数
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

