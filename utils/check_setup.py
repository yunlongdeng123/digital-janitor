#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
环境配置验证脚本
用于检查项目依赖和配置文件是否正确安装/配置
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


def check_imports():
    """检查关键依赖包是否已安装"""
    print("=" * 50)
    print("🔍 检查依赖包...")
    print("=" * 50)
    
    required_packages = [
        "langgraph",
        "pydantic",
        "pypdf",
        "docx",  # python-docx
        "yaml",  # pyyaml
        "loguru",
        "watchdog",
        "dotenv",  # python-dotenv
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package:15s} - 已安装")
        except ImportError:
            print(f"❌ {package:15s} - 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print("\n⚠️  警告: 以下包未安装，请运行:")
        print("   pip install -r requirements.txt")
        return False
    else:
        print("\n✅ Imports OK - 所有依赖包已正确安装")
        return True


def check_config():
    """检查配置文件是否存在且可读取"""
    print("\n" + "=" * 50)
    print("🔍 检查配置文件...")
    print("=" * 50)
    
    try:
        import yaml
        
        # 查找 config.yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        
        if not config_path.exists():
            print(f"❌ 配置文件不存在: {config_path}")
            return False
        
        print(f"✅ 配置文件存在: {config_path}")
        
        # 尝试读取配置
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        print(f"✅ 配置文件可读取")
        
        # 检查关键配置项
        print("\n📋 配置内容概览:")
        if "paths" in config:
            print(f"   - paths: {list(config['paths'].keys())}")
        if "dry_run" in config:
            print(f"   - dry_run: {config['dry_run']}")
        if "routing" in config:
            print(f"   - routing: {list(config['routing'].keys())} ({len(config['routing'])} 条规则)")
        if "safety" in config:
            print(f"   - safety: 已配置 ({len(config['safety'])} 项)")
            if "allowed_ext" in config["safety"]:
                print(f"     允许扩展名: {len(config['safety']['allowed_ext'])} 种")
        
        print("\n✅ Config OK - 配置文件读取成功")
        return True
        
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return False


def check_directories():
    """检查必要的目录是否存在"""
    print("\n" + "=" * 50)
    print("🔍 检查目录结构...")
    print("=" * 50)
    
    required_dirs = ["inbox", "archive", "quarantine", "logs"]
    project_root = Path(__file__).parent.parent
    
    all_exist = True
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"✅ {dir_name:15s} - 存在")
        else:
            print(f"❌ {dir_name:15s} - 不存在")
            all_exist = False
    
    if all_exist:
        print("\n✅ Directories OK - 所有目录已创建")
    else:
        print("\n⚠️  警告: 部分目录不存在")
    
    return all_exist


def main():
    """主函数"""
    print("\n🚀 Smart File Organizer - 环境配置检查")
    print(f"📍 Python 版本: {sys.version}")
    print()
    
    # 执行检查
    imports_ok = check_imports()
    config_ok = check_config()
    dirs_ok = check_directories()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 检查结果总结")
    print("=" * 50)
    
    if imports_ok and config_ok and dirs_ok:
        print("✅ 环境配置完美！可以开始开发了 🎉")
        return 0
    else:
        print("⚠️  环境配置存在问题，请根据上述提示修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())

