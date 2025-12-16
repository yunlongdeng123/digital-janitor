# 📁 Digital Janitor

智能文件整理助手 - 基于 LangGraph 和 LLM 的自动化文件管理系统

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ 特性

- 🤖 **AI 智能分类** - 基于 LLM 的语义理解，自动识别发票、合同、论文、演示文稿等
- 📝 **智能重命名** - 自动提取关键信息（日期、金额、主题），生成规范化文件名
- 📁 **自动归档** - 按分类和年份自动组织文件结构
- 🤝 **人工审批** - Web UI 可视化审批界面，安全可控
- 👀 **实时监听** - 自动检测新文件，后台处理
- 🔒 **安全可靠** - 三层防护机制，完整操作日志
- 🔍 **智能 OCR** - 自动识别扫描件 PDF，支持 RapidOCR 和 Vision LLM
- 🧠 **偏好学习** - 自动学习用户习惯，优化后续建议 ⭐ NEW

---

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/digital-janitor.git
cd digital-janitor

# 创建虚拟环境
conda create -n janitor python=3.10
conda activate janitor

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### 使用

**Web UI 模式（推荐）：**

```bash
# 1. 生成待审批文件
python run_graph_once.py --limit 5

# 2. 启动 Web 界面
streamlit run app.py
# 或使用快捷脚本
start_ui.bat

# 3. 在浏览器中审批（http://localhost:8501）
```

**命令行模式：**

```bash
# 预览模式（生成待审批，不移动文件）
python run_graph_once.py --limit 10

# 自动批准模式
python run_graph_once.py --auto-approve --execute
```

**文件监听模式：**

```bash
# 启动监听器，自动处理新文件
python watch_inbox.py

# 在另一个终端启动 UI 进行审批
streamlit run app.py
```

---

## 📂 项目结构

```
digital-janitor/
├── core/                   # 核心模块
│   ├── llm_processor.py    # LLM 分析引擎
│   ├── schemas.py          # 数据结构定义
│   └── validator.py        # 安全校验器
├── utils/                  # 工具函数
│   └── file_ops.py         # 文件操作
├── docs/                   # 文档
│   ├── GUIDE.md            # 使用指南
│   └── ARCHITECTURE.md     # 技术架构
├── examples/               # 示例和测试
├── inbox/                  # 待处理文件（输入）
├── archive/                # 已归档文件（输出）
├── pending/                # 待审批文件
├── logs/                   # 日志文件
├── run_graph_once.py       # 命令行工具
├── watch_inbox.py          # 文件监听器
├── app.py                  # Web UI
├── config.yaml             # 配置文件
└── requirements.txt        # 依赖列表
```

---

## 📊 支持的文件类型

| 类别 | 扩展名 | 归档示例 |
|------|--------|---------|
| 💰 发票 | `.pdf` | `财务/2024/01/invoice_2024-01_公司名_金额.pdf` |
| 📝 合同 | `.pdf`, `.docx` | `合同/2024/contract_甲方_乙方_主题.docx` |
| 📚 论文 | `.pdf` | `论文/AI研究/2024/paper_标题_作者.pdf` |
| 🎨 演示文稿 | `.ppt`, `.pptx` | `演示文稿/2024/演示_主题_日期.pptx` |
| 🖼️ 图片 | `.png`, `.jpg` | `图片/2024/01/image_描述.jpg` |

---

## 🎨 Web UI 功能

### 侧边栏
- 📊 待审批/已处理统计
- ⚙️ 配置信息显示
- 🚀 快捷操作

### 主界面
- 📋 待审批队列
- 📄 文件详情展示
- 👁️ 内容预览
- 💡 LLM 分析理由
- ✅ 批准/拒绝/隔离操作
- 🔄 批量操作支持

---

## 🛠️ 技术栈

- **AI 框架：** LangGraph, LangChain, OpenAI
- **Web UI：** Streamlit
- **文档处理：** pypdf, python-docx, python-pptx
- **文件监听：** watchdog
- **数据验证：** Pydantic

---

## 📚 文档

- [使用指南](docs/GUIDE.md) - 详细的使用说明和配置
- [技术架构](docs/ARCHITECTURE.md) - 系统设计和技术细节
- [OCR 增强功能](docs/OCR_ENHANCEMENT.md) - 智能 PDF 识别说明
- [Memory 系统](docs/MEMORY_SYSTEM.md) - 审批日志和偏好学习 ⭐ NEW
- [示例代码](examples/) - 测试脚本和示例

---

## 🔒 安全特性

### 三层防护机制

1. **语义校验** - 文件名合法性、路径安全性检查
2. **人工审批** - 不合法自动拒绝，合法需人工确认
3. **文件操作** - 冲突自动处理，异常完整捕获

### 完整日志追溯

- `logs/ui_events.jsonl` - UI 操作记录
- `logs/graph_plan_*.jsonl` - 工作流执行记录
- 所有操作包含时间戳、文件路径、结果详情

---

## 📈 使用场景

- 📁 **个人文件管理** - 整理下载文件、截图、文档
- 🏢 **企业文档归档** - 合同、发票、报告自动分类
- 📚 **学术资料整理** - 论文、笔记、PPT 按主题归档
- 💼 **商业文档管理** - 客户资料、项目文档自动整理

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

[MIT License](LICENSE)

---

## 🙏 致谢

基于以下优秀的开源项目：
- [LangGraph](https://github.com/langchain-ai/langgraph) - AI 工作流编排
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [Streamlit](https://streamlit.io/) - Web UI 框架

---

**让 AI 帮你整理文件，解放双手！** ✨
