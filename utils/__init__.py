"""
Utils 工具模块
"""

from utils.file_ops import (
    discover_files,
    extract_text_preview,
    get_file_size_mb,
    is_allowed_extension
)

__all__ = [
    "discover_files",
    "extract_text_preview",
    "get_file_size_mb",
    "is_allowed_extension"
]

__version__ = "0.1.0"

