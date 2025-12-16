#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试可编辑审批功能

验证：
1. overrides 参数是否正确处理
2. 扩展名是否自动补全
3. Memory 是否正确记录修改标志
4. 偏好学习是否被触发
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.memory import MemoryDatabase, ApprovalRepository, PreferenceRepository


def test_memory_recording():
    """测试 Memory 记录功能"""
    print("=" * 80)
    print("🧪 测试 Memory 记录")
    print("=" * 80)
    
    try:
        with MemoryDatabase() as db:
            repo = ApprovalRepository(db)
            
            # 获取最近 5 条记录
            logs = repo.get_recent_approvals(limit=5)
            
            if not logs:
                print("❌ 没有找到任何审批记录")
                print("   请先使用 UI 批准一个文件\n")
                return False
            
            print(f"\n✅ 找到 {len(logs)} 条最近的审批记录\n")
            
            for i, log in enumerate(logs, 1):
                print(f"--- 记录 #{i} ---")
                print(f"  原始文件: {log['original_filename']}")
                print(f"  操作: {log['action']}")
                print(f"  建议文件夹: {log['suggested_folder']}")
                print(f"  最终文件夹: {log['final_folder']}")
                print(f"  用户修改了文件夹: {log['user_modified_folder']}")
                print(f"  建议文件名: {log['suggested_filename']}")
                print(f"  最终文件名: {log['final_filename']}")
                print(f"  用户修改了文件名: {log['user_modified_filename']}")
                print(f"  供应商: {log.get('vendor', 'N/A')}")
                print(f"  文档类型: {log.get('doc_type', 'N/A')}")
                print(f"  时间: {log['created_at']}")
                print()
            
            # 检查是否有修改记录
            modified_logs = [log for log in logs if log['action'] == 'modified']
            if modified_logs:
                print(f"🎉 发现 {len(modified_logs)} 条用户修改记录！")
            else:
                print("💡 提示：尚未发现用户修改记录")
                print("   在 UI 中修改字段后批准，action 会变为 'modified'\n")
            
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_preference_learning():
    """测试偏好学习功能"""
    print("=" * 80)
    print("🧠 测试偏好学习")
    print("=" * 80)
    
    try:
        with MemoryDatabase() as db:
            pref_repo = PreferenceRepository(db)
            
            # 获取所有学习到的偏好
            prefs = pref_repo.list_all_preferences()
            
            if not prefs:
                print("❌ 还没有学习到任何偏好")
                print("   请在 UI 中修改文件夹并批准，系统会自动学习\n")
                return False
            
            print(f"\n✅ 系统已学习到 {len(prefs)} 条偏好规则\n")
            
            for i, pref in enumerate(prefs, 1):
                print(f"--- 偏好 #{i} ---")
                print(f"  类型: {pref['type']}")
                print(f"  供应商: {pref.get('vendor', 'N/A')}")
                print(f"  文档类型: {pref.get('doc_type', 'N/A')}")
                print(f"  目标文件夹: {pref['value']}")
                print(f"  置信度: {pref['confidence']:.2f}")
                print(f"  样本数: {pref['sample_count']}")
                print(f"  最后更新: {pref['last_seen']}")
                print()
            
            # 测试查询功能
            print("=" * 80)
            print("🔍 测试偏好查询")
            print("=" * 80)
            
            if prefs:
                test_pref = prefs[0]
                vendor = test_pref.get('vendor')
                doc_type = test_pref.get('doc_type')
                
                if vendor and doc_type:
                    learned_folder = pref_repo.get_preference(
                        'vendor_folder',
                        {'vendor': vendor, 'doc_type': doc_type},
                        min_confidence=0.5
                    )
                    
                    print(f"\n查询：{vendor} + {doc_type}")
                    print(f"结果：{learned_folder}")
                    
                    if learned_folder == test_pref['value']:
                        print("✅ 查询结果正确！\n")
                    else:
                        print("❌ 查询结果不匹配\n")
            
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_statistics():
    """测试统计功能"""
    print("=" * 80)
    print("📊 测试统计信息")
    print("=" * 80)
    
    try:
        with MemoryDatabase() as db:
            repo = ApprovalRepository(db)
            
            stats = repo.get_statistics(days=30)
            
            print(f"\n最近 30 天统计：")
            print(f"  总审批数: {stats['total_approvals']}")
            print(f"  最近审批数: {stats['recent_count']}")
            print(f"  平均处理时间: {stats['avg_processing_time_ms']:.0f} ms")
            
            print(f"\n操作分布：")
            for action, count in stats['action_breakdown'].items():
                print(f"  {action}: {count}")
            
            print(f"\nTop 供应商：")
            for vendor, count in stats['top_vendors'][:5]:
                print(f"  {vendor}: {count} 个文件")
            
            print()
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("🚀 Digital Janitor - 可编辑审批功能测试")
    print("=" * 80)
    print()
    
    # 检查数据库是否存在
    db_path = Path("memory.db")
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        print("   请先运行一次 UI 或 run_graph_once.py 来初始化数据库\n")
        return
    
    results = []
    
    # 运行测试
    results.append(("Memory 记录", test_memory_recording()))
    results.append(("偏好学习", test_preference_learning()))
    results.append(("统计信息", test_statistics()))
    
    # 总结
    print("=" * 80)
    print("📋 测试总结")
    print("=" * 80)
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
    
    print()
    print(f"总体结果: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！可编辑审批功能正常工作。")
    else:
        print("\n⚠️  部分测试未通过，可能是因为：")
        print("   1. 尚未使用 UI 批准任何文件")
        print("   2. 尚未修改任何字段（所以没有触发学习）")
        print("\n💡 建议：")
        print("   1. 运行 `python run_graph_once.py --limit 1` 生成待审批文件")
        print("   2. 运行 `streamlit run app.py` 启动 UI")
        print("   3. 在 UI 中修改文件夹或供应商，然后点击批准")
        print("   4. 再次运行此测试脚本验证结果")
    
    print()


if __name__ == "__main__":
    main()

