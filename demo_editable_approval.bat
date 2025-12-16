@echo off
chcp 65001 > nul
echo ================================================================================
echo 🚀 Digital Janitor - 可编辑审批功能演示
echo ================================================================================
echo.

echo [1/3] 生成测试待审批文件...
echo.
python run_graph_once.py --limit 3
echo.

if %ERRORLEVEL% NEQ 0 (
    echo ❌ 生成失败，请检查错误信息
    pause
    exit /b 1
)

echo ✅ 已生成待审批文件
echo.
echo [2/3] 启动 Web UI...
echo.
echo 💡 提示：
echo    1. 浏览器会自动打开 http://localhost:8501
echo    2. 在 UI 中修改字段（文件夹、文件名、供应商）
echo    3. 点击 ✅ 批准 按钮
echo    4. 系统会学习你的修改习惯
echo.
echo [3/3] 等待 5 秒后启动...
timeout /t 5 /nobreak > nul
echo.

start /B streamlit run app.py

echo.
echo ================================================================================
echo ✅ UI 已启动！
echo.
echo 📝 使用说明：
echo    - 修改审批信息后点击批准，系统会学习你的偏好
echo    - 运行 'python test_editable_approval.py' 查看学习结果
echo    - 按 Ctrl+C 停止 UI 服务器
echo.
echo 📚 更多帮助：查看 EDITABLE_APPROVAL_GUIDE.md
echo ================================================================================
echo.
pause

