#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Digital Janitor - Web UI 审批界面

Step 7 Phase 2: 使用 Streamlit 构建文件整理审批 Dashboard

运行方式：
    streamlit run app.py
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

import streamlit as st
import pandas as pd

# 设置页面配置（必须是第一个 Streamlit 命令）
st.set_page_config(
    page_title="Digital Janitor - 文件审批中心",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Memory 系统
from core.memory import MemoryDatabase, ApprovalRepository, PreferenceRepository
import hashlib

# 导入项目模块
from utils.file_ops import safe_move_file


# ==================== 辅助函数 ====================

def load_pending_files() -> List[Dict[str, Any]]:
    """
    加载所有待审批文件
    
    Returns:
        包含待审批信息的字典列表
    """
    pending_dir = Path("pending")
    if not pending_dir.exists():
        return []
    
    pending_items = []
    for json_file in sorted(pending_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 添加文件路径和创建时间
            data["_json_file"] = str(json_file)
            data["_json_name"] = json_file.name
            
            # 计算文件年龄
            created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
            data["_age"] = datetime.now() - created_at
            
            pending_items.append(data)
        except Exception as e:
            st.error(f"❌ 读取 {json_file.name} 失败: {e}")
    
    return pending_items


def save_approval_to_memory(
    pending_item: Dict[str, Any],
    action: str,
    final_filename: str,
    final_folder: str
):
    """
    保存审批决策到 Memory 系统
    
    Args:
        pending_item: 待审批项数据
        action: 操作类型 (approved/modified/rejected)
        final_filename: 最终文件名
        final_folder: 最终文件夹
    """
    try:
        with MemoryDatabase() as db:
            repo = ApprovalRepository(db)
            
            # 计算文件 hash
            src_file = Path(pending_item["original_file"])
            hasher = hashlib.sha256()
            if src_file.exists():
                hasher.update(str(src_file.stat().st_size).encode('utf-8'))
                with open(src_file, 'rb') as f:
                    hasher.update(f.read(8192))
            file_hash = hasher.hexdigest()
            
            # 准备日志数据
            log_data = {
                'session_id': f"ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'file_hash': file_hash,
                'original_filename': pending_item.get("original_name", ""),
                'original_path': pending_item.get("original_file", ""),
                'file_size_bytes': src_file.stat().st_size if src_file.exists() else 0,
                
                # AI 分析
                'doc_type': pending_item.get("category"),
                'vendor': pending_item.get("extracted", {}).get("vendor"),
                'extracted_date': pending_item.get("extracted", {}).get("date"),
                'confidence_score': pending_item.get("confidence", 0.0),
                
                # 建议 vs 实际
                'suggested_filename': pending_item.get("new_name", ""),
                'suggested_folder': pending_item.get("dest_dir", ""),
                'final_filename': final_filename,
                'final_folder': final_folder,
                
                # 决策
                'action': action,
                'user_modified_filename': final_filename != pending_item.get("new_name"),
                'user_modified_folder': final_folder != pending_item.get("dest_dir"),
                
                # 处理信息
                'processing_time_ms': 0,  # UI 操作无此信息
                'extraction_method': 'unknown',
                'operator': 'ui_user'
            }
            
            # 保存到数据库
            repo.save_approval(log_data)
            
    except Exception as e:
        # 保存失败不影响主流程
        print(f"⚠️  Failed to save to memory: {e}")


def approve_file(pending_item: Dict[str, Any], archive_root: Path) -> tuple[bool, str]:
    """
    批准并执行文件移动
    
    Args:
        pending_item: 待审批项数据
        archive_root: 归档根目录
    
    Returns:
        (成功标志, 消息)
    """
    try:
        # 1. 构建源和目标路径
        src = Path(pending_item["original_file"])
        dest_dir = pending_item["dest_dir"]
        new_name = pending_item["new_name"]
        dst = archive_root / dest_dir / new_name
        
        # 2. 检查源文件是否存在
        if not src.exists():
            return False, f"源文件不存在: {src}"
        
        # 3. 执行文件移动
        result = safe_move_file(src, dst)
        
        if result["status"] == "success":
            # 4. 删除 pending JSON
            json_file = Path(pending_item["_json_file"])
            json_file.unlink()
            
            # 5. 写入日志
            log_event("approve", pending_item, result)
            
            # 6. 🆕 保存到 Memory 系统
            final_folder = dest_dir
            final_filename = Path(result["dst"]).name
            save_approval_to_memory(pending_item, "approved", final_filename, final_folder)
            
            moved_to = result["dst"]
            conflict_msg = " (已自动重命名)" if result.get("conflict_resolved") else ""
            return True, f"✅ 已移动到: {moved_to}{conflict_msg}"
        else:
            return False, f"移动失败: {result.get('error', '未知错误')}"
            
    except Exception as e:
        return False, f"处理失败: {str(e)}"


def reject_file(pending_item: Dict[str, Any], move_to_quarantine: bool = False) -> tuple[bool, str]:
    """
    拒绝文件
    
    Args:
        pending_item: 待审批项数据
        move_to_quarantine: 是否移动到隔离区
    
    Returns:
        (成功标志, 消息)
    """
    try:
        json_file = Path(pending_item["_json_file"])
        
        # 🆕 保存到 Memory 系统
        save_approval_to_memory(
            pending_item,
            "rejected",
            pending_item.get("original_name", ""),
            ""  # 拒绝的文件没有最终文件夹
        )
        
        if move_to_quarantine:
            # 移动到隔离区
            quarantine_dir = Path("quarantine/rejected")
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            dest = quarantine_dir / json_file.name
            shutil.move(str(json_file), str(dest))
            
            msg = f"⏭️ 已拒绝并移动到隔离区"
        else:
            # 直接删除
            json_file.unlink()
            msg = f"⏭️ 已拒绝"
        
        # 写入日志
        log_event("reject", pending_item, {"quarantined": move_to_quarantine})
        
        return True, msg
        
    except Exception as e:
        return False, f"拒绝失败: {str(e)}"


def log_event(action: str, pending_item: Dict[str, Any], result: Dict[str, Any]):
    """
    记录 UI 操作日志
    
    Args:
        action: 操作类型 (approve/reject)
        pending_item: 待审批项数据
        result: 操作结果
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "ui_events.jsonl"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "original_file": pending_item.get("original_file"),
        "new_name": pending_item.get("new_name"),
        "category": pending_item.get("category"),
        "result": result,
    }
    
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def get_today_logs() -> int:
    """获取今日已处理数量"""
    log_file = Path("logs/ui_events.jsonl")
    if not log_file.exists():
        return 0
    
    today = datetime.now().date()
    count = 0
    
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_date = datetime.fromisoformat(entry["timestamp"]).date()
                    if entry_date == today:
                        count += 1
                except:
                    continue
    except:
        pass
    
    return count


def format_age(age: timedelta) -> str:
    """格式化文件年龄"""
    total_seconds = int(age.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}秒前"
    elif total_seconds < 3600:
        return f"{total_seconds // 60}分钟前"
    elif total_seconds < 86400:
        return f"{total_seconds // 3600}小时前"
    else:
        return f"{total_seconds // 86400}天前"


# ==================== 侧边栏 ====================

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("📁 Digital Janitor")
        st.markdown("---")
        
        # 🆕 页面选择器
        st.header("🗂️ 页面")
        page = st.radio(
            "选择页面",
            ["📋 待审批队列", "📈 统计看板", "📜 审批历史", "🧠 学习到的偏好"],
            label_visibility="collapsed"
        )
        st.session_state['current_page'] = page
        st.markdown("---")
        
        # 统计信息
        st.header("📊 统计信息")
        
        pending_count = len(load_pending_files())
        today_count = get_today_logs()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("待审批", pending_count, help="当前待审批文件数量")
        with col2:
            st.metric("今日已处理", today_count, help="今日已批准/拒绝的文件数")
        
        st.markdown("---")
        
        # 配置
        st.header("⚙️ 配置")
        
        # 读取配置
        try:
            import yaml
            config_path = Path("config.yaml")
            if config_path.exists():
                with config_path.open("r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                
                dry_run = config.get("dry_run", True)
                archive_path = config.get("paths", {}).get("archive", "archive")
                
                st.info(f"🧪 Dry Run 模式: {'开启' if dry_run else '关闭'}")
                st.info(f"📂 归档目录: {archive_path}")
        except:
            st.warning("⚠️ 无法读取配置文件")
        
        st.markdown("---")
        
        # 快捷操作
        st.header("🚀 快捷操作")
        
        if st.button("🔄 刷新页面", use_container_width=True):
            st.rerun()
        
        if st.button("🗑️ 清空隔离区", use_container_width=True):
            quarantine_dir = Path("quarantine/rejected")
            if quarantine_dir.exists():
                count = len(list(quarantine_dir.glob("*.json")))
                shutil.rmtree(quarantine_dir)
                st.success(f"已清空 {count} 个文件")
                st.rerun()
        
        st.markdown("---")
        
        # 帮助信息
        with st.expander("ℹ️ 帮助"):
            st.markdown("""
            **使用说明：**
            1. 待审批文件会自动显示在主界面
            2. 点击"批准"执行文件移动
            3. 点击"拒绝"删除待审批项
            4. 所有操作都会记录到日志
            
            **提示：**
            - 批准后文件会立即移动
            - 拒绝的文件可移动到隔离区
            - 使用"刷新"查看最新文件
            """)


# ==================== 主界面 ====================

def render_main():
    """渲染主界面"""
    st.title("📋 文件审批中心")
    st.markdown("---")
    
    # 加载待审批文件
    pending_items = load_pending_files()
    
    if not pending_items:
        st.info("✅ 没有待审批文件！")
        st.balloons()
        
        # 显示快捷操作
        st.markdown("### 🚀 快速开始")
        col1, col2 = st.columns(2)
        
        with col1:
            st.code("python run_graph_once.py --limit 5", language="bash")
            st.caption("生成待审批文件")
        
        with col2:
            st.code("python watch_inbox.py", language="bash")
            st.caption("启动文件监听器")
        
        return
    
    # 显示待审批数量
    st.success(f"📦 发现 {len(pending_items)} 个待审批文件")
    
    # 批量操作
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("### 待审批队列")
    with col2:
        if st.button("✅ 批准全部", use_container_width=True, type="primary"):
            approve_all(pending_items)
    with col3:
        if st.button("❌ 拒绝全部", use_container_width=True):
            reject_all(pending_items)
    
    st.markdown("---")
    
    # 加载配置
    try:
        import yaml
        with Path("config.yaml").open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        archive_root = Path(config["paths"]["archive"])
    except:
        archive_root = Path("archive")
    
    # 显示每个待审批项
    for i, item in enumerate(pending_items):
        render_pending_item(item, i, archive_root)


def render_pending_item(item: Dict[str, Any], index: int, archive_root: Path):
    """
    渲染单个待审批项
    
    Args:
        item: 待审批项数据
        index: 索引
        archive_root: 归档根目录
    """
    with st.container():
        # 创建卡片样式
        with st.expander(
            f"📄 {item.get('original_name', '未知文件')} → {item.get('new_name', '未知')}", 
            expanded=True
        ):
            # 第一行：基本信息
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**原始文件：** `{item.get('original_file', 'N/A')}`")
                st.markdown(f"**新文件名：** `{item.get('new_name', 'N/A')}`")
                st.markdown(f"**目标目录：** `{item.get('dest_dir', 'N/A')}`")
            
            with col2:
                # 分类标签
                category = item.get('category', 'default')
                confidence = item.get('confidence', 0.0)
                
                category_emoji = {
                    "invoice": "💰", "contract": "📝", "paper": "📄",
                    "image": "🖼️", "presentation": "🎨", "default": "📦"
                }.get(category, "📦")
                
                st.metric(
                    f"{category_emoji} {category.upper()}",
                    f"{confidence:.0%}",
                    help="分类置信度"
                )
                
                # 文件年龄
                age = item.get('_age')
                if age:
                    st.caption(f"⏱️ {format_age(age)}")
            
            # 第二行：详细信息（改为直接显示，避免嵌套 expander）
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 提取的元数据：**")
                extracted = item.get('extracted', {})
                if extracted:
                    for key, value in extracted.items():
                        if value:
                            st.text(f"• {key}: {value}")
                else:
                    st.caption("无")
            
            with col2:
                st.markdown("**💡 LLM 分析理由：**")
                rationale = item.get('rationale', 'N/A')
                st.caption(rationale)
            
            # 预览内容（改为直接显示）
            preview = item.get('preview', '')
            if preview:
                st.markdown("---")
                st.markdown("**👁️ 内容预览：**")
                st.text_area(
                    "preview", 
                    preview[:500], 
                    height=100, 
                    disabled=True, 
                    label_visibility="collapsed",
                    key=f"preview_{index}"
                )
            
            # 第三行：操作按钮
            st.markdown("---")
            col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
            
            with col1:
                if st.button("✅ 批准", key=f"approve_{index}", type="primary", use_container_width=True):
                    with st.spinner("处理中..."):
                        success, msg = approve_file(item, archive_root)
                    
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            
            with col2:
                if st.button("❌ 拒绝", key=f"reject_{index}", use_container_width=True):
                    with st.spinner("处理中..."):
                        success, msg = reject_file(item, move_to_quarantine=False)
                    
                    if success:
                        st.warning(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            
            with col3:
                if st.button("🗑️ 隔离", key=f"quarantine_{index}", use_container_width=True):
                    with st.spinner("处理中..."):
                        success, msg = reject_file(item, move_to_quarantine=True)
                    
                    if success:
                        st.info(msg)
                        st.rerun()
                    else:
                        st.error(msg)


def approve_all(pending_items: List[Dict[str, Any]]):
    """批准所有文件"""
    try:
        import yaml
        with Path("config.yaml").open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        archive_root = Path(config["paths"]["archive"])
    except:
        archive_root = Path("archive")
    
    success_count = 0
    fail_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, item in enumerate(pending_items):
        status_text.text(f"处理中: {item.get('original_name')} ({i+1}/{len(pending_items)})")
        
        success, msg = approve_file(item, archive_root)
        if success:
            success_count += 1
        else:
            fail_count += 1
            st.error(f"{item.get('original_name')}: {msg}")
        
        progress_bar.progress((i + 1) / len(pending_items))
    
    status_text.empty()
    progress_bar.empty()
    
    if fail_count == 0:
        st.success(f"🎉 已批准全部 {success_count} 个文件！")
    else:
        st.warning(f"✅ 成功: {success_count} | ❌ 失败: {fail_count}")
    
    st.rerun()


def reject_all(pending_items: List[Dict[str, Any]]):
    """拒绝所有文件"""
    for item in pending_items:
        reject_file(item, move_to_quarantine=True)
    
    st.warning(f"⏭️ 已拒绝全部 {len(pending_items)} 个文件")
    st.rerun()


# ==================== 🆕 历史查看页面 ====================

def render_history_page():
    """渲染审批历史页面"""
    st.title("📜 审批历史")
    
    try:
        with MemoryDatabase() as db:
            repo = ApprovalRepository(db)
            
            # 统计卡片
            stats = repo.get_statistics(days=30)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总处理数", stats['total_approvals'])
            with col2:
                st.metric("最近30天", stats['recent_count'])
            with col3:
                approved = stats['action_breakdown'].get('approved', 0) + stats['action_breakdown'].get('modified', 0)
                st.metric("通过", approved)
            with col4:
                rejected = stats['action_breakdown'].get('rejected', 0) + stats['action_breakdown'].get('skipped', 0)
                st.metric("拒绝", rejected)
            
            st.markdown("---")
            
            # 筛选器
            st.subheader("🔍 筛选条件")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                doc_type_filter = st.selectbox(
                    "文档类型",
                    ["全部", "invoice", "contract", "paper", "presentation", "image", "default"]
                )
            
            with col2:
                vendor_filter = st.text_input("供应商（模糊搜索）")
            
            with col3:
                limit = st.number_input("显示数量", min_value=10, max_value=500, value=50)
            
            # 查询
            filters = {
                'doc_type': None if doc_type_filter == "全部" else doc_type_filter,
                'vendor': vendor_filter if vendor_filter else None,
                'limit': limit
            }
            
            results = repo.get_recent_approvals(**filters)
            
            if results:
                st.success(f"找到 {len(results)} 条记录")
                
                # 转为 DataFrame
                df = pd.DataFrame(results)
                
                # 格式化时间
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                
                # 选择显示的列
                display_cols = [
                    'created_at', 'original_filename', 'doc_type', 'vendor',
                    'action', 'final_filename', 'confidence_score'
                ]
                
                # 过滤存在的列
                display_cols = [col for col in display_cols if col in df.columns]
                
                # 显示表格
                st.dataframe(
                    df[display_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "created_at": "时间",
                        "original_filename": "原始文件名",
                        "doc_type": "类型",
                        "vendor": "供应商",
                        "action": "操作",
                        "final_filename": "最终文件名",
                        "confidence_score": st.column_config.NumberColumn("置信度", format="%.2f")
                    }
                )
                
                # 导出功能
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 导出为 CSV",
                    data=csv,
                    file_name=f"approval_history_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("没有找到匹配的记录")
                
    except Exception as e:
        st.error(f"加载历史记录失败: {e}")


def render_preferences_page():
    """渲染学习到的偏好页面"""
    st.title("🧠 学习到的偏好")
    
    try:
        with MemoryDatabase() as db:
            repo = PreferenceRepository(db)
            
            # 获取所有偏好
            prefs = repo.list_all_preferences()
            
            if prefs:
                st.success(f"发现 {len(prefs)} 条学习到的偏好")
                
                # 按类型分组显示
                vendor_folder_prefs = [p for p in prefs if p['type'] == 'vendor_folder']
                
                if vendor_folder_prefs:
                    st.subheader("📁 供应商文件夹映射")
                    
                    for pref in vendor_folder_prefs:
                        with st.expander(f"{pref['vendor']} + {pref['doc_type']} → {pref['value']}"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("置信度", f"{pref['confidence']:.0%}")
                            with col2:
                                st.metric("样本数", pref['sample_count'])
                            with col3:
                                st.text(f"最后更新: {pref['last_seen'][:10] if pref['last_seen'] else 'N/A'}")
                            
                            if st.button(f"🗑️ 删除", key=f"del_{pref['id']}"):
                                repo.disable_preference(pref['id'])
                                st.success("已删除")
                                st.rerun()
                
                # 转为表格显示
                df = pd.DataFrame(vendor_folder_prefs)
                if not df.empty:
                    st.dataframe(
                        df[['vendor', 'doc_type', 'value', 'confidence', 'sample_count']],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "vendor": "供应商",
                            "doc_type": "文档类型",
                            "value": "目标文件夹",
                            "confidence": st.column_config.NumberColumn("置信度", format="%.2f"),
                            "sample_count": "样本数"
                        }
                    )
            else:
                st.info("还没有学习到任何偏好")
                st.markdown("""
                💡 **如何让系统学习？**
                1. 在审批时，如果 AI 建议的文件夹不正确
                2. 你多次将某个供应商的文件移动到特定文件夹
                3. 系统会自动学习这个偏好，下次自动应用
                """)
                
    except Exception as e:
        st.error(f"加载偏好失败: {e}")


def render_dashboard_page():
    """渲染统计看板页面"""
    st.title("📈 统计看板")
    st.markdown("系统运行数据总览")
    st.markdown("---")
    
    try:
        with MemoryDatabase() as db:
            repo = ApprovalRepository(db)
            
            # 获取统计数据
            stats = repo.get_statistics(days=30)
            all_approvals = repo.get_recent_approvals(limit=1000)
            
            # === 1. 关键指标 (KPI) ===
            st.subheader("📊 关键指标")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total = stats['total_approvals']
                st.metric(
                    "总处理文件数",
                    f"{total:,}",
                    help="系统启动以来处理的文件总数"
                )
            
            with col2:
                # 计算自动化率
                approved_count = stats['action_breakdown'].get('approved', 0)
                automation_rate = (approved_count / total * 100) if total > 0 else 0
                st.metric(
                    "自动化率",
                    f"{automation_rate:.1f}%",
                    help="直接批准（未修改）的文件占比"
                )
            
            with col3:
                # 估算节省时间（假设每个文件手动处理需要2分钟）
                time_saved_minutes = total * 2
                if time_saved_minutes >= 60:
                    time_saved_display = f"{time_saved_minutes // 60:.1f}小时"
                else:
                    time_saved_display = f"{time_saved_minutes}分钟"
                
                st.metric(
                    "节省时间估算",
                    time_saved_display,
                    help="假设每个文件手动整理需要2分钟"
                )
            
            with col4:
                recent = stats['recent_count']
                st.metric(
                    "最近30天",
                    f"{recent:,}",
                    help="最近30天处理的文件数"
                )
            
            st.markdown("---")
            
            # === 2. 图表 1: 文件类型分布 ===
            st.subheader("📁 文件类型分布")
            
            if all_approvals:
                # 统计文件类型
                df_all = pd.DataFrame(all_approvals)
                
                if 'doc_type' in df_all.columns:
                    type_counts = df_all['doc_type'].value_counts()
                    
                    # 创建两列布局
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # 使用 bar_chart
                        st.bar_chart(type_counts)
                    
                    with col2:
                        # 显示详细数据
                        st.dataframe(
                            pd.DataFrame({
                                '类型': type_counts.index,
                                '数量': type_counts.values,
                                '占比': [f"{v/type_counts.sum()*100:.1f}%" for v in type_counts.values]
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                else:
                    st.info("暂无文件类型数据")
            else:
                st.info("暂无数据")
            
            st.markdown("---")
            
            # === 3. 图表 2: 最近7天处理量趋势 ===
            st.subheader("📈 最近7天处理量趋势")
            
            if all_approvals:
                df_all = pd.DataFrame(all_approvals)
                
                if 'created_at' in df_all.columns:
                    # 转换时间格式
                    df_all['date'] = pd.to_datetime(df_all['created_at']).dt.date
                    
                    # 获取最近7天的数据
                    last_7_days = pd.date_range(
                        end=datetime.now().date(),
                        periods=7
                    ).date
                    
                    # 统计每天的处理量
                    daily_counts = df_all.groupby('date').size()
                    
                    # 创建完整的7天数据（包括0的天数）
                    trend_data = pd.Series(
                        [daily_counts.get(day, 0) for day in last_7_days],
                        index=last_7_days
                    )
                    
                    # 创建两列布局
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.line_chart(trend_data)
                    
                    with col2:
                        st.dataframe(
                            pd.DataFrame({
                                '日期': [str(d) for d in trend_data.index],
                                '处理量': trend_data.values
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                else:
                    st.info("暂无时间数据")
            else:
                st.info("暂无数据")
            
            st.markdown("---")
            
            # === 4. 图表 3: Top 5 供应商 ===
            st.subheader("🏢 Top 5 最常出现的供应商")
            
            top_vendors = stats.get('top_vendors', [])
            
            if top_vendors:
                # 转为 DataFrame
                vendor_df = pd.DataFrame(top_vendors, columns=['供应商', '文件数'])
                vendor_df = vendor_df.head(5)  # 只取前5个
                
                # 创建两列布局
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 使用 bar_chart
                    chart_data = vendor_df.set_index('供应商')
                    st.bar_chart(chart_data)
                
                with col2:
                    # 显示表格
                    st.dataframe(
                        vendor_df,
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.info("暂无供应商数据")
            
            st.markdown("---")
            
            # === 5. 额外信息 ===
            st.subheader("ℹ️ 系统信息")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"📊 **操作分布**")
                for action, count in stats['action_breakdown'].items():
                    percentage = (count / total * 100) if total > 0 else 0
                    st.text(f"• {action}: {count} ({percentage:.1f}%)")
            
            with col2:
                avg_time = stats['avg_processing_time_ms']
                st.info(f"⏱️ **平均处理时间**")
                st.text(f"• {avg_time:.0f} ms/文件")
                
                if total > 0:
                    total_time_seconds = total * avg_time / 1000
                    st.text(f"• 累计: {total_time_seconds:.1f} 秒")
            
    except Exception as e:
        st.error(f"加载统计数据失败: {e}")
        st.exception(e)  # 显示详细错误信息


# ==================== 主程序 ====================

def main():
    """主程序入口"""
    # 渲染侧边栏
    render_sidebar()
    
    # 🆕 根据选择的页面渲染不同内容
    page = st.session_state.get('current_page', '📋 待审批队列')
    
    if page == '📈 统计看板':
        render_dashboard_page()
    elif page == '📜 审批历史':
        render_history_page()
    elif page == '🧠 学习到的偏好':
        render_preferences_page()
    else:
        # 默认：渲染主界面（待审批队列）
        render_main()
    
    # 页脚
    st.markdown("---")
    st.caption("📁 Digital Janitor - Powered by Streamlit & LangGraph")


if __name__ == "__main__":
    main()

