#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Digital Janitor - LangGraph 工作流版

核心功能：
- 🔄 LangGraph 状态图工作流
- 🤝 HITL (Human-in-the-Loop) 人工确认
- 📦 真实文件移动 + 冲突处理
- 📝 完整日志追踪

Step 6 重构：
- 封装 JanitorWorkflow 类，使核心逻辑可被外部调用
- 既可作为命令行工具运行，也可作为库被导入

使用方式：
    1. 命令行模式：
       python run_graph_once.py --limit 5 --execute
    
    2. 作为库导入：
       from run_graph_once import JanitorWorkflow
       workflow = JanitorWorkflow()
       result = workflow.process_file(Path("inbox/doc.pdf"))
"""

from __future__ import annotations

import sys
import json
import argparse
import re
import os
from pathlib import Path
from datetime import datetime
from typing import TypedDict, Optional, Dict, Any

# 设置 UTF-8 编码支持 (Windows 控制台)
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

import yaml
from dotenv import load_dotenv

# LangGraph 核心组件
from langgraph.graph import StateGraph, END

# 项目内部模块
from core.schemas import RenamePlan
from core.validator import validate_plan
from utils.file_ops import discover_files, extract_text_preview_enhanced, get_file_size_mb, safe_move_file
from core.llm_processor import analyze_file

# Memory 系统
from core.memory import MemoryDatabase, ApprovalRepository, PreferenceRepository
import hashlib

# --- 辅助函数：PR#2 三级路由策略 ---

# 类别中文映射表
CAT_CN_MAP = {
    "invoice": "发票",
    "receipt": "票据",
    "bank_statement": "银行账单",
    "contract": "合同",
    "paper": "论文",
    "image": "图片",
    "presentation": "演示文稿",
    "default": "其他",
}

# 无效 Vendor 值列表（大小写不敏感）
INVALID_VENDOR_VALUES = {"", "unknown", "n/a", "none", "无", "未知", "null"}


def sanitize_path_component(value: str) -> str:
    """
    清洗路径组件，移除非法字符
    
    Args:
        value: 原始值（如 vendor 名称）
    
    Returns:
        安全的路径组件字符串
    """
    if not value:
        return ""
    # 替换 Windows/Unix 路径非法字符
    illegal_chars = r'[/\\:*?"<>|]'
    sanitized = re.sub(illegal_chars, '_', value)
    # 移除首尾空格和点（Windows 不允许文件夹名以点结尾）
    sanitized = sanitized.strip().rstrip('.')
    return sanitized


def is_valid_vendor(vendor: Optional[str]) -> bool:
    """
    检查 vendor 是否有效
    
    Args:
        vendor: 供应商/对方名称
    
    Returns:
        True 如果 vendor 有效，False 否则
    """
    if vendor is None:
        return False
    vendor_lower = vendor.strip().lower()
    return vendor_lower not in INVALID_VENDOR_VALUES


def build_date_partition_path(category: str, date_str: Optional[str]) -> str:
    """
    构建日期分层路径 (Category/YYYY/MM)
    
    用于财务类文档（发票、票据、银行账单）的归档。
    
    Args:
        category: 文档类别
        date_str: 提取的日期字符串 (格式: YYYY-MM 或 YYYY-MM-DD)
    
    Returns:
        目标目录路径，如 "发票/2024/12"
    """
    # 获取中文类别名
    cat_cn = CAT_CN_MAP.get(category, CAT_CN_MAP["default"])
    
    # 解析日期
    year, month = "未知年份", "未知月份"
    if date_str:
        m = re.match(r"(?P<y>20\d{2})[-./]?(?P<m>\d{2})?", date_str)
        if m:
            year = m.group("y")
            month = m.group("m") if m.group("m") else "01"
    
    return f"{cat_cn}/{year}/{month}"


def build_semantic_path(
    category: str, 
    vendor: Optional[str],
    default_tpl: str = "{category}/{vendor}",
    fallback_tpl: str = "{category}/General"
) -> str:
    """
    构建语义化路径 (Category/Vendor)
    
    用于非财务类文档（合同、论文等）的归档。
    
    Args:
        category: 文档类别
        vendor: 供应商/对方/作者名称
        default_tpl: 默认模板 (当 vendor 有效时使用)
        fallback_tpl: 兜底模板 (当 vendor 无效时使用)
    
    Returns:
        目标目录路径，如 "合同/腾讯科技" 或 "合同/General"
    """
    # 获取中文类别名
    cat_cn = CAT_CN_MAP.get(category, CAT_CN_MAP["default"])
    
    # 检查 vendor 有效性
    if is_valid_vendor(vendor):
        # 使用默认模板
        safe_vendor = sanitize_path_component(vendor)
        return default_tpl.format(category=cat_cn, vendor=safe_vendor)
    else:
        # 使用兜底模板
        return fallback_tpl.format(category=cat_cn)


# --- 1. 定义状态 (State) ---
class JanitorState(TypedDict, total=False):
    """定义工作流中流转的数据结构"""
    # 输入
    file_path: Path           # 文件路径
    cfg: dict                 # 配置字典
    archive_root: Path        # 归档根目录
    dry_run: bool             # 是否是Dry-Run
    max_preview: int          # 最大预览字符数
    auto_approve: bool        # 自动批准模式（用于测试/演示）
    preference_repo: Any      # 🆕 偏好仓库

    # 中间产物
    preview: str              # 预览文本
    extraction_metadata: Dict[str, Any]  # 🆕 OCR V2: 文本提取元数据 (method, confidence, quality_score, needs_review, processing_time_ms)
    analysis: Dict[str, Any]  # 存储 LLM 分析的原始结果
    plan: RenamePlan          # 核心对象：重命名计划

    # 🆕 HITL 决策相关
    approved: bool            # 是否批准执行
    decision: str             # 决策类型：approved / rejected / auto_reject_invalid / skipped / pending

    # 🆕 Step 5: 文件移动相关
    move_result: Dict[str, Any]  # 文件移动结果

    # 🆕 Step 7: 待审批相关
    pending_file: str         # 待审批 JSON 文件路径

    # 🆕 PR#2: 路由策略相关
    routing_source: str       # 路由来源: memory / date_partition / semantic
    used_learned_preference: bool  # 是否使用了学习到的偏好

    # 输出/日志
    record: Dict[str, Any]    # 记录
    error: str                # 错误信息


# --- 2. 定义节点 (Nodes) ---

def node_extract_preview(state: JanitorState) -> JanitorState:
    """节点1: 提取文本预览（OCR V2 增强版）"""
    fp = state["file_path"]  # 获取文件路径
    max_preview = state.get("max_preview", 1000)
    
    # 🆕 OCR V2: 使用增强版文本提取
    result = extract_text_preview_enhanced(fp, limit=max_preview)
    
    # 提取文本内容
    state["preview"] = result.get("text", "")
    
    # 🆕 OCR V2: 保存元数据（排除 text 字段）
    state["extraction_metadata"] = {
        "method": result.get("method", "unknown"),
        "confidence": result.get("confidence", 0.0),
        "quality_score": result.get("quality_score", 0),
        "needs_review": result.get("needs_review", False),
        "processing_time_ms": result.get("processing_time_ms", 0),
        "page_count": result.get("page_count", 0),
        "char_count": result.get("char_count", 0),
        "error": result.get("error"),
    }
    
    # 🆕 打印简短日志
    method = state["extraction_metadata"]["method"]
    quality = state["extraction_metadata"]["quality_score"]
    time_ms = state["extraction_metadata"]["processing_time_ms"]
    cached = "_cached" in method
    
    print(f"   📄 文本提取: {method} | 质量={quality} | 耗时={time_ms}ms" + (" 💾" if cached else ""))
    
    # 如果质量较低，打印警告
    if state["extraction_metadata"]["needs_review"]:
        print(f"   ⚠️  OCR 质量较低 ({quality}分)，可能需要人工审查")
    
    return state


def node_llm_analyze(state: JanitorState) -> JanitorState:
    """节点2: 调用 LLM 分析"""
    fp = state["file_path"]
    try:
        # 调用核心模块
        a = analyze_file(state.get("preview", ""), fp.name, max_preview=state.get("max_preview", 1000))
        
        # 将 Pydantic 对象转为 Dict 存入 State (方便序列化)
        state["analysis"] = {
            "category": a.category,
            "confidence": a.confidence,
            "suggested_filename": a.suggested_filename,
            "extracted_date": a.extracted_date,
            "extracted_amount": a.extracted_amount,
            "vendor_or_party": a.vendor_or_party,
            "title": a.title,
            "rationale": a.rationale,
        }
    except Exception as e:
        state["error"] = f"LLM 分析失败: {e}"
    return state


def node_build_plan(state: JanitorState) -> JanitorState:
    """
    节点3: 构建重命名计划 (RenamePlan)
    
    PR#2: 实现三级路由优先级
      1. Memory 偏好 (最高) - 从用户历史操作中学习
      2. 日期分层规则 - 财务类文档按 Category/YYYY/MM
      3. 语义化归档 - 其他文档按 Category/Vendor
    """
    fp = state["file_path"]
    cfg = state["cfg"]

    # 如果之前的步骤报错，生成一个失败的计划
    if state.get("error"):
        plan = RenamePlan(
            category="error",
            new_name=fp.name,
            dest_dir="quarantine/failed",
            confidence=0.0,
            extracted={},
            rationale=state["error"],
            is_valid=False,
            validation_msg=state["error"],
        )
        state["plan"] = plan
        state["routing_source"] = "error"
        return state

    # 正常构建逻辑
    a = state["analysis"]
    category = a["category"]
    vendor = a.get("vendor_or_party")
    date_str = a.get("extracted_date")
    
    # 读取路由配置
    routing_cfg = cfg.get("routing", {})
    date_partition_types = routing_cfg.get("date_partition_types", ["invoice", "receipt", "bank_statement"])
    default_structure = routing_cfg.get("default_structure", "{category}/{vendor}")
    fallback_structure = routing_cfg.get("fallback_structure", "{category}/General")
    
    # === 三级路由优先级 ===
    
    # 1️⃣ 优先级 1: Memory 偏好 (最高)
    learned_folder = None
    if "preference_repo" in state and state["preference_repo"]:
        try:
            context = {
                'vendor': vendor,
                'doc_type': category
            }
            learned_folder = state["preference_repo"].get_preference(
                'vendor_folder',
                context,
                min_confidence=0.7
            )
        except Exception:
            pass  # 失败不影响主流程
    
    if learned_folder:
        # Memory 偏好命中
        target_dir_rel = learned_folder
        state["routing_source"] = "memory"
        state["used_learned_preference"] = True
        print(f"   🧠 路由: Memory 偏好命中 -> {target_dir_rel}")
    else:
        state["used_learned_preference"] = False
        
        # 2️⃣ 优先级 2: 日期分层规则 (财务类文档)
        if category in date_partition_types:
            target_dir_rel = build_date_partition_path(category, date_str)
            state["routing_source"] = "date_partition"
            print(f"   📅 路由: 日期分层 ({category}) -> {target_dir_rel}")
        else:
            # 3️⃣ 优先级 3: 语义化归档 (非财务类文档)
            target_dir_rel = build_semantic_path(
                category=category,
                vendor=vendor,
                default_tpl=default_structure,
                fallback_tpl=fallback_structure
            )
            state["routing_source"] = "semantic"
            if is_valid_vendor(vendor):
                print(f"   🏷️  路由: 语义化 ({category}/{vendor}) -> {target_dir_rel}")
            else:
                print(f"   📁 路由: 语义化兜底 ({category}/General) -> {target_dir_rel}")

    # 扩展名处理
    ext = fp.suffix
    suggested = a["suggested_filename"]
    # 如果建议名不包含扩展名，补上
    if ext and (not suggested.lower().endswith(ext.lower())):
        new_name = f"{suggested}{ext.lower()}"
    else:
        new_name = suggested

    # 创建 Pydantic 对象
    plan = RenamePlan(
        category=category,
        new_name=new_name,
        dest_dir=target_dir_rel,
        confidence=a["confidence"],
        extracted={
            "date": date_str,
            "amount": a.get("extracted_amount"),
            "vendor_or_party": vendor,
            "title": a.get("title"),
        },
        rationale=a.get("rationale", ""),
    )
    state["plan"] = plan
    return state


def node_validate(state: JanitorState) -> JanitorState:
    """节点4: 安全校验"""
    # 复用 core.validator
    state["plan"] = validate_plan(state["plan"])
    return state


def node_human_review(state: JanitorState) -> JanitorState:
    """节点4.5: 人类在环确认（HITL）- Step 7 非阻塞式审批 + OCR V2 质量熔断"""
    fp = state["file_path"]
    plan = state["plan"]

    # 1) 不合法：自动拒绝，不询问
    if not plan.is_valid:
        state["approved"] = False
        state["decision"] = "auto_reject_invalid"
        return state

    # 2) 合法：打印摘要
    print(f"\n🧑‍⚖️  需要确认：{fp.name}")
    print(f"   → 新名字：{plan.new_name}")
    print(f"   → 目标目录：{plan.dest_dir}")
    print(f"   → 类别/置信度：{plan.category} / {float(plan.confidence):.2f}")
    
    # 🆕 OCR V2: 检查 OCR 质量熔断
    extraction_metadata = state.get("extraction_metadata", {})
    ocr_needs_review = extraction_metadata.get("needs_review", False)
    ocr_quality_score = extraction_metadata.get("quality_score", 100)
    
    # 🆕 Step 7: 非阻塞式审批机制
    auto_approve = state.get("auto_approve", False)
    
    # 🆕 OCR V2 质量熔断：如果 OCR 质量低，强制转为人工审批
    if ocr_needs_review:
        print(f"   ⚠️  OCR 质量低 ({ocr_quality_score}分)，强制转为人工审批")
        auto_approve = False  # 强制关闭自动批准
    
    if auto_approve:
        # 自动批准模式：立即批准
        print("   🤖 自动批准模式：已批准")
        state["approved"] = True
        state["decision"] = "approved"
    else:
        # 非自动批准模式：保存为待审批 JSON
        import json
        from datetime import datetime
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
        safe_filename = fp.stem.replace(" ", "_")[:30]  # 限制长度，避免路径过长
        pending_filename = f"plan_{timestamp}_{safe_filename}.json"
        pending_path = Path("pending") / pending_filename
        
        # 构建待审批数据
        pending_data = {
            "original_file": str(fp),
            "original_name": fp.name,
            "new_name": plan.new_name,
            "dest_dir": plan.dest_dir,
            "category": plan.category,
            "confidence": float(plan.confidence),
            "extracted": plan.extracted,
            "rationale": plan.rationale,
            "preview": state.get("preview", "")[:500],  # 保存前500字符预览
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            # 🆕 OCR V2: 记录质量问题标记
            "ocr_quality_issue": ocr_needs_review,
            "ocr_quality_score": ocr_quality_score,
            "extraction_method": extraction_metadata.get("method", "unknown"),
        }
        
        # 保存到 JSON 文件
        with pending_path.open("w", encoding="utf-8") as f:
            json.dump(pending_data, f, ensure_ascii=False, indent=2)
        
        print(f"   ⏳ 计划已生成，等待 UI 审批")
        print(f"      文件：{pending_filename}")
        
        # 🆕 OCR V2: 如果是因为 OCR 质量问题导致的人工审批，额外提示
        if ocr_needs_review:
            print(f"      ⚠️  原因：OCR 质量低 ({ocr_quality_score}分)")
        
        # 设置为 pending 状态（不执行，也不拒绝）
        state["approved"] = False
        state["decision"] = "pending"
        state["pending_file"] = str(pending_path)
    
    return state


def node_apply(state: JanitorState) -> JanitorState:
    """节点5a: 执行（批准后）"""
    fp = state["file_path"]
    plan = state["plan"]
    archive_root = state["archive_root"]

    # 再保险：如果没批准，直接返回
    if not state.get("approved", False):
        return state

    # 🆕 Step 5: 区分 Dry-run 和真实执行
    if state.get("dry_run", True):
        # Dry-run 模式：只打印，不动文件
        print(f"   🧪 Dry-run 批准：将把 {fp.name} → {plan.new_name}")
        print(f"      移动到 {plan.dest_dir}\n")
        
        execution_status = "dry_run"
        moved_to = None
        
    else:
        # 🆕 真实执行模式：实际移动文件
        # 构建完整的目标路径
        dst = archive_root / plan.dest_dir / plan.new_name
        
        # 调用 safe_move_file 执行移动
        move_result = safe_move_file(fp, dst)
        state["move_result"] = move_result
        
        if move_result["status"] == "success":
            # 移动成功
            execution_status = "success"
            moved_to = move_result["dst"]
            
            print(f"   📦 已移动：{fp.name}")
            print(f"      → {moved_to}")
            
            # 如果发生了冲突解决
            if move_result.get("conflict_resolved", False):
                final_name = Path(moved_to).name
                print(f"      ⚠️  检测到冲突，已重命名为 {final_name}")
            
            print()
        else:
            # 移动失败
            execution_status = "failed"
            moved_to = None
            
            print(f"   ❌ 移动失败：{fp.name}")
            print(f"      原因: {move_result.get('error', '未知错误')}\n")

    # 🆕 OCR V2: 获取提取元数据
    extraction_metadata = state.get("extraction_metadata", {})
    
    # 构建日志记录
    state["record"] = {
        "timestamp": datetime.now().isoformat(),
        "original_file": str(fp),
        "file_size_mb": get_file_size_mb(fp),
        "preview": (state.get("preview", "")[:200]),
        "plan": plan.model_dump(),
        "dry_run": state.get("dry_run", True),
        "approved": state.get("approved", False),
        "decision": state.get("decision", "no_decision"),
        # 🆕 Step 5: 记录执行结果
        "execution_status": execution_status,
        "moved_to": moved_to,
        "move_result": state.get("move_result"),
        # 🆕 OCR V2: 记录文本提取元数据
        "extraction_metadata": extraction_metadata,
        # 🆕 PR#2: 记录路由来源
        "routing_source": state.get("routing_source", "unknown"),
        "used_learned_preference": state.get("used_learned_preference", False),
    }
    return state


def node_skip(state: JanitorState) -> JanitorState:
    """节点5b: 跳过（拒绝/不合法/待审批）"""
    fp = state["file_path"]
    plan = state["plan"]
    decision = state.get("decision", "skipped")

    # 🆕 OCR V2: 获取提取元数据
    extraction_metadata = state.get("extraction_metadata", {})
    ocr_needs_review = extraction_metadata.get("needs_review", False)
    ocr_quality_score = extraction_metadata.get("quality_score", 100)

    # 根据决策类型给出不同的提示
    if decision == "auto_reject_invalid":
        emoji = "❌"
        reason = f"不合法: {plan.validation_msg}"
    elif decision == "rejected":
        emoji = "⏭️"
        reason = "用户拒绝"
    elif decision == "pending":
        emoji = "⏳"
        reason = "等待审批"
        # 🆕 OCR V2: 如果因 OCR 质量问题导致的 pending，在原因中注明
        if ocr_needs_review:
            reason = f"等待审批 (OCR质量低: {ocr_quality_score}分)"
    else:
        emoji = "⏭️"
        reason = "跳过"
    
    print(f"   {emoji} {reason}：{fp.name}\n")

    # 构建日志记录（即使跳过也要记录）
    state["record"] = {
        "timestamp": datetime.now().isoformat(),
        "original_file": str(fp),
        "file_size_mb": get_file_size_mb(fp),
        "preview": (state.get("preview", "")[:200]),
        "plan": plan.model_dump(),
        "dry_run": state.get("dry_run", True),
        "approved": False,
        "decision": decision,
        "pending_file": state.get("pending_file"),  # 🆕 Step 7: 记录待审批文件路径
        # 🆕 OCR V2: 记录文本提取元数据
        "extraction_metadata": extraction_metadata,
        # 🆕 PR#2: 记录路由来源
        "routing_source": state.get("routing_source", "unknown"),
        "used_learned_preference": state.get("used_learned_preference", False),
    }
    return state


# --- 路由函数 ---
def route_after_review(state: JanitorState) -> str:
    """根据人类决策路由到不同节点"""
    return "apply" if state.get("approved") else "skip"


# --- 3. 构建图 (Graph) ---
def build_graph():
    """构建 LangGraph 状态图"""

    # 构建状态图
    g = StateGraph(JanitorState)
    
    # 添加节点
    g.add_node("extract_preview", node_extract_preview)
    g.add_node("llm_analyze", node_llm_analyze)
    g.add_node("build_plan", node_build_plan)
    g.add_node("validate", node_validate)
    g.add_node("human_review", node_human_review)  # 🆕 新增
    g.add_node("apply", node_apply)                # 🆕 拆分后的节点
    g.add_node("skip", node_skip)                  # 🆕 拆分后的节点

    # 定义边 (Edge)
    g.set_entry_point("extract_preview")
    g.add_edge("extract_preview", "llm_analyze")
    g.add_edge("llm_analyze", "build_plan")
    g.add_edge("build_plan", "validate")
    g.add_edge("validate", "human_review")         # 🆕 validate 后进入人类确认

    # 🆕 条件分支：根据人类决策路由
    g.add_conditional_edges(
        "human_review",
        route_after_review,
        {"apply": "apply", "skip": "skip"}
    )

    g.add_edge("apply", END)
    g.add_edge("skip", END)

    return g.compile()


# --- 辅助函数 ---
def load_config(path: Path) -> dict:
    """加载 YAML 配置文件"""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ==================== Step 6 Phase 1: 可复用的工作流类 ====================

class JanitorWorkflow:
    """
    Digital Janitor 工作流封装类
    
    将核心逻辑封装，使其既能被命令行调用，也能被其他脚本（如 watcher）导入使用。
    
    使用示例：
        # 初始化工作流
        workflow = JanitorWorkflow(config_path="config.yaml", env_path=".env")
        
        # 处理单个文件
        result = workflow.process_file(
            file_path=Path("inbox/document.pdf"),
            dry_run=False,
            auto_approve=False,
            max_preview=1000
        )
    """
    
    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        """
        初始化工作流
        
        Args:
            config_path: 配置文件路径
            env_path: 环境变量文件路径
        """
        # 1. 加载环境变量
        env_file = Path(env_path)
        if env_file.exists():
            load_dotenv(env_file)
        
        # 2. 加载配置
        self.config_path = Path(config_path)
        self.cfg = load_config(self.config_path)
        
        # 3. 解析路径配置
        self.inbox = Path(self.cfg["paths"]["inbox"])
        self.archive = Path(self.cfg["paths"]["archive"])
        self.logs = Path(self.cfg["paths"]["logs"])
        self.pending = Path("pending")  # 🆕 Step 7: 待审批目录
        
        # 4. 确保必要目录存在
        self.pending.mkdir(parents=True, exist_ok=True)
        
        # 5. 编译 LangGraph 图（只编译一次，重复使用）
        self.app = build_graph()
        
        # 6. 🆕 初始化 Memory 系统
        self.memory_db = MemoryDatabase()
        self.approval_repo = ApprovalRepository(self.memory_db)
        self.preference_repo = PreferenceRepository(self.memory_db)
        self.session_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def process_file(
        self, 
        file_path: Path, 
        dry_run: bool = True,
        auto_approve: bool = False,
        max_preview: int = 1000
    ) -> Dict[str, Any]:
        """
        处理单个文件
        
        Args:
            file_path: 要处理的文件路径
            dry_run: 是否为 dry-run 模式（只预览，不实际移动）
            auto_approve: 是否自动批准（跳过人工确认）
            max_preview: LLM 分析的最大文本长度
        
        Returns:
            包含处理结果的字典（record）
            
        Example:
            >>> workflow = JanitorWorkflow()
            >>> result = workflow.process_file(
            ...     Path("inbox/contract.pdf"),
            ...     dry_run=False,
            ...     auto_approve=True
            ... )
            >>> print(result["execution_status"])
            success
        """
        # 构造初始状态
        initial_state: JanitorState = {
            "file_path": file_path,
            "cfg": self.cfg,
            "archive_root": self.archive,
            "dry_run": dry_run,
            "max_preview": max_preview,
            "auto_approve": auto_approve,
            "preference_repo": self.preference_repo,  # 🆕 传入偏好仓库
        }
        
        # 调用编译好的图执行工作流
        final_state = self.app.invoke(initial_state)
        
        # 返回处理记录
        return final_state.get("record", {})
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """
        计算文件 hash（快速算法：文件大小 + 头部 8KB）
        
        Args:
            file_path: 文件路径
        
        Returns:
            SHA256 哈希字符串
        """
        hasher = hashlib.sha256()
        file_size = file_path.stat().st_size
        
        # 1. 写入文件大小
        hasher.update(str(file_size).encode('utf-8'))
        
        # 2. 读取头部 8KB
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(8192)
                hasher.update(chunk)
        except Exception:
            pass
        
        return hasher.hexdigest()
    
    def get_learned_folder(self, vendor: str, doc_type: str) -> Optional[str]:
        """
        获取学习到的文件夹偏好
        
        Args:
            vendor: 供应商名称
            doc_type: 文档类型
        
        Returns:
            学习到的文件夹路径，如果没有则返回 None
        """
        context = {
            'vendor': vendor,
            'doc_type': doc_type
        }
        return self.preference_repo.get_preference(
            'vendor_folder',
            context,
            min_confidence=0.7
        )
    
    def save_approval_decision(
        self,
        file_path: Path,
        analysis: Dict[str, Any],
        plan: Dict[str, Any],
        final_filename: str,
        final_folder: str,
        action: str,
        processing_time_ms: int = 0,
        extraction_method: str = "unknown"
    ):
        """
        保存用户的审批决策到 Memory 系统
        
        Args:
            file_path: 原始文件路径
            analysis: LLM 分析结果
            plan: 重命名计划
            final_filename: 最终文件名
            final_folder: 最终文件夹
            action: 操作类型 (approved/modified/rejected/skipped)
            processing_time_ms: 处理耗时（毫秒）
            extraction_method: 文本提取方法
        """
        try:
            # 计算文件 hash
            file_hash = self._compute_file_hash(file_path)
            
            # 准备日志数据
            log_data = {
                'session_id': self.session_id,
                'file_hash': file_hash,
                'original_filename': file_path.name,
                'original_path': str(file_path),
                'file_size_bytes': file_path.stat().st_size,
                
                # AI 分析
                'doc_type': analysis.get('category'),
                'vendor': analysis.get('vendor_or_party'),
                'extracted_date': analysis.get('extracted_date'),
                'confidence_score': analysis.get('confidence', 0.0),
                
                # 建议 vs 实际
                'suggested_filename': plan.get('new_name', ''),
                'suggested_folder': plan.get('dest_dir', ''),
                'final_filename': final_filename,
                'final_folder': final_folder,
                
                # 决策
                'action': action,
                'user_modified_filename': final_filename != plan.get('new_name'),
                'user_modified_folder': final_folder != plan.get('dest_dir'),
                
                # 处理信息
                'processing_time_ms': processing_time_ms,
                'extraction_method': extraction_method
            }
            
            # 保存到数据库
            self.approval_repo.save_approval(log_data)
            
        except Exception as e:
            # 记录失败不影响主流程
            print(f"⚠️  Failed to save approval decision: {e}")


# --- 主函数 ---

def main():
    """
    命令行入口函数（重构后）
    使用 JanitorWorkflow 类来处理文件
    """
    # 1. 解析命令行参数
    ap = argparse.ArgumentParser(description="Digital Janitor - LangGraph Workflow")
    ap.add_argument("--config", type=str, default="config.yaml", help="配置文件路径")
    ap.add_argument("--env", type=str, default=".env", help="环境变量文件路径")
    ap.add_argument("--preview", type=int, default=1000, help="LLM 分析的最大文本长度")
    ap.add_argument("--limit", type=int, default=10, help="处理文件数量限制")
    ap.add_argument("--auto-approve", action="store_true", help="自动批准所有合法计划（用于测试）")
    ap.add_argument("--execute", action="store_true", help="🆕 真实执行模式（移动文件），默认为 dry-run")
    args = ap.parse_args()

    # 2. 初始化工作流（加载配置、编译图）
    try:
        workflow = JanitorWorkflow(
            config_path=args.config,
            env_path=args.env
        )
    except Exception as e:
        print(f"[ERROR] Failed to initialize workflow: {e}")
        return 1

    # 3. 准备目录和扫描文件
    workflow.inbox.mkdir(parents=True, exist_ok=True)
    workflow.logs.mkdir(parents=True, exist_ok=True)
    
    files = discover_files(workflow.inbox)[: args.limit]
    if not files:
        print(f"[WARN] Inbox is empty: {workflow.inbox}")
        return 0

    # 4. 打印启动信息
    dry_run = not args.execute
    mode_str = "🧪 DRY-RUN 模式（不会移动文件）" if dry_run else "⚡ EXECUTE 模式（真实移动文件）"
    print(f"🚀 Starting LangGraph Workflow with HITL")
    print(f"📂 Processing {len(files)} files...")
    print(f"🔧 Mode: {mode_str}\n")
    print("=" * 80)

    # 5. 逐个处理文件
    records = []
    for i, fp in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 🔍 Processing: {fp.name}")
        print("-" * 80)
        
        # 🆕 Step 6: 使用 workflow.process_file() 方法
        record = workflow.process_file(
            file_path=fp,
            dry_run=dry_run,
            auto_approve=args.auto_approve,
            max_preview=args.preview
        )
        records.append(record)

    # 6. 保存日志
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_suffix = "dryrun" if dry_run else "execute"
    log_path = workflow.logs / f"graph_plan_{mode_suffix}_{ts}.jsonl"
    with log_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    print("-" * 80)
    print(f"✅ Completed. Log saved to: {log_path.name}")
    if not dry_run:
        print(f"📦 Files have been moved to: {workflow.archive.absolute()}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())