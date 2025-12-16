#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
校验器测试脚本
验证 RenamePlan 校验功能
"""

import sys
import os
from pathlib import Path

# 修复 Windows 控制台 UTF-8 输出问题
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.schemas import RenamePlan
from core.validator import validate_plan, validate_plans_batch, get_validation_stats


def test_valid_plan():
    """测试 1: 有效的计划"""
    print("=" * 60)
    print("测试 1: 有效的计划")
    print("=" * 60)
    
    plan = RenamePlan(
        category="invoice",
        new_name="[发票]_2024-03_阿里云_1580元.pdf",
        dest_dir="archive/发票/2024/03",
        confidence=0.95,
        extracted={"date_ym": "2024-03", "amount": "1580元"},
        rationale="发票关键词命中"
    )
    
    result = validate_plan(plan)
    
    if result.is_valid:
        print(f"✅ 校验通过")
        print(f"  - new_name: {result.new_name}")
        print(f"  - dest_dir: {result.dest_dir}")
        print(f"  - validation_msg: {result.validation_msg}")
        return True
    else:
        print(f"❌ 校验失败: {result.validation_msg}")
        return False


def test_invalid_filename():
    """测试 2: 包含非法字符的文件名"""
    print("\n" + "=" * 60)
    print("测试 2: 包含非法字符的文件名")
    print("=" * 60)
    
    plan = RenamePlan(
        category="invoice",
        new_name='发票<>:"/\\|?*.pdf',  # 包含所有非法字符
        dest_dir="archive/发票/2024/03",
        confidence=0.95
    )
    
    print(f"原始文件名: {plan.new_name}")
    
    result = validate_plan(plan)
    
    print(f"清理后文件名: {result.new_name}")
    print(f"校验状态: {'通过' if result.is_valid else '失败'}")
    print(f"校验消息: {result.validation_msg}")
    
    # 这个测试预期通过（因为会自动清理非法字符）
    return result.is_valid


def test_directory_traversal():
    """测试 3: 目录穿越攻击"""
    print("\n" + "=" * 60)
    print("测试 3: 目录穿越攻击防护")
    print("=" * 60)
    
    dangerous_paths = [
        "../../../etc/passwd",
        "archive/../../system",
        "..\\..\\Windows\\System32",
    ]
    
    all_blocked = True
    for path in dangerous_paths:
        plan = RenamePlan(
            category="default",
            new_name="test.txt",
            dest_dir=path,
            confidence=0.5
        )
        
        result = validate_plan(plan)
        
        if result.is_valid:
            print(f"❌ 危险路径未被阻止: {path}")
            all_blocked = False
        else:
            print(f"✅ 成功阻止危险路径: {path}")
            print(f"   原因: {result.validation_msg}")
    
    return all_blocked


def test_absolute_path():
    """测试 4: 绝对路径检测"""
    print("\n" + "=" * 60)
    print("测试 4: 绝对路径检测")
    print("=" * 60)
    
    absolute_paths = [
        "/home/user/archive",
        "C:\\Users\\Documents",
        "D:/data/files",
    ]
    
    all_blocked = True
    for path in absolute_paths:
        plan = RenamePlan(
            category="default",
            new_name="test.txt",
            dest_dir=path,
            confidence=0.5
        )
        
        result = validate_plan(plan)
        
        if result.is_valid:
            print(f"❌ 绝对路径未被阻止: {path}")
            all_blocked = False
        else:
            print(f"✅ 成功阻止绝对路径: {path}")
            print(f"   原因: {result.validation_msg}")
    
    return all_blocked


def test_reserved_names():
    """测试 5: Windows 保留名称"""
    print("\n" + "=" * 60)
    print("测试 5: Windows 保留名称检测")
    print("=" * 60)
    
    reserved_names = ["CON.txt", "PRN.pdf", "AUX.docx", "NUL.xlsx"]
    
    all_detected = True
    for name in reserved_names:
        plan = RenamePlan(
            category="default",
            new_name=name,
            dest_dir="archive",
            confidence=0.5
        )
        
        result = validate_plan(plan)
        
        if result.is_valid:
            print(f"❌ 保留名称未被检测: {name}")
            all_detected = False
        else:
            print(f"✅ 成功检测保留名称: {name}")
            print(f"   原因: {result.validation_msg}")
    
    return all_detected


def test_batch_validation():
    """测试 6: 批量校验"""
    print("\n" + "=" * 60)
    print("测试 6: 批量校验")
    print("=" * 60)
    
    plans = [
        RenamePlan(
            category="invoice",
            new_name="[发票]_2024-03.pdf",
            dest_dir="archive/发票/2024",
            confidence=0.95
        ),
        RenamePlan(
            category="contract",
            new_name="合同<>.pdf",  # 包含非法字符
            dest_dir="../../../etc",  # 目录穿越
            confidence=0.80
        ),
        RenamePlan(
            category="paper",
            new_name="论文.pdf",
            dest_dir="archive/论文",
            confidence=0.90
        ),
    ]
    
    results = validate_plans_batch(plans)
    stats = get_validation_stats(results)
    
    print(f"总计: {stats['total']}")
    print(f"通过: {stats['valid']}")
    print(f"失败: {stats['invalid']}")
    print(f"通过率: {stats['valid_rate']:.1%}")
    
    if stats['invalid'] > 0:
        print(f"\n失败的计划:")
        for item in stats['invalid_plans']:
            print(f"  - {item['file']}: {item['reason']}")
    
    # 预期：3个计划中，2个通过，1个失败
    return stats['valid'] == 2 and stats['invalid'] == 1


def main():
    """主函数"""
    print("\n🚀 校验器功能测试")
    print(f"📍 项目根目录: {project_root}")
    print()
    
    # 运行所有测试
    results = []
    results.append(("有效计划", test_valid_plan()))
    results.append(("非法字符清理", test_invalid_filename()))
    results.append(("目录穿越防护", test_directory_traversal()))
    results.append(("绝对路径检测", test_absolute_path()))
    results.append(("保留名称检测", test_reserved_names()))
    results.append(("批量校验", test_batch_validation()))
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:20s} {status}")
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print("✅ 所有测试通过！校验器工作正常 🎉")
        return 0
    else:
        print(f"⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

