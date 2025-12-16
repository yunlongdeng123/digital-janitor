# Digital Janitor 使用指南

## 快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
conda activate janitor

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### 2. 基础使用

**方式一：Web UI（推荐）**

```bash
# Step 1: 生成待审批文件
python run_graph_once.py --limit 5

# Step 2: 启动 Web 界面
streamlit run app.py

# Step 3: 在浏览器中审批（http://localhost:8501）
```

**方式二：命令行**

```bash
# 预览模式（安全）
python run_graph_once.py --limit 5

# 自动批准
python run_graph_once.py --auto-approve --execute
```

**方式三：文件监听**

```bash
# 启动监听器（自动处理新文件）
python watch_inbox.py

# 在另一个终端启动 UI 审批
streamlit run app.py
```

---

## 详细功能

### Web UI 界面

**侧边栏功能：**
- 📊 待审批数量统计
- 📊 今日已处理数量
- ⚙️ 配置信息显示
- 🚀 快捷操作（刷新、清空隔离区）

**主界面功能：**
- 📋 待审批队列展示
- 📄 文件详细信息（原名、新名、目标目录）
- 🏷️ 分类标签和置信度
- 👁️ 内容预览
- 💡 LLM 分析理由
- ✅ 批准/拒绝/隔离操作
- 🔄 批量操作

**操作按钮：**
| 按钮 | 功能 | 说明 |
|------|------|------|
| ✅ 批准 | 执行文件移动 | 移动到 archive，删除 pending JSON |
| ❌ 拒绝 | 删除待审批项 | 删除 pending JSON，原文件保留 |
| 🗑️ 隔离 | 移动到隔离区 | pending JSON 移到 quarantine |
| ✅ 批准全部 | 批量批准 | 逐个处理所有文件 |
| ❌ 拒绝全部 | 批量拒绝 | 批量移到隔离区 |

---

### 命令行选项

**run_graph_once.py 参数：**

```bash
# 限制处理文件数量
--limit N          处理前 N 个文件

# 自动批准（跳过人工确认）
--auto-approve     自动批准所有合法计划

# 真实执行（否则只生成 pending）
--execute          执行真实文件移动

# 内容预览长度
--max-preview N    提取文本的最大字符数（默认1000）
```

**常用组合：**

```bash
# 安全预览（生成待审批，在 UI 中确认）
python run_graph_once.py --limit 10

# 完全自动（信任模型时使用）
python run_graph_once.py --limit 50 --auto-approve --execute

# 测试单个文件
python run_graph_once.py --limit 1
```

**watch_inbox.py 参数：**

```bash
# 自动批准模式
--auto-approve     监听到新文件后自动批准

# 真实执行模式
--execute          执行真实文件移动

# 文件稳定性等待时间
--stability-wait N 等待 N 秒确认文件传输完成（默认3）
```

---

## 支持的文件类型

| 类别 | 扩展名 | 归档路径示例 | 提取信息 |
|------|--------|-------------|---------|
| 💰 发票 | .pdf | `财务/2024/01/invoice_2024-01_公司名_金额.pdf` | 日期、公司、金额 |
| 📝 合同 | .pdf, .docx | `合同/2024/contract_甲方_乙方_主题_金额.docx` | 甲方、乙方、金额、日期 |
| 📚 论文 | .pdf | `论文/主题分类/2024/paper_标题_作者_年份.pdf` | 标题、作者、年份 |
| 🎨 演示文稿 | .ppt, .pptx | `演示文稿/2024/演示_主题_日期.pptx` | 主题、日期 |
| 🖼️ 图片 | .png, .jpg, .gif | `图片/2024/01/image_描述_日期.jpg` | 日期 |
| 📦 其他 | .txt, .md, .xlsx 等 | `其他/未知年份/default_描述.txt` | 基本信息 |

---

## 配置说明

### config.yaml

```yaml
# 目录配置
paths:
  inbox: inbox              # 待处理文件
  archive: archive          # 归档目录
  logs: logs                # 日志目录

# 支持的文件扩展名
safety:
  allowed_ext:
    - ".pdf"
    - ".docx"
    - ".pptx"
    - ".png"
    # ... 更多

# 命名模板（可自定义）
naming_template:
  invoice:
    pattern: "invoice_{date}_{company}_{amount}.{ext}"
  contract:
    pattern: "contract_{party_a}_{party_b}_{topic}_{amount}.{ext}"
  # ...

# 路由规则（可自定义）
routing:
  invoice:
    target_dir: "财务/{year}/{month}"
  contract:
    target_dir: "合同/{year}"
  # ...
```

### .env 环境变量

```bash
# OpenAI API 配置
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1  # 可选

# LLM 模型选择
LLM_MODEL=gpt-4o-mini  # 或 gpt-4, gpt-3.5-turbo
```

---

## 工作流程

### 典型日常使用流程

```
1. 启动监听器（后台运行）
   └─ python watch_inbox.py

2. 文件进入 inbox
   └─ 手动复制 / 浏览器下载 / 邮件附件

3. 监听器自动处理
   └─ 检测新文件 → LLM 分析 → 生成 pending JSON

4. 定期打开 Web UI 审批
   └─ streamlit run app.py
   └─ 查看文件详情 → 批准或拒绝

5. 文件自动归档到 archive/
   └─ 按分类和年份组织
```

### 批量整理历史文件流程

```
1. 复制文件到 inbox/
   └─ 100+ 个历史文件

2. 生成待审批文件
   └─ python run_graph_once.py --limit 100

3. 启动 Web UI
   └─ streamlit run app.py

4. 查看并批量审批
   └─ 点击"批准全部"（或逐个审批）

5. 完成整理
   └─ 检查 archive/ 目录
```

---

## 日志和追溯

### 日志文件

| 文件 | 内容 | 用途 |
|------|------|------|
| `logs/ui_events.jsonl` | UI 操作记录 | 审批历史追溯 |
| `logs/graph_plan_dryrun_*.jsonl` | Dry-run 记录 | 预览测试 |
| `logs/graph_plan_execute_*.jsonl` | 真实执行记录 | 已移动文件记录 |

### 查看日志

```bash
# 查看最近的 UI 操作
cat logs/ui_events.jsonl | tail -n 10

# 查看今日操作
cat logs/ui_events.jsonl | grep "2024-12-14"

# 使用 jq 格式化（如果安装了 jq）
cat logs/ui_events.jsonl | jq .
```

### 日志格式

```json
{
  "timestamp": "2024-12-14T16:30:45.123456",
  "action": "approve",
  "original_file": "inbox/contract_draft.docx",
  "new_name": "contract_张三_李四_合同草案.docx",
  "category": "contract",
  "result": {
    "status": "success",
    "dst": "archive/合同/2024/contract_张三_李四_合同草案.docx",
    "conflict_resolved": false
  }
}
```

---

## 常见问题

### Q1: UI 上看不到待审批文件？

**原因：** `pending/` 目录为空

**解决：**
```bash
python run_graph_once.py --limit 5
# 然后在 UI 中点击"刷新"
```

### Q2: 批准后文件没有移动？

**检查：**
1. 源文件是否存在
2. 是否有文件占用
3. 磁盘空间是否充足
4. 查看日志：`cat logs/ui_events.jsonl | tail -n 5`

### Q3: 如何恢复误操作？

1. 查看日志找到文件位置
2. 手动移回 inbox
3. 重新处理

### Q4: 分类不准确怎么办？

**短期：** 在 UI 中拒绝，手动整理

**长期：** 优化 Prompt
- 编辑 `core/llm_processor.py`
- 修改 `system_prompt` 中的分类规则
- 添加更多示例或关键词

### Q5: 如何添加新的文件类型？

1. 修改 `config.yaml`：
   - 添加到 `safety.allowed_ext`
   - 添加 `naming_template`
   - 添加 `routing` 规则

2. 修改 `core/schemas.py`：
   - 更新 `category` 枚举

3. 修改 `core/llm_processor.py`：
   - 更新分类规则说明

4. （可选）修改 `utils/file_ops.py`：
   - 添加特殊的文本提取逻辑

---

## 安全建议

### 使用前

1. ✅ **备份重要文件**
2. ✅ **先用 dry-run 测试**
3. ✅ **小批量开始**（`--limit 5`）
4. ✅ **在测试目录验证**

### 使用中

1. ✅ **定期检查 archive 目录**
2. ✅ **查看日志确认操作**
3. ✅ **对重要文件单独审批**
4. ✅ **使用 Web UI 仔细确认**

### 三层安全防护

```
Layer 1: 语义校验 (validator.py)
   └─ 文件名合法性、路径安全性

Layer 2: 人工审批 (HITL)
   └─ 不合法自动拒绝，合法需人工确认

Layer 3: 文件操作 (safe_move_file)
   └─ 冲突自动处理、异常捕获
```

---

## 高级用法

### 局域网访问 UI

```bash
# 启动时允许局域网访问
streamlit run app.py --server.address 0.0.0.0

# 在其他设备访问
http://[你的电脑IP]:8501
```

### 定时任务

**Windows（任务计划程序）：**
```
操作：python run_graph_once.py --auto-approve --execute
触发器：每天 23:00
```

**Linux/Mac（cron）：**
```bash
# 每天 23:00 执行
0 23 * * * cd /path/to/digital-janitor && python run_graph_once.py --auto-approve --execute
```

### 自定义主题

创建 `.streamlit/config.toml`：

```toml
[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

---

## 性能优化

### 当前性能

- 单文件处理：2-5 秒（含 LLM 调用）
- UI 加载：< 1 秒（100 个 pending）
- 文件移动：< 100ms
- 监听器延迟：< 5 秒

### 优化建议

**减少 LLM 调用次数：**
```bash
# 使用更大的 limit 一次处理
python run_graph_once.py --limit 50
```

**缓存机制：**（需开发）
- 相似文件名缓存结果
- 内容哈希去重

---

## 故障排除

### 问题：LLM 调用失败

```bash
# 检查 API Key
cat .env | grep OPENAI_API_KEY

# 测试连接
python -c "from openai import OpenAI; OpenAI().models.list()"
```

### 问题：文件监听不工作

```bash
# 检查 watchdog 安装
python -c "import watchdog; print('OK')"

# 查看监听器日志
# 监听器终端会显示检测到的文件
```

### 问题：UI 无法访问

```bash
# 检查端口占用
netstat -an | findstr 8501

# 更换端口
streamlit run app.py --server.port 8080
```

---

## 下一步

- 查看 [技术架构](./ARCHITECTURE.md) 了解系统设计
- 查看 [examples/](../examples/) 目录的测试脚本
- 修改 `config.yaml` 自定义分类规则
- 根据需求扩展新功能

如有问题，请查看项目 [README.md](../README.md) 或提交 Issue。

