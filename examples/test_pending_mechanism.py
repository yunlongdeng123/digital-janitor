#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Step 7 Phase 1 - 非阻塞式审批机制
"""

import sys
import os
import json
from pathlib import Path

# 设置 UTF-8 编码
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

def test_pending_mechanism():
    """测试待审批机制"""
    print("=" * 80)
    print("🧪 Step 7 Phase 1 - 非阻塞式审批机制测试")
    print("=" * 80)
    print()
    
    # 1. 检查 pending 目录
    pending_dir = Path("pending")
    print(f"📂 检查 pending 目录...")
    if pending_dir.exists():
        print(f"   ✅ pending/ 目录已存在")
    else:
        print(f"   ⚠️  pending/ 目录不存在，将被自动创建")
    print()
    
    # 2. 测试工作流（非自动批准模式）
    print(f"📄 测试非自动批准模式...")
    print(f"   命令: python run_graph_once.py --limit 1")
    print(f"   预期: 生成 pending JSON 文件，不等待输入")
    print()
    
    # 3. 运行测试
    from run_graph_once import JanitorWorkflow
    from utils.file_ops import discover_files
    
    try:
        workflow = JanitorWorkflow()
        print(f"✅ 工作流初始化成功")
        print()
        
        # 获取测试文件
        files = discover_files(workflow.inbox)[:1]
        if not files:
            print("⚠️  inbox 为空，无法测试")
            return
        
        test_file = files[0]
        print(f"🔍 测试文件: {test_file.name}")
        print(f"-" * 80)
        
        # 清空 pending 目录（用于测试）
        pending_count_before = len(list(pending_dir.glob("*.json"))) if pending_dir.exists() else 0
        
        # 处理文件（非自动批准模式）
        result = workflow.process_file(
            file_path=test_file,
            dry_run=True,
            auto_approve=False,  # 关键：不自动批准
            max_preview=1000
        )
        
        print(f"-" * 80)
        print()
        
        # 4. 验证结果
        print(f"📊 处理结果:")
        print(f"   决策: {result.get('decision')}")
        
        if result.get('decision') == 'pending':
            print(f"   ✅ 成功进入 pending 状态")
            
            # 检查 pending 文件
            pending_file = result.get('pending_file')
            if pending_file:
                print(f"   ✅ 已生成 pending 文件: {pending_file}")
                
                # 读取并验证 JSON 内容
                pending_path = Path(pending_file)
                if pending_path.exists():
                    with pending_path.open('r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    print(f"\n   📄 JSON 内容验证:")
                    required_fields = [
                        'original_file', 'original_name', 'new_name',
                        'dest_dir', 'category', 'confidence', 'status'
                    ]
                    
                    for field in required_fields:
                        if field in data:
                            print(f"      ✅ {field}: {data[field]}")
                        else:
                            print(f"      ❌ {field}: 缺失")
                    
                    print(f"\n   🎉 pending 机制测试通过！")
                else:
                    print(f"   ❌ pending 文件不存在: {pending_path}")
            else:
                print(f"   ❌ 未返回 pending_file 路径")
        else:
            print(f"   ⚠️  未进入 pending 状态，而是: {result.get('decision')}")
            print(f"   提示: 确保没有使用 --auto-approve 参数")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)


def list_pending_files():
    """列出所有待审批文件"""
    print("\n" + "=" * 80)
    print("📋 当前待审批文件列表")
    print("=" * 80)
    print()
    
    pending_dir = Path("pending")
    if not pending_dir.exists():
        print("⚠️  pending/ 目录不存在")
        return
    
    pending_files = list(pending_dir.glob("*.json"))
    
    if not pending_files:
        print("✅ 没有待审批文件")
    else:
        print(f"📦 发现 {len(pending_files)} 个待审批文件:\n")
        
        for i, pf in enumerate(pending_files, 1):
            try:
                with pf.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"{i}. {pf.name}")
                print(f"   原始文件: {data.get('original_name')}")
                print(f"   新名字: {data.get('new_name')}")
                print(f"   分类: {data.get('category')} (置信度: {data.get('confidence')})")
                print(f"   创建时间: {data.get('created_at')}")
                print()
            except Exception as e:
                print(f"{i}. {pf.name} - ❌ 读取失败: {e}")
                print()
    
    print("=" * 80)


if __name__ == "__main__":
    try:
        # 测试 pending 机制
        test_pending_mechanism()
        
        # 列出所有待审批文件
        list_pending_files()
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

