#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试文件监听器
在另一个终端运行 watch_inbox.py，然后运行此脚本创建测试文件
"""

import sys
import os
import time
from pathlib import Path

# 设置 UTF-8 编码
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

def test_watcher():
    """创建测试文件，触发监听器"""
    
    inbox = Path("inbox")
    
    print("=" * 80)
    print("🧪 测试文件监听器")
    print("=" * 80)
    print()
    print("⚠️  请确保在另一个终端运行了：")
    print("   python watch_inbox.py --auto-approve")
    print()
    input("按 Enter 继续...")
    print()
    
    # 测试 1: 创建一个文本文件
    print("📝 测试 1: 创建文本文件...")
    test_file1 = inbox / f"test_watcher_{int(time.time())}.txt"
    test_file1.write_text("这是一个测试文件，用于验证监听器功能。", encoding="utf-8")
    print(f"   ✅ 已创建: {test_file1.name}")
    print(f"   ⏳ 等待监听器处理...")
    time.sleep(3)
    
    # 测试 2: 模拟大文件（分步写入）
    print("\n📦 测试 2: 模拟大文件写入...")
    test_file2 = inbox / f"test_large_{int(time.time())}.txt"
    with test_file2.open("w", encoding="utf-8") as f:
        for i in range(5):
            f.write(f"Line {i}: " + "x" * 100 + "\n")
            f.flush()
            time.sleep(0.2)  # 模拟慢速写入
    print(f"   ✅ 已创建: {test_file2.name}")
    print(f"   ⏳ 等待监听器处理...")
    time.sleep(3)
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("💡 查看另一个终端的输出，确认文件被正确处理")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_watcher()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

