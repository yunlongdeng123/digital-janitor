"""
文件计划校验器模块
对重命名计划进行安全性和有效性校验
"""

import re
from pathlib import Path
from typing import List

from core.schemas import RenamePlan


# Windows 文件名非法字符
INVALID_WIN_CHARS = r'<>:"/\\|?*'
INVALID_CHARS_PATTERN = re.compile(f"[{re.escape(INVALID_WIN_CHARS)}]")


def sanitize_filename(filename: str) -> str:
    """
    清理文件名中的非法字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        清理后的文件名
    """
    # 移除 Windows 非法字符，替换为下划线
    cleaned = INVALID_CHARS_PATTERN.sub("_", filename)
    
    # 去除首尾空格
    cleaned = cleaned.strip()
    
    # 去除首尾的点号（Windows 不允许）
    cleaned = cleaned.strip(".")
    
    # 如果清理后为空，返回默认名称
    if not cleaned:
        cleaned = "unnamed"
    
    return cleaned


def is_safe_path(path_str: str) -> tuple[bool, str]:
    """
    检查路径是否安全（防止目录穿越攻击）
    
    Args:
        path_str: 路径字符串
    
    Returns:
        (is_safe, error_message) 元组
    """
    try:
        # 0. 预处理
        s = path_str.strip()
        
        # 1. 拦截 Windows 盘符 (如 C:, d:) 和 UNC 路径 (//, \\)
        # 建议 #5 的修复
        if re.match(r'^[a-zA-Z]:', s):
            return False, "路径包含盘符，必须使用相对路径"
        if s.startswith(("\\\\", "//")):
            return False, "禁止使用 UNC 网络路径"
            
        path = Path(s)
        
        # 2. 检查是否包含 ".." (父目录引用)
        if ".." in path.parts:
            return False, "路径包含 '..' 父目录引用，存在安全风险"
        
        # 3. 检查是否为绝对路径（必须是相对路径）
        if path.is_absolute():
            return False, "路径必须是相对路径，不能使用绝对路径"
        
        # 4. 检查路径是否包含非法字符
        # 统一转为 posix 风格检查
        path_str_normalized = str(path).replace("\\", "/")
        for char in '<>"|?*':
            if char in path_str_normalized:
                return False, f"路径包含非法字符: '{char}'"
        
        # 5. 再次拦截危险前缀（双重保险）
        dangerous_prefixes = ["/", "\\"]
        for prefix in dangerous_prefixes:
            if s.startswith(prefix):
                return False, f"路径不能以 '{prefix}' 开头"
        
        return True, ""
        
    except Exception as e:
        return False, f"路径解析失败: {str(e)}"


def validate_plan(plan: RenamePlan) -> RenamePlan:
    """
    校验重命名计划的安全性和有效性
    
    校验规则：
    1. new_name: 移除 Windows 非法字符，去除首尾空格
    2. dest_dir: 必须是相对路径，不能包含 ".."（防止目录穿越）
    3. 如果校验通过，设置 is_valid = True；否则设为 False 并填写 validation_msg
    
    Args:
        plan: 待校验的重命名计划
    
    Returns:
        更新后的 RenamePlan 对象（带校验结果）
    """
    errors: List[str] = []
    
    # 1. 校验并清理 new_name
    original_name = plan.new_name
    cleaned_name = sanitize_filename(original_name)
    
    if cleaned_name != original_name:
        # 文件名被修改，记录警告但不算错误
        plan.new_name = cleaned_name
        if not cleaned_name:
            errors.append(f"文件名无效: '{original_name}' -> 清理后为空")
    
    # 检查文件名长度（Windows 路径限制）
    if len(cleaned_name) > 255:
        errors.append(f"文件名过长: {len(cleaned_name)} 字符 (最大 255)")
    
    # 检查文件名是否为保留名称（Windows）
    reserved_names = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    name_without_ext = Path(cleaned_name).stem.upper()
    if name_without_ext in reserved_names:
        errors.append(f"文件名使用了 Windows 保留名称: {name_without_ext}")
    
    # 2. 校验 dest_dir
    is_safe, error_msg = is_safe_path(plan.dest_dir)
    if not is_safe:
        errors.append(f"目标路径不安全: {error_msg}")
    
    # 3. 设置校验结果
    if errors:
        plan.is_valid = False
        plan.validation_msg = "; ".join(errors)
    else:
        plan.is_valid = True
        plan.validation_msg = "校验通过"
    
    return plan


def validate_plans_batch(plans: List[RenamePlan]) -> List[RenamePlan]:
    """
    批量校验重命名计划
    
    Args:
        plans: 重命名计划列表
    
    Returns:
        校验后的计划列表
    """
    return [validate_plan(plan) for plan in plans]


def get_validation_stats(plans: List[RenamePlan]) -> dict:
    """
    获取校验统计信息
    
    Args:
        plans: 已校验的计划列表
    
    Returns:
        统计信息字典
    """
    total = len(plans)
    valid = sum(1 for p in plans if p.is_valid)
    invalid = total - valid
    
    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "valid_rate": valid / total if total > 0 else 0.0,
        "invalid_plans": [
            {
                "file": p.new_name,
                "reason": p.validation_msg
            }
            for p in plans if not p.is_valid
        ]
    }

