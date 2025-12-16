# 快速开始

## 5 分钟上手

### 1. 安装（2 分钟）

```bash
# 克隆项目
git clone https://github.com/your-username/digital-janitor.git
cd digital-janitor

# 创建环境并安装依赖
conda create -n janitor python=3.10
conda activate janitor
pip install -r requirements.txt

# 配置 API Key
echo "OPENAI_API_KEY=your-key-here" > .env
```

### 2. 准备测试文件（30 秒）

```bash
# 将一些文件放入 inbox 目录
# 比如：PDF、Word、PPT、图片等
```

### 3. 启动使用（2 分钟）

```bash
# 生成待审批文件
python run_graph_once.py --limit 5

# 启动 Web UI
streamlit run app.py
# 或使用快捷脚本（Windows）
start_ui.bat

# 浏览器打开 http://localhost:8501
# 点击"批准"或"拒绝"按钮即可！
```

---

## 三种使用模式

### 模式 1: Web UI（推荐新手）

```bash
python run_graph_once.py --limit 10  # 生成待审批
streamlit run app.py                 # 启动界面
```

**优点：** 可视化、安全、直观

---

### 模式 2: 命令行（快速批处理）

```bash
# 安全预览
python run_graph_once.py --limit 10

# 自动批准
python run_graph_once.py --auto-approve --execute
```

**优点：** 快速、适合批量处理

---

### 模式 3: 文件监听（实时整理）

```bash
# 终端 1：启动监听器
python watch_inbox.py

# 终端 2：启动 UI 审批
streamlit run app.py
```

**优点：** 自动化、适合日常使用

---

## 常用命令

```bash
# 查看帮助
python run_graph_once.py --help

# 限制处理数量
python run_graph_once.py --limit 5

# 自动批准模式
python run_graph_once.py --auto-approve

# 真实执行（移动文件）
python run_graph_once.py --execute

# 组合使用
python run_graph_once.py --limit 10 --auto-approve --execute
```

---

## 目录说明

- `inbox/` - 放待整理的文件
- `archive/` - 已整理的文件
- `pending/` - 待审批的 JSON
- `logs/` - 操作日志

---

## 下一步

- 查看 [详细文档](docs/GUIDE.md)
- 了解 [技术架构](docs/ARCHITECTURE.md)
- 运行 [测试示例](examples/)

---

**Have Fun!** 🎉

