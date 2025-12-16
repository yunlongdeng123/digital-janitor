"""
OCR 相关配置
用于智能 PDF 识别增强功能
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class OcrConfig:
    """OCR 相关配置"""
    
    # RapidOCR 配置
    rapidocr_max_pages: int = 10
    rapidocr_min_confidence: float = 0.5
    rapidocr_dpi: int = 200
    
    # Vision LLM 配置
    vision_max_pages: int = 3
    vision_dpi: int = 150
    vision_model: str = "Qwen/Qwen3-VL-30B-A3B-Thinking"
    
    # 触发阈值
    ocr_trigger_chars_per_page: int = 100
    ocr_trigger_garbage_ratio: float = 0.3
    
    # 重要文档判断
    important_keywords: List[str] = field(default_factory=lambda: [
        'invoice', '发票', 'contract', '合同', 
        'report', '报告', 'statement', '对账单',
        '协议', 'agreement', '证明', 'certificate'
    ])
    important_min_size_kb: int = 100
    important_max_size_kb: int = 10_000
    important_max_pages: int = 5
    
    # 性能控制
    enable_vision_llm: bool = True  # 是否启用 Vision LLM（成本控制）
    enable_rapidocr: bool = True    # 是否启用 RapidOCR
    
    # 调试选项
    save_debug_images: bool = False  # 是否保存调试图片
    debug_image_dir: str = "logs/ocr_debug"


# 全局配置实例
OCR_CONFIG = OcrConfig()


def update_ocr_config(**kwargs):
    """
    更新 OCR 配置
    
    示例：
        update_ocr_config(
            rapidocr_max_pages=20,
            enable_vision_llm=False
        )
    """
    global OCR_CONFIG
    for key, value in kwargs.items():
        if hasattr(OCR_CONFIG, key):
            setattr(OCR_CONFIG, key, value)
        else:
            raise ValueError(f"未知的配置项: {key}")

