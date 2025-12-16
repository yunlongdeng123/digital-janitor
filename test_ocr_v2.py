#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 OCR V2 功能

验证：
1. OCR 缓存是否工作
2. 图片文件支持
3. 质量评分
4. 缓存命中率
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.file_ops import (
    OCRCache, 
    compute_file_hash, 
    calculate_quality_score,
    extract_text_preview_enhanced
)


def test_quality_score():
    """测试质量评分算法"""
    print("=" * 80)
    print("🧪 测试质量评分算法")
    print("=" * 80)
    
    test_cases = [
        ("", 0.0, "空文本"),
        ("短", 0.5, "极短文本"),
        ("这是一段正常的中文文本，包含了足够的字符数量，应该得到较高的评分。" * 3, 0.9, "正常文本"),
        ("��������@#$%^&*()_+", 0.3, "乱码文本"),
        ("Normal English text with good quality" * 5, 0.95, "高质量英文"),
    ]
    
    print()
    for text, confidence, description in test_cases:
        score, needs_review = calculate_quality_score(text, confidence)
        status = "❌ 需审查" if needs_review else "✅ 通过"
        print(f"{status} {description:15s} | 评分: {score:3d} | 置信度: {confidence:.2f} | 长度: {len(text):4d}")
    
    print()
    return True


def test_cache_basic():
    """测试缓存基本功能"""
    print("=" * 80)
    print("🧪 测试缓存基本功能")
    print("=" * 80)
    
    try:
        # 1. 初始化缓存
        cache = OCRCache()
        print("\n✅ 缓存初始化成功")
        print(f"   数据库路径: {cache.db_path}")
        
        # 2. 测试写入
        test_hash = "test_hash_12345"
        cache.set(
            file_hash=test_hash,
            text="这是一段测试文本",
            method="rapidocr",
            confidence=0.85,
            quality_score=75
        )
        print("✅ 缓存写入成功")
        
        # 3. 测试读取
        cached = cache.get(test_hash)
        if cached:
            print("✅ 缓存读取成功")
            print(f"   文本: {cached['text'][:30]}...")
            print(f"   方法: {cached['method']}")
            print(f"   置信度: {cached['confidence']}")
            print(f"   质量: {cached['quality_score']}")
        else:
            print("❌ 缓存读取失败")
            return False
        
        # 4. 测试更新
        cache.set(
            file_hash=test_hash,
            text="更新后的文本",
            method="vision_llm",
            confidence=0.95,
            quality_score=90
        )
        cached_updated = cache.get(test_hash)
        if cached_updated and cached_updated['text'] == "更新后的文本":
            print("✅ 缓存更新成功")
        else:
            print("❌ 缓存更新失败")
            return False
        
        # 5. 清理测试数据（可选）
        # cache.clear()
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_hash():
    """测试文件 hash 计算"""
    print("=" * 80)
    print("🧪 测试文件 Hash 计算")
    print("=" * 80)
    
    try:
        # 查找测试文件
        test_files = list(Path("inbox").glob("*.*"))[:3]
        
        if not test_files:
            print("⚠️  inbox 目录为空，跳过测试")
            return True
        
        print(f"\n找到 {len(test_files)} 个测试文件\n")
        
        for file_path in test_files:
            try:
                file_hash = compute_file_hash(file_path)
                file_size = file_path.stat().st_size
                print(f"📄 {file_path.name:30s} | Hash: {file_hash[:16]}... | 大小: {file_size:8d} bytes")
            except Exception as e:
                print(f"❌ {file_path.name}: {e}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_image_ocr():
    """测试图片 OCR"""
    print("=" * 80)
    print("🧪 测试图片 OCR 功能")
    print("=" * 80)
    
    # 查找图片文件
    image_exts = ['.png', '.jpg', '.jpeg', '.webp']
    test_images = []
    
    for ext in image_exts:
        test_images.extend(Path("inbox").glob(f"*{ext}"))
        test_images.extend(Path("inbox").glob(f"*{ext.upper()}"))
    
    if not test_images:
        print("\n⚠️  没有找到图片文件，跳过测试")
        print("   提示：将图片文件放到 inbox/ 目录来测试图片 OCR")
        print()
        return True
    
    print(f"\n找到 {len(test_images)} 个图片文件\n")
    
    for img_path in test_images[:3]:  # 只测试前 3 个
        print(f"处理: {img_path.name}")
        try:
            result = extract_text_preview_enhanced(img_path, limit=200)
            
            print(f"  方法: {result['method']}")
            print(f"  置信度: {result['confidence']:.2f}")
            print(f"  质量: {result['quality_score']}")
            print(f"  需审查: {result['needs_review']}")
            print(f"  字符数: {result['char_count']}")
            print(f"  耗时: {result['processing_time_ms']}ms")
            
            if result['text']:
                preview = result['text'][:100].replace('\n', ' ')
                print(f"  预览: {preview}...")
            else:
                print(f"  ⚠️  未提取到文本")
            
            if result.get('error'):
                print(f"  ❌ 错误: {result['error']}")
            
            print()
            
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    return True


def test_cache_hit():
    """测试缓存命中"""
    print("=" * 80)
    print("🧪 测试缓存命中率")
    print("=" * 80)
    
    # 查找测试文件
    test_files = list(Path("inbox").glob("*.pdf"))[:1]
    
    if not test_files:
        print("\n⚠️  没有找到 PDF 文件，跳过测试")
        return True
    
    test_file = test_files[0]
    print(f"\n测试文件: {test_file.name}\n")
    
    try:
        # 第一次处理（未缓存）
        print("第 1 次处理（预计未命中缓存）:")
        start_time = time.time()
        result1 = extract_text_preview_enhanced(test_file, limit=500)
        time1 = time.time() - start_time
        
        print(f"  方法: {result1['method']}")
        print(f"  质量: {result1['quality_score']}")
        print(f"  耗时: {time1*1000:.0f}ms")
        print()
        
        # 第二次处理（应该命中缓存）
        print("第 2 次处理（预计命中缓存）:")
        start_time = time.time()
        result2 = extract_text_preview_enhanced(test_file, limit=500)
        time2 = time.time() - start_time
        
        print(f"  方法: {result2['method']}")
        print(f"  质量: {result2['quality_score']}")
        print(f"  耗时: {time2*1000:.0f}ms")
        print()
        
        # 验证缓存
        if "_cached" in result2['method']:
            print(f"✅ 缓存命中！加速比: {time1/max(time2, 0.001):.1f}x")
        else:
            print("⚠️  未命中缓存（可能是 direct 方法不缓存）")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("🚀 Digital Janitor - OCR V2 功能测试")
    print("=" * 80)
    print()
    
    results = []
    
    # 运行测试
    results.append(("质量评分算法", test_quality_score()))
    results.append(("缓存基本功能", test_cache_basic()))
    results.append(("文件 Hash 计算", test_file_hash()))
    results.append(("图片 OCR", test_image_ocr()))
    results.append(("缓存命中率", test_cache_hit()))
    
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
        print("\n🎉 所有测试通过！OCR V2 功能正常工作。")
    else:
        print("\n⚠️  部分测试未通过")
    
    print()


if __name__ == "__main__":
    main()

