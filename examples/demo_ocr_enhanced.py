"""
OCR 增强功能演示脚本
展示如何使用智能 PDF 识别功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.file_ops import extract_text_preview_enhanced, should_use_ocr
from config.ocr_config import OCR_CONFIG, update_ocr_config


def demo_basic_usage():
    """基础使用演示"""
    print("=" * 60)
    print("演示 1: 基础使用")
    print("=" * 60)
    
    # 假设有一个测试 PDF
    test_pdf = Path("inbox/test.pdf")
    
    if not test_pdf.exists():
        print(f"⚠️  测试文件不存在: {test_pdf}")
        print("请在 inbox/ 目录放置一个 PDF 文件进行测试")
        return
    
    print(f"\n📄 正在处理: {test_pdf.name}")
    
    # 调用增强版提取
    result = extract_text_preview_enhanced(test_pdf)
    
    # 显示结果
    print(f"\n📊 提取结果:")
    print(f"  方法: {result['method']}")
    print(f"  置信度: {result['confidence']:.2f}")
    print(f"  页数: {result['page_count']}")
    print(f"  字符数: {result['char_count']}")
    print(f"  处理耗时: {result['processing_time_ms']}ms")
    
    if result['error']:
        print(f"  ❌ 错误: {result['error']}")
    
    print(f"\n📝 文本预览 (前 300 字符):")
    print("-" * 60)
    print(result['text'][:300])
    print("-" * 60)


def demo_should_use_ocr():
    """OCR 触发条件演示"""
    print("\n" + "=" * 60)
    print("演示 2: OCR 触发条件测试")
    print("=" * 60)
    
    test_cases = [
        ("正常文本", "This is a normal PDF with plenty of text. " * 50, 2),
        ("空文本", "", 1),
        ("低密度文本", "Page\n" * 20, 5),
        ("大量空白", " " * 900 + "text" * 25, 1),
    ]
    
    for name, text, page_count in test_cases:
        needs_ocr, reason = should_use_ocr(text, page_count)
        status = "✅ 需要 OCR" if needs_ocr else "❌ 不需要"
        print(f"\n{name}:")
        print(f"  {status}")
        print(f"  原因: {reason}")


def demo_config():
    """配置演示"""
    print("\n" + "=" * 60)
    print("演示 3: 配置管理")
    print("=" * 60)
    
    print("\n📋 当前配置:")
    print(f"  RapidOCR 最大页数: {OCR_CONFIG.rapidocr_max_pages}")
    print(f"  RapidOCR DPI: {OCR_CONFIG.rapidocr_dpi}")
    print(f"  Vision LLM 最大页数: {OCR_CONFIG.vision_max_pages}")
    print(f"  Vision LLM 启用: {OCR_CONFIG.enable_vision_llm}")
    print(f"  RapidOCR 启用: {OCR_CONFIG.enable_rapidocr}")
    
    print("\n🔧 修改配置:")
    update_ocr_config(
        rapidocr_max_pages=20,
        enable_vision_llm=False
    )
    print(f"  RapidOCR 最大页数: {OCR_CONFIG.rapidocr_max_pages} (已更新)")
    print(f"  Vision LLM 启用: {OCR_CONFIG.enable_vision_llm} (已更新)")
    
    # 恢复默认设置
    update_ocr_config(
        rapidocr_max_pages=10,
        enable_vision_llm=True
    )
    print("\n✅ 配置已恢复默认值")


def demo_batch_processing():
    """批量处理演示"""
    print("\n" + "=" * 60)
    print("演示 4: 批量处理 PDF")
    print("=" * 60)
    
    inbox = Path("inbox")
    pdf_files = list(inbox.glob("*.pdf"))
    
    if not pdf_files:
        print("⚠️  inbox/ 目录中没有 PDF 文件")
        return
    
    print(f"\n找到 {len(pdf_files)} 个 PDF 文件:")
    
    for pdf_file in pdf_files[:5]:  # 只处理前 5 个
        print(f"\n📄 {pdf_file.name}")
        result = extract_text_preview_enhanced(pdf_file)
        
        print(f"  方法: {result['method']}")
        print(f"  置信度: {result['confidence']:.2f}")
        print(f"  字符数: {result['char_count']}")
        print(f"  耗时: {result['processing_time_ms']}ms")


def main():
    """主函数"""
    print("\n" + "🔍" * 30)
    print("Digital Janitor - OCR 增强功能演示")
    print("🔍" * 30)
    
    try:
        # 运行所有演示
        demo_basic_usage()
        demo_should_use_ocr()
        demo_config()
        demo_batch_processing()
        
        print("\n" + "✅" * 30)
        print("演示完成！")
        print("✅" * 30)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  演示已中断")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

