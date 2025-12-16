#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
演示如何将 JanitorWorkflow 作为库导入使用
这为 Step 6 Phase 2（文件监听）做准备
"""

import sys
import os
from pathlib import Path

# 设置 UTF-8 编码
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# 🆕 Step 6: 导入 JanitorWorkflow 类
from run_graph_once import JanitorWorkflow


def demo_as_library():
    """演示作为库使用的方式"""
    
    print("=" * 80)
    print("📚 演示：将 JanitorWorkflow 作为库使用")
    print("=" * 80)
    print()
    
    # 1. 初始化工作流（只需初始化一次）
    print("🔧 初始化工作流...")
    workflow = JanitorWorkflow(
        config_path="config.yaml",
        env_path=".env"
    )
    print(f"   ✅ 工作流已初始化")
    print(f"   📂 Inbox: {workflow.inbox}")
    print(f"   📦 Archive: {workflow.archive}")
    print()
    
    # 2. 获取要处理的文件
    from utils.file_ops import discover_files
    files = discover_files(workflow.inbox)[:2]  # 只处理前 2 个
    
    if not files:
        print("⚠️  Inbox 为空，无文件可处理")
        return
    
    print(f"📄 发现 {len(files)} 个文件待处理")
    print()
    
    # 3. 逐个处理文件
    for i, file_path in enumerate(files, 1):
        print("-" * 80)
        print(f"[{i}/{len(files)}] 🔍 处理文件: {file_path.name}")
        print("-" * 80)
        
        # 🆕 Step 6: 调用 process_file 方法
        result = workflow.process_file(
            file_path=file_path,
            dry_run=True,          # Dry-run 模式
            auto_approve=True,     # 自动批准
            max_preview=1000
        )
        
        # 4. 检查处理结果
        print()
        print(f"📊 处理结果:")
        print(f"   执行状态: {result.get('execution_status')}")
        print(f"   是否批准: {result.get('approved')}")
        print(f"   决策: {result.get('decision')}")
        
        if result.get('plan'):
            plan = result['plan']
            print(f"   新文件名: {plan.get('new_name')}")
            print(f"   目标目录: {plan.get('dest_dir')}")
        
        print()
    
    print("=" * 80)
    print("✅ 演示完成！")
    print()
    print("💡 这种用法特别适合：")
    print("   - 文件监听器（watchdog）")
    print("   - Web API 后端")
    print("   - 定时任务（cron/scheduler）")
    print("=" * 80)


def demo_single_file():
    """演示处理单个文件"""
    
    print("\n" + "=" * 80)
    print("📄 演示：处理单个指定文件")
    print("=" * 80)
    print()
    
    # 初始化工作流
    workflow = JanitorWorkflow()
    
    # 指定要处理的文件
    test_file = Path("inbox/raw_invoice.pdf")
    
    if not test_file.exists():
        print(f"⚠️  文件不存在: {test_file}")
        return
    
    print(f"🔍 处理文件: {test_file.name}")
    print()
    
    # 处理文件
    result = workflow.process_file(
        file_path=test_file,
        dry_run=True,
        auto_approve=True
    )
    
    # 显示结果
    print("\n📊 处理结果:")
    print(f"   原始文件: {result.get('original_file')}")
    print(f"   执行状态: {result.get('execution_status')}")
    
    if result.get('plan'):
        plan = result['plan']
        print(f"   分类: {plan.get('category')}")
        print(f"   置信度: {plan.get('confidence')}")
        print(f"   新文件名: {plan.get('new_name')}")
    
    print("=" * 80)


if __name__ == "__main__":
    try:
        # 演示 1: 批量处理
        demo_as_library()
        
        # 演示 2: 单个文件
        demo_single_file()
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

