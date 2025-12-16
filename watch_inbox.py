#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Digital Janitor - 实时文件监听器

Step 6 Phase 2: 使用 watchdog 监听 inbox 目录
- 🔍 实时监听文件创建/移动事件
- ⏱️  防抖机制：确保文件传输完成后再处理
- 📋 队列处理：防止并发冲突
- 🛡️  异常隔离：单个文件错误不影响监听器运行

使用方式：
    # Dry-run 模式（只预览）
    python watch_inbox.py
    
    # Execute 模式（真实移动文件）
    python watch_inbox.py --execute --auto-approve
"""

from __future__ import annotations

import sys
import os
import argparse
import time
import threading
from queue import Queue, Empty
from pathlib import Path
from datetime import datetime

# 设置 UTF-8 编码
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# 导入重构后的工作流类
from run_graph_once import JanitorWorkflow


# ==================== 文件稳定性检查 ====================

def wait_for_file_stability(
    path: Path,
    timeout: float = 5.0,
    check_interval: float = 0.5,
    min_stable_count: int = 3
) -> bool:
    """
    等待文件传输完成（文件大小稳定）
    
    防止在文件还在写入时就开始处理。通过多次检查文件大小，
    只有当大小连续几次不变时，才认为文件已稳定。
    
    Args:
        path: 文件路径
        timeout: 最大等待时间（秒）
        check_interval: 检查间隔（秒）
        min_stable_count: 连续稳定次数（默认 3 次）
    
    Returns:
        True 表示文件已稳定，False 表示超时或文件消失
    
    Example:
        >>> if wait_for_file_stability(Path("inbox/big_file.pdf")):
        ...     print("文件已准备好处理")
    """
    start_time = time.time()
    last_size = -1
    stable_count = 0
    
    while (time.time() - start_time) < timeout:
        # 检查文件是否存在
        if not path.exists():
            return False
        
        # 检查是否是文件（排除目录）
        if not path.is_file():
            return False
        
        try:
            # 获取当前文件大小
            current_size = path.stat().st_size
            
            # 文件大小必须大于 0（排除空文件或正在创建的文件）
            if current_size == 0:
                time.sleep(check_interval)
                continue
            
            # 比较与上次大小
            if current_size == last_size:
                stable_count += 1
                # 连续多次大小不变，认为文件已稳定
                if stable_count >= min_stable_count:
                    return True
            else:
                # 大小发生变化，重置计数
                stable_count = 0
                last_size = current_size
            
            time.sleep(check_interval)
            
        except (OSError, PermissionError):
            # 文件可能正在被占用
            time.sleep(check_interval)
            continue
    
    # 超时
    return False


# ==================== 文件过滤器 ====================

def should_process_file(path: Path) -> bool:
    """
    判断文件是否应该被处理
    
    过滤掉：
    - 目录
    - 隐藏文件（以 . 开头）
    - 临时文件（以 ~$ 开头或 .tmp 结尾）
    - 不支持的扩展名
    
    Args:
        path: 文件路径
    
    Returns:
        True 表示应该处理，False 表示应该跳过
    """
    # 必须是文件
    if not path.is_file():
        return False
    
    filename = path.name
    
    # 跳过隐藏文件
    if filename.startswith('.'):
        return False
    
    # 跳过临时文件
    if filename.startswith('~$') or filename.endswith('.tmp'):
        return False
    
    # 跳过 Windows 锁定文件
    if filename.startswith('~lock.'):
        return False
    
    # 支持的扩展名（可以扩展）
    supported_extensions = {
        '.pdf', '.docx', '.doc', '.txt', '.md',
        '.xlsx', '.xls', '.ppt', '.pptx',
        '.png', '.jpg', '.jpeg', '.gif'
    }
    
    ext = path.suffix.lower()
    if ext not in supported_extensions:
        return False
    
    return True


# ==================== 事件处理器 ====================

class InboxHandler(FileSystemEventHandler):
    """
    Inbox 目录的文件系统事件处理器
    
    监听文件创建和移动事件，将合法的文件路径放入队列。
    """
    
    def __init__(self, file_queue: Queue):
        """
        初始化处理器
        
        Args:
            file_queue: 用于存放待处理文件路径的队列
        """
        super().__init__()
        self.file_queue = file_queue
    
    def on_created(self, event: FileSystemEvent):
        """文件创建事件"""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        
        # 过滤文件
        if should_process_file(path):
            print(f"📥 检测到新文件: {path.name}")
            self.file_queue.put(path)
    
    def on_moved(self, event: FileSystemEvent):
        """文件移动事件（拖拽到 inbox）"""
        if event.is_directory:
            return
        
        path = Path(event.dest_path)
        
        # 过滤文件
        if should_process_file(path):
            print(f"📥 检测到移入文件: {path.name}")
            self.file_queue.put(path)


# ==================== Worker 线程 ====================

def worker_thread(
    file_queue: Queue,
    workflow: JanitorWorkflow,
    dry_run: bool,
    auto_approve: bool,
    stop_event: threading.Event
):
    """
    Worker 线程：从队列中获取文件并处理
    
    Args:
        file_queue: 文件队列
        workflow: JanitorWorkflow 实例（已初始化）
        dry_run: 是否为 dry-run 模式
        auto_approve: 是否自动批准
        stop_event: 停止事件
    """
    print("🔧 Worker 线程已启动")
    
    while not stop_event.is_set():
        try:
            # 从队列获取文件（带超时，以便响应 stop_event）
            try:
                file_path = file_queue.get(timeout=1.0)
            except Empty:
                continue
            
            print(f"\n{'=' * 80}")
            print(f"⚙️  开始处理: {file_path.name}")
            print(f"{'=' * 80}")
            
            # 1. 等待文件稳定
            print(f"⏱️  等待文件传输完成...")
            if not wait_for_file_stability(file_path, timeout=10.0):
                print(f"⚠️  文件不稳定或已消失，跳过: {file_path.name}")
                file_queue.task_done()
                continue
            
            print(f"✅ 文件已稳定，开始处理")
            print(f"-" * 80)
            
            # 2. 调用工作流处理文件
            try:
                result = workflow.process_file(
                    file_path=file_path,
                    dry_run=dry_run,
                    auto_approve=auto_approve,
                    max_preview=1000
                )
                
                # 3. 打印处理结果摘要
                decision = result.get('decision')
                print(f"\n📊 处理结果:")
                print(f"   执行状态: {result.get('execution_status')}")
                print(f"   决策: {decision}")
                
                # 🆕 Step 7: 区分不同决策类型的显示
                if decision == "pending":
                    pending_file = result.get('pending_file')
                    if pending_file:
                        print(f"   ⏳ 待审批文件: {pending_file}")
                elif result.get('moved_to'):
                    print(f"   ✅ 已移动至: {result.get('moved_to')}")
                
            except Exception as e:
                print(f"❌ 处理文件时出错: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                file_queue.task_done()
            
            print(f"{'=' * 80}\n")
            
        except Exception as e:
            # 捕获所有异常，确保 Worker 不会崩溃
            print(f"❌ Worker 线程异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("🛑 Worker 线程已停止")


# ==================== 主函数 ====================

def main():
    """
    主函数：启动文件监听器
    """
    # 1. 解析命令行参数
    ap = argparse.ArgumentParser(description="Digital Janitor - 实时文件监听器")
    ap.add_argument("--config", type=str, default="config.yaml", help="配置文件路径")
    ap.add_argument("--env", type=str, default=".env", help="环境变量文件路径")
    ap.add_argument("--execute", action="store_true", help="真实执行模式（移动文件），默认为 dry-run")
    ap.add_argument("--auto-approve", action="store_true", help="自动批准所有合法计划")
    args = ap.parse_args()
    
    # 2. 初始化工作流（只初始化一次）
    print("🚀 初始化 Digital Janitor 监听器...")
    try:
        workflow = JanitorWorkflow(
            config_path=args.config,
            env_path=args.env
        )
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return 1
    
    # 3. 准备目录
    workflow.inbox.mkdir(parents=True, exist_ok=True)
    workflow.logs.mkdir(parents=True, exist_ok=True)
    
    # 4. 创建队列和停止事件
    file_queue = Queue()
    stop_event = threading.Event()
    
    # 5. 启动 Worker 线程
    dry_run = not args.execute
    worker = threading.Thread(
        target=worker_thread,
        args=(file_queue, workflow, dry_run, args.auto_approve, stop_event),
        daemon=True
    )
    worker.start()
    
    # 6. 设置文件系统监听器
    event_handler = InboxHandler(file_queue)
    observer = Observer()
    observer.schedule(event_handler, str(workflow.inbox), recursive=False)
    observer.start()
    
    # 7. 打印启动信息
    mode_str = "🧪 DRY-RUN 模式" if dry_run else "⚡ EXECUTE 模式"
    approve_str = "🤖 自动批准" if args.auto_approve else "🤝 需要人工确认"
    
    print(f"\n{'=' * 80}")
    print(f"👀 Digital Janitor 正在监听...")
    print(f"{'=' * 80}")
    print(f"📂 监听目录: {workflow.inbox.absolute()}")
    print(f"🔧 运行模式: {mode_str}")
    print(f"🎛️  批准模式: {approve_str}")
    print(f"\n💡 提示:")
    print(f"   - 将文件复制/移动到 inbox 目录即可自动处理")
    print(f"   - 按 Ctrl+C 停止监听")
    print(f"{'=' * 80}\n")
    
    # 8. 保持运行，等待 Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号...")
        print("⏳ 等待队列中的任务完成...")
        
        # 停止 observer
        observer.stop()
        observer.join()
        
        # 停止 worker
        stop_event.set()
        worker.join(timeout=5.0)
        
        print("✅ 监听器已安全停止")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

