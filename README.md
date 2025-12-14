# Smart File Organizer

一个基于 AI 的智能文件整理助手，能够自动识别、分类和重命名各类文档。

## 项目目标

利用 LangGraph 和大语言模型，构建一个智能文件管理系统，能够：

- 📄 自动识别文件类型（发票、合同、论文、图片等）
- 🏷️ 智能提取文件关键信息（日期、金额、主题等）
- 📝 按照预设规则重命名文件
- 📁 自动归档到对应目录
- 🔍 提供文件预览和干运行模式

## 目录结构

```
digital-janitor/
├── inbox/          # 收件箱：存放待处理的文件
├── archive/        # 归档区：已处理并重命名的文件
├── quarantine/     # 隔离区：无法识别或处理失败的文件
├── logs/           # 日志目录：记录处理过程和错误
├── config.yaml     # 配置文件：路径、规则等设置
└── requirements.txt # Python 依赖包
```

## 快速开始

### 方式一：使用 venv（推荐）

1. **创建虚拟环境**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

### 方式二：使用 Conda

1. **创建 Conda 环境**
   ```bash
   conda create -n janitor python=3.10
   conda activate janitor
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

### 配置与运行

3. **配置文件**
   
   编辑 `config.yaml`，根据需要调整命名规则和路径。
   
   设置 `dry_run: true` 可以先预览效果，不实际移动文件。

4. **验证环境**
   ```bash
   python utils/check_setup.py
   ```

5. **放入测试文件**
   
   将需要整理的文件放入 `inbox/` 目录。

6. **运行程序**
   ```bash
   python run_once.py  # 单次运行模式
   # python watch_mode.py  # 监听模式（待开发）
   ```

## 技术栈

- **LangGraph**: AI 工作流编排
- **Pydantic**: 数据验证和类型安全
- **PyPDF & python-docx**: 文档内容提取
- **Loguru**: 优雅的日志记录
- **YAML**: 配置文件管理
- **Watchdog**: 文件系统监听
- **python-dotenv**: 环境变量管理

## 开发状态

🚧 项目初始化完成，核心功能开发中...

## 许可

MIT License

