"""
Core 核心模块
包含 LLM 处理和数据结构定义
"""

from core.schemas import FileAnalysis, RenamePlan
from core.validator import validate_plan, validate_plans_batch, get_validation_stats

# 延迟导入 llm_processor，避免在没有安装 langchain 时导入失败
try:
    from core.llm_processor import analyze_file
    __all__ = [
        "FileAnalysis", 
        "RenamePlan",
        "analyze_file",
        "validate_plan",
        "validate_plans_batch",
        "get_validation_stats"
    ]
except ImportError:
    # 如果 langchain 未安装，只导出 schemas 和 validator
    __all__ = [
        "FileAnalysis",
        "RenamePlan", 
        "validate_plan",
        "validate_plans_batch",
        "get_validation_stats"
    ]

__version__ = "0.1.0"

