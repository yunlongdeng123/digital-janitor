@echo off
REM Step 4 HITL 功能演示脚本
REM 使用方法：在 PowerShell 或 CMD 中运行此脚本

echo ====================================================
echo Digital Janitor - HITL 功能演示
echo ====================================================
echo.

echo [测试 1] 自动批准模式（适合录制演示视频）
echo 命令：python run_graph_once.py --limit 3 --auto-approve
echo.
pause

call conda activate janitor
python run_graph_once.py --limit 3 --auto-approve

echo.
echo ====================================================
echo.
echo [测试 2] 交互式确认模式（真实使用场景）
echo 命令：python run_graph_once.py --limit 3
echo 提示：看到确认提示时，输入 y 批准，n 或回车拒绝
echo.
pause

python run_graph_once.py --limit 3

echo.
echo ====================================================
echo 演示完成！请查看 logs/ 目录下的 JSONL 文件
echo ====================================================
pause

