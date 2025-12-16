# Digital Janitor 技术架构

## 系统概览

Digital Janitor 是一个基于 LangGraph 的智能文件整理系统，采用状态机工作流设计，实现从文件检测到自动归档的完整流程。

### 核心特性

- **状态机工作流：** 使用 LangGraph StateGraph 编排处理流程
- **LLM 智能分类：** 基于文件内容的语义理解和分类
- **非阻塞审批：** pending 机制支持异步人工确认
- **多模态支持：** PDF、Word、PPT、图片等多种文件格式
- **安全可靠：** 三层防护机制，完整日志追溯

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层                             │
├────────────────┬───────────────────┬────────────────────────┤
│  Web UI        │  命令行工具        │  文件监听器             │
│  (Streamlit)   │  (CLI)            │  (Watchdog)            │
└────────┬───────┴───────┬───────────┴────────┬───────────────┘
         │               │                     │
         └───────────────┼─────────────────────┘
                         │
         ┌───────────────▼───────────────┐
         │      JanitorWorkflow 类        │
         │    (核心工作流引擎)            │
         └───────────────┬───────────────┘
                         │
         ┌───────────────▼───────────────┐
         │      LangGraph StateGraph     │
         │    (状态机工作流)              │
         └───────────────┬───────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
┌───▼────┐       ┌──────▼─────┐      ┌──────▼─────┐
│ LLM    │       │ File Ops   │      │ Validator  │
│ 处理器  │       │ 文件操作    │      │ 校验器      │
└────────┘       └────────────┘      └────────────┘
    │                    │                    │
    └────────────────────┼────────────────────┘
                         │
         ┌───────────────▼───────────────┐
         │      文件系统 & 日志            │
         │  inbox/  archive/  logs/      │
         │  pending/  quarantine/        │
         └───────────────────────────────┘
```

---

## 核心模块

### 1. 工作流引擎（run_graph_once.py）

**JanitorWorkflow 类：**
```python
class JanitorWorkflow:
    def __init__(self, config_path, env_path)
        # 加载配置、编译 LangGraph
    
    def process_file(self, file_path, dry_run, auto_approve, max_preview)
        # 处理单个文件的完整流程
        # 返回处理结果
```

**核心职责：**
- 封装 LangGraph 工作流
- 管理配置和状态
- 提供统一的文件处理接口
- 支持 dry-run 和 execute 模式

---

### 2. LangGraph 状态图

**状态定义（JanitorState）：**
```python
class JanitorState(TypedDict):
    file_path: Path          # 文件路径
    preview: str             # 内容预览
    analysis: FileAnalysis   # LLM 分析结果
    plan: RenamePlan         # 重命名计划
    is_valid: bool           # 校验结果
    decision: str            # 审批决策
    approved: bool           # 是否批准
    move_result: dict        # 移动结果
    # ... 配置和上下文
```

**节点流程：**
```
node_extract_preview    # 1. 提取文件预览
         ↓
node_llm_analyze        # 2. LLM 分析分类
         ↓
node_build_plan         # 3. 构建重命名计划
         ↓
node_validate           # 4. 校验合法性
         ↓
route_after_validate    # 5. 路由判断
    ├─ invalid → node_skip
    └─ valid → node_decide_approval
                    ↓
         route_after_decision
    ├─ pending → END (生成 pending JSON)
    ├─ rejected → node_skip
    └─ approved → node_apply (执行移动)
```

**关键特性：**
- **条件分支：** 根据校验和审批结果动态路由
- **状态传递：** 所有节点共享 TypedDict 状态
- **可扩展：** 易于添加新节点和分支

---

### 3. LLM 处理器（core/llm_processor.py）

**核心函数：**
```python
def analyze_file(filename: str, preview: str) -> FileAnalysis:
    """
    使用 LLM 分析文件
    
    输入：文件名 + 内容预览
    输出：结构化的 FileAnalysis 对象
    """
    # 1. 构建 Prompt
    # 2. 调用 LLM（with_structured_output）
    # 3. 返回 Pydantic 对象
```

**Prompt 策略：**
- **系统提示：** 详细的分类规则和示例
- **用户输入：** 文件名 + 内容预览
- **结构化输出：** 使用 Pydantic Schema 约束

**分类规则：**
```python
- invoice (发票): 关键词 - 发票、税号、价税合计
- contract (合同): 关键词 - 合同、甲方、乙方
- paper (论文): 关键词 - abstract, DOI, references
- presentation (演示文稿): 关键词 - 幻灯片、PPT
- image (图片): 文件扩展名
- default (其他): 无法明确分类
```

---

### 4. 数据结构（core/schemas.py）

**FileAnalysis（LLM 输出）：**
```python
class FileAnalysis(BaseModel):
    category: str       # 分类
    confidence: float   # 置信度 (0-1)
    extracted: dict     # 提取的元数据
    rationale: str      # 分析理由
```

**RenamePlan（重命名计划）：**
```python
class RenamePlan(BaseModel):
    category: str       # 分类
    new_name: str       # 新文件名
    dest_dir: str       # 目标目录
    confidence: float   # 置信度
    extracted: dict     # 元数据
```

**优势：**
- **类型安全：** Pydantic 自动验证
- **结构化：** LLM 输出符合 Schema
- **可序列化：** 支持 JSON 导出

---

### 5. 校验器（core/validator.py）

**校验规则：**
```python
def validate_plan(plan: RenamePlan, cfg: dict) -> tuple[bool, str]:
    """
    三层校验：
    1. 文件名合法性（长度、字符）
    2. 路径安全性（不允许 ../ 等）
    3. 字段完整性（必填字段）
    """
```

**安全防护：**
- 文件名长度限制（< 200 字符）
- 禁止特殊字符（`<>:"|?*`）
- 禁止路径遍历（`../`）
- 检查必填字段

---

### 6. 文件操作（utils/file_ops.py）

**核心函数：**

```python
def extract_text_preview(path: Path, limit: int) -> str:
    """
    提取文件文本预览
    支持：PDF, DOCX, PPTX, TXT, MD
    """

def safe_move_file(src: Path, dst: Path) -> dict:
    """
    安全移动文件
    - 创建目标目录
    - 处理文件名冲突（自动添加后缀）
    - 完整异常捕获
    - 返回详细结果
    """

def resolve_collision(destination: Path) -> Path:
    """
    解决文件名冲突
    file.pdf → file_1.pdf → file_2.pdf
    """
```

**冲突处理策略：**
```python
if dst.exists():
    # 添加数字后缀
    # 最多尝试 100 次
    for i in range(1, 100):
        new_name = f"{stem}_{i}{ext}"
        if not new_path.exists():
            return new_path
```

---

### 7. 文件监听器（watch_inbox.py）

**核心组件：**

```python
class InboxHandler(FileSystemEventHandler):
    """处理文件系统事件"""
    def on_created(self, event):
        # 新文件 → 放入队列
    def on_moved(self, event):
        # 移动到 inbox → 放入队列

def wait_for_file_stability(file_path, wait_time=3):
    """
    防抖机制：
    - 连续 3 次检查文件大小不变
    - 确保文件传输完成
    - 超时保护（10 次检查）
    """

def worker_thread(queue, workflow):
    """
    Worker 线程：
    - 从队列取文件
    - 调用 workflow.process_file()
    - 异常隔离（单个文件失败不影响全局）
    """
```

**工作流程：**
```
1. Observer 监听 inbox 目录
2. 检测到新文件 → 放入 Queue
3. Worker 从 Queue 取文件
4. 等待文件稳定（防抖）
5. 调用 JanitorWorkflow.process_file()
6. 记录日志
7. 继续处理下一个文件
```

---

### 8. Web UI（app.py）

**核心功能：**

```python
def load_pending_files() -> List[Dict]:
    """扫描 pending/ 目录，加载所有待审批文件"""

def approve_file(pending_item, archive_root) -> tuple[bool, str]:
    """
    批准流程：
    1. 读取 pending JSON
    2. 调用 safe_move_file()
    3. 删除 pending JSON
    4. 记录日志
    """

def reject_file(pending_item, move_to_quarantine) -> tuple[bool, str]:
    """
    拒绝流程：
    1. 删除或移到隔离区
    2. 记录日志
    """
```

**Streamlit 界面：**
- **侧边栏：** 统计、配置、快捷操作
- **主界面：** 待审批列表、文件详情、操作按钮
- **实时刷新：** `st.rerun()` 更新界面
- **异常处理：** 所有操作都有 try-except

---

## 关键机制

### 1. 非阻塞审批（pending 机制）

**传统 HITL（阻塞式）：**
```python
# 处理流程被阻塞
plan = generate_plan()
approved = input("批准吗？(y/n)")  # 阻塞在这里
if approved == 'y':
    execute(plan)
```

**非阻塞 HITL（pending 机制）：**
```python
# 工作流生成 pending JSON，立即结束
plan = generate_plan()
save_to_pending(plan)  # 保存到 pending/
return  # 工作流结束，不阻塞

# 用户稍后在 UI 中审批
# UI 读取 pending/，提供批准/拒绝按钮
```

**优势：**
- 支持批量处理（一次生成多个 pending）
- 支持监听器（不阻塞主线程）
- 支持多种 UI（Web、CLI、移动端）
- 用户可以随时审批

---

### 2. 防抖机制（File Stability Check）

**问题：** 文件复制到 inbox 时，监听器立即检测到，但文件可能还在传输中。

**解决：**
```python
def wait_for_file_stability(file_path, wait_time=3):
    last_size = -1
    stable_count = 0
    
    for _ in range(10):  # 最多检查 10 次
        current_size = file_path.stat().st_size
        
        if current_size == last_size:
            stable_count += 1
            if stable_count >= 3:  # 连续 3 次大小不变
                return True
        else:
            stable_count = 0
        
        last_size = current_size
        time.sleep(wait_time)
    
    return False  # 超时
```

---

### 3. 冲突处理（Auto Rename）

**策略：**
```python
# 原文件：contract.docx
# 目标目录已存在 contract.docx

# 自动重命名：
contract.docx → contract_1.docx → contract_2.docx → ...

# 最多尝试 100 次，防止无限循环
```

**实现：**
```python
def resolve_collision(destination: Path) -> Path:
    if not destination.exists():
        return destination
    
    stem = destination.stem
    ext = destination.suffix
    parent = destination.parent
    
    for i in range(1, 100):
        new_name = f"{stem}_{i}{ext}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
    
    raise RuntimeError("无法解决冲突：尝试次数过多")
```

---

## 技术栈

### 核心框架

| 技术 | 版本 | 用途 |
|------|------|------|
| **LangGraph** | ≥0.2.0 | 状态图工作流编排 |
| **LangChain** | ≥0.3.0 | LLM 集成和工具链 |
| **OpenAI** | ≥1.0.0 | GPT 模型调用 |
| **Pydantic** | ≥2.0 | 数据验证和结构化输出 |
| **Streamlit** | ≥1.28.0 | Web UI 框架 |
| **Watchdog** | ≥3.0.0 | 文件系统监听 |

### 文档处理

| 库 | 用途 |
|------|------|
| **pypdf** | PDF 文本提取 |
| **python-docx** | Word 文档处理 |
| **python-pptx** | PowerPoint 处理 |

### 工具库

| 库 | 用途 |
|------|------|
| **python-dotenv** | 环境变量管理 |
| **PyYAML** | 配置文件解析 |
| **pathlib** | 路径操作 |

---

## 数据流

### 1. 文件处理流程

```
inbox/file.pdf
    ↓ (1) 检测文件
JanitorWorkflow.process_file()
    ↓ (2) 提取预览
extract_text_preview() → preview text
    ↓ (3) LLM 分析
llm_processor.analyze_file() → FileAnalysis
    ↓ (4) 构建计划
build_plan() → RenamePlan
    ↓ (5) 校验
validator.validate_plan() → is_valid
    ↓ (6) 决策
    ├─ invalid → 跳过
    ├─ pending → 保存到 pending/
    └─ approved → safe_move_file()
                      ↓
        archive/类别/年份/新文件名.pdf
                      ↓
        logs/graph_plan_*.jsonl (记录)
```

### 2. pending → 审批流程

```
pending/plan_xxx.json
    ↓ (1) UI 加载
load_pending_files() → List[Dict]
    ↓ (2) 展示在 Web UI
Streamlit 渲染文件卡片
    ↓ (3) 用户操作
[批准] or [拒绝] or [隔离]
    ↓ (4) 执行操作
approve_file() → safe_move_file()
    ↓ (5) 清理和记录
删除 pending JSON + 写入 ui_events.jsonl
    ↓
archive/类别/年份/文件.ext
```

---

## 配置系统

### 配置优先级

```
命令行参数 > 环境变量 > config.yaml > 默认值
```

### 配置加载

```python
def load_config(config_path: Path) -> dict:
    """加载 YAML 配置文件"""

def load_env():
    """加载 .env 环境变量"""

# 配置合并
cfg = {
    **load_config("config.yaml"),
    **os.environ,  # 环境变量覆盖
}
```

---

## 日志系统

### 日志级别

```python
# Python logging 标准级别
DEBUG    # 调试信息
INFO     # 一般信息
WARNING  # 警告
ERROR    # 错误
```

### 日志格式

**JSONL 格式（结构化）：**
```json
{
  "timestamp": "2024-12-14T16:30:45.123456",
  "level": "INFO",
  "event": "file_processed",
  "file_path": "inbox/contract.docx",
  "result": "success"
}
```

**优势：**
- 易于解析
- 支持日志分析工具
- 一行一条记录

---

## 性能优化

### 当前性能

- **LLM 调用：** 2-3 秒/文件
- **文件移动：** < 100ms
- **UI 加载：** < 1 秒（100 个 pending）
- **监听器延迟：** 3-5 秒（含防抖）

### 优化方向

1. **LLM 缓存**
   - 相似文件名缓存结果
   - 使用 LangChain Cache

2. **并发处理**
   - 多 Worker 线程
   - asyncio 异步 LLM 调用

3. **索引优化**
   - SQLite 替代 JSON
   - 建立文件索引

---

## 扩展性

### 添加新文件类型

1. 修改 `config.yaml`（配置）
2. 修改 `core/schemas.py`（数据结构）
3. 修改 `core/llm_processor.py`（分类规则）
4. 修改 `utils/file_ops.py`（文本提取）

### 添加新功能节点

```python
def node_custom_processing(state: JanitorState) -> JanitorState:
    """自定义处理节点"""
    # 处理逻辑
    state["custom_field"] = result
    return state

# 在 build_graph() 中添加节点
graph.add_node("custom_processing", node_custom_processing)
graph.add_edge("analyze", "custom_processing")
```

---

## 安全考虑

### 1. 路径安全

```python
# 禁止路径遍历
if ".." in path or path.startswith("/"):
    raise SecurityError("不安全的路径")

# 强制在工作目录内
archive_root.resolve() in dst.resolve().parents
```

### 2. 文件名安全

```python
# 禁止特殊字符
illegal_chars = '<>:"|?*'
for char in illegal_chars:
    if char in filename:
        raise ValueError("文件名包含非法字符")
```

### 3. 操作审计

```python
# 所有操作记录到日志
log_entry = {
    "timestamp": datetime.now(),
    "action": "approve",
    "user": "admin",  # 可扩展用户系统
    "file": "xxx.pdf",
    "result": "success"
}
```

---

## 测试

### 单元测试

- `core/test_validator.py` - 校验器测试
- `core/test_llm.py` - LLM 集成测试

### 集成测试

- `examples/test_ppt_support.py` - PPT 支持测试
- `examples/test_pending_mechanism.py` - pending 机制测试
- `examples/test_watcher.py` - 监听器测试

---

## 部署建议

### 本地开发

```bash
conda activate janitor
python watch_inbox.py &
streamlit run app.py
```

### 生产环境

**使用 Supervisor（Linux）：**
```ini
[program:janitor-watcher]
command=/path/to/python watch_inbox.py --auto-approve
directory=/path/to/digital-janitor
autostart=true
autorestart=true

[program:janitor-ui]
command=/path/to/streamlit run app.py --server.port=8501
directory=/path/to/digital-janitor
autostart=true
autorestart=true
```

**使用 Docker：**
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py"]
```

---

## 总结

Digital Janitor 是一个**工程化完整、架构清晰**的 AI Agent 系统：

- ✅ **模块化设计**：各模块职责明确，易于维护
- ✅ **可扩展**：易于添加新功能和文件类型
- ✅ **安全可靠**：多层防护，完整日志
- ✅ **用户友好**：多种使用方式，Web UI 直观
- ✅ **生产就绪**：异常处理、日志、配置完善

适合作为 **LangGraph 应用开发**和**AI Agent 系统设计**的参考案例。

