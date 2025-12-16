@echo off
chcp 65001 > nul
echo ================================================================================
echo 🚀 Digital Janitor - OCR V2 功能演示
echo ================================================================================
echo.

echo 💡 本演示将展示 OCR V2 的三大新功能：
echo    1. 📦 本地缓存（避免重复处理）
echo    2. 🖼️  图片支持（PNG/JPG/WebP）
echo    3. 📊 质量评分（自动评估结果质量）
echo.

echo [1/2] 运行功能测试...
echo.
python test_ocr_v2.py
echo.

if %ERRORLEVEL% NEQ 0 (
    echo ❌ 测试失败，请检查错误信息
    pause
    exit /b 1
)

echo ================================================================================
echo.
echo [2/2] 使用建议
echo.
echo 📚 详细文档：
echo    - OCR_V2_GUIDE.md        # 用户使用指南
echo    - CHANGELOG_OCR_V2.md    # 技术更新日志
echo.
echo 🔧 配置调整（如需）：
echo    编辑 config\ocr_config.py
echo    - enable_rapidocr: 启用/禁用 RapidOCR
echo    - rapidocr_dpi: 调整图片分辨率（影响质量和速度）
echo    - rapidocr_max_pages: 最大处理页数
echo.
echo 💾 缓存管理：
echo    - 位置: %USERPROFILE%\.digital_janitor\ocr_cache.db
echo    - 清空: 运行以下 Python 代码
echo      from utils.file_ops import OCRCache; OCRCache().clear()
echo.
echo 📈 性能提升：
echo    - 缓存未命中: 1000-5000ms（取决于文件大小）
echo    - 缓存命中: ^< 10ms（10-100倍加速）
echo.
echo ================================================================================
echo ✅ 演示完成！
echo.
pause

