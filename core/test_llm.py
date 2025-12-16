#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM 处理器测试脚本
用于验证 LLM 调用是否正常工作
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from core.llm_processor import analyze_file


def test_llm_basic():
    """基础测试：发票文档"""
    print("=" * 60)
    print("测试 1: 发票文档分析")
    print("=" * 60)
    
    text = """
    发票测试文档
    
    开票日期: 2024年3月15日
    价税合计: ¥1,580.00元
    税号: 91110000123456789X
    购方: 北京科技有限公司
    销方: 阿里云计算有限公司
    
    这是一张增值税专用发票。
    """
    
    filename = "test_invoice.txt"
    
    try:
        result = analyze_file(text, filename)
        print(f"\n✅ 分析成功！")
        print(f"  - 类别: {result.category}")
        print(f"  - 置信度: {result.confidence:.2f}")
        print(f"  - 日期: {result.extracted_date}")
        print(f"  - 金额: {result.extracted_amount}")
        print(f"  - 供应商: {result.vendor_or_party}")
        print(f"  - 标题: {result.title}")
        print(f"  - 建议文件名: {result.suggested_filename}")
        print(f"  - 理由: {result.rationale}")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False


def test_llm_contract():
    """测试 2: 合同文档"""
    print("\n" + "=" * 60)
    print("测试 2: 合同文档分析")
    print("=" * 60)
    
    text = """
    劳动合同
    
    甲方（用人单位）：ABC科技有限公司
    乙方（劳动者）：张三
    
    根据《中华人民共和国劳动合同法》及相关法律法规的规定，
    甲乙双方在平等自愿、协商一致的基础上，就乙方到甲方工作事宜，
    订立本劳动合同。
    
    签订日期：2024年1月10日
    生效日期：2024年2月1日
    """
    
    filename = "labor_contract.pdf"
    
    try:
        result = analyze_file(text, filename)
        print(f"\n✅ 分析成功！")
        print(f"  - 类别: {result.category}")
        print(f"  - 置信度: {result.confidence:.2f}")
        print(f"  - 日期: {result.extracted_date}")
        print(f"  - 对方: {result.vendor_or_party}")
        print(f"  - 标题: {result.title}")
        print(f"  - 建议文件名: {result.suggested_filename}")
        print(f"  - 理由: {result.rationale}")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False


def test_llm_empty():
    """测试 3: 空内容（仅文件名）"""
    print("\n" + "=" * 60)
    print("测试 3: 空内容分析（仅文件名）")
    print("=" * 60)
    
    text = ""
    filename = "invoice_2024_03.pdf"
    
    try:
        result = analyze_file(text, filename)
        print(f"\n✅ 分析成功！")
        print(f"  - 类别: {result.category}")
        print(f"  - 置信度: {result.confidence:.2f}")
        print(f"  - 建议文件名: {result.suggested_filename}")
        print(f"  - 理由: {result.rationale}")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False


def main():
    """主函数"""
    print("\n🚀 LLM 处理器测试")
    print(f"📍 项目根目录: {project_root}")
    
    # 加载环境变量
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量: {env_path}")
    else:
        print(f"⚠️  未找到 .env 文件: {env_path}")
        print(f"💡 提示: 请复制 .env.example 为 .env 并配置 API 密钥")
        return 1
    
    # 检查必要的环境变量
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-your-api-key-here":
        print(f"❌ 错误: 未设置有效的 OPENAI_API_KEY")
        print(f"💡 请在 .env 文件中配置你的 API 密钥")
        return 1
    
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    api_base = os.getenv("OPENAI_API_BASE", "默认")
    
    print(f"📋 配置信息:")
    print(f"  - 模型: {model}")
    print(f"  - API Base: {api_base}")
    print(f"  - API Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    # 运行测试
    results = []
    results.append(test_llm_basic())
    results.append(test_llm_contract())
    results.append(test_llm_empty())
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("✅ 所有测试通过！LLM 处理器工作正常 🎉")
        return 0
    else:
        print(f"⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

