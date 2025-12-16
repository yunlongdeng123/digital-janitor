# Memory System - 审批日志和偏好学习

## 功能概览

Digital Janitor 的 Memory 系统实现了两个核心功能：
1. **审批日志追溯** - 记录每次文件处理的完整决策链
2. **偏好自动学习** - 从历史记录中提取用户习惯，优化后续建议

---

## 系统架构

```
Memory System
├── Approval Log (事实记录)
│   └── 每次操作的完整快照
└── Learned Preferences (提取的规律)
    ├── Vendor → Folder 映射
    ├── DocType → Date Partition 规则 (TODO)
    └── Naming Template 偏好 (TODO)
```

### 技术栈

- **数据库**: SQLite（支持 ACID、易于查询、无需额外服务）
- **ORM**: SQLAlchemy（类型安全、易迁移）
- **位置**: `~/.digital_janitor/memory.db`

---

## 数据模型

### 1. ApprovalLog (审批日志)

记录每次文件处理的完整信息：

**核心字段：**
- 文件标识：`file_hash`, `original_filename`, `file_size`
- AI 分析：`doc_type`, `vendor`, `confidence_score`
- 建议 vs 实际：`suggested_filename`, `final_filename`
- 决策追踪：`action`, `user_modified_filename`, `user_modified_folder`

### 2. LearnedPreference (学习到的偏好)

从审批记录中自动提取的用户偏好：

**核心字段：**
- 偏好类型：`preference_type` (vendor_folder/doctype_partition/naming_template)
- 触发条件：`trigger_vendor`, `trigger_doc_type`
- 偏好值：`preference_value` (目标文件夹路径)
- 置信度：`confidence`, `sample_count`

### 3. PreferenceAuditLog (偏好变更审计)

记录偏好的变更历史，用于调试和追溯。

---

## 使用方法

### 1. 自动记录审批

系统会自动记录所有审批操作：

```python
from run_graph_once import JanitorWorkflow

workflow = JanitorWorkflow()

# 处理文件时自动记录
result = workflow.process_file(
    Path("inbox/invoice.pdf"),
    dry_run=False,
    auto_approve=False
)

# 审批日志已自动保存到 memory.db
```

### 2. 查看审批历史

在 Web UI 中：
1. 启动 Web UI：`streamlit run app.py`
2. 在侧边栏选择 "📜 审批历史"
3. 可按文档类型、供应商、日期筛选
4. 可导出为 CSV

### 3. 查看学习到的偏好

在 Web UI 中：
1. 侧边栏选择 "🧠 学习到的偏好"
2. 查看系统学习到的 Vendor → Folder 映射
3. 可删除不需要的偏好

### 4. 程序化访问

```python
from core.memory import MemoryDatabase, ApprovalRepository, PreferenceRepository

# 使用 with 语句自动管理连接
with MemoryDatabase() as db:
    repo = ApprovalRepository(db)
    
    # 获取最近的审批记录
    recent = repo.get_recent_approvals(
        limit=50,
        doc_type='invoice',
        vendor='ABC Corp'
    )
    
    # 获取统计信息
    stats = repo.get_statistics(days=30)
    print(f"总处理数: {stats['total_approvals']}")
```

---

## 偏好学习机制

### 学习规则

**规则 1: Vendor → Folder 映射**

当用户多次将同一供应商的文件移动到特定文件夹时，系统会学习这个偏好。

**触发条件：**
- 用户修改了 AI 建议的文件夹（`user_modified_folder = True`）
- 文件有明确的供应商信息（`vendor` 不为空）

**学习算法：**
```python
if 新样本与现有偏好一致:
    confidence += 0.1  # 最高 1.0
    
if 新样本与现有偏好冲突:
    confidence -= 0.15  # 最低 0.1
    if sample_count >= 3:
        更新为新值  # 新模式稳定后替换
```

**应用时机：**
- 在构建重命名计划时（`node_build_plan`）
- 优先使用学习到的文件夹（confidence >= 0.7）
- 如果没有学习到的偏好，使用默认规则

### 示例场景

**场景 1：学习供应商文件夹**

```
第 1 次：
  AI 建议: 财务/2024/12/invoice_ABC_Corp.pdf
  用户改为: 财务/ABC_Corp/2024/invoice_ABC_Corp.pdf
  → 系统学习: ABC Corp + invoice → 财务/ABC_Corp/2024 (confidence=0.6)

第 2 次：
  AI 建议: 财务/2024/12/invoice_ABC_Corp_02.pdf
  用户又改为: 财务/ABC_Corp/2024/invoice_ABC_Corp_02.pdf
  → 系统强化: ABC Corp + invoice → 财务/ABC_Corp/2024 (confidence=0.7)

第 3 次：
  系统自动应用学习到的偏好
  AI 直接建议: 财务/ABC_Corp/2024/invoice_ABC_Corp_03.pdf ✅
```

**场景 2：冲突处理**

```
第 1-2 次：用户一直把 ABC Corp 放在 财务/ABC_Corp/2024
→ confidence=0.7

第 3 次：用户突然改成 财务/供应商/ABC_Corp
→ confidence 降低到 0.55（低于 0.7 阈值，不再自动应用）

第 4-5 次：用户持续使用新路径
→ 更新为新偏好: 财务/供应商/ABC_Corp (confidence=0.7)
```

---

## Web UI 功能

### 审批历史页面

**功能：**
- 📊 统计卡片（总处理数、最近30天、通过/拒绝数）
- 🔍 筛选条件（文档类型、供应商、数量限制）
- 📋 表格展示（时间、文件名、类型、供应商、操作、置信度）
- 📥 导出 CSV

**使用场景：**
- 追溯某个文件的处理历史
- 统计某个供应商的文件数量
- 审计所有拒绝的文件
- 导出数据进行分析

### 学习到的偏好页面

**功能：**
- 📁 供应商文件夹映射列表
- 📊 每个偏好的置信度和样本数
- 🗑️ 删除不需要的偏好

**使用场景：**
- 查看系统学习到了哪些规则
- 删除错误的学习结果
- 了解哪些供应商已有固定路径

---

## API 参考

### ApprovalRepository

```python
# 保存审批记录
repo.save_approval(log_data: dict) -> int

# 获取最近的审批记录
repo.get_recent_approvals(
    limit: int = 50,
    doc_type: Optional[str] = None,
    vendor: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    action: Optional[str] = None
) -> List[Dict]

# 获取统计信息
repo.get_statistics(days: int = 30) -> Dict[str, Any]
```

### PreferenceRepository

```python
# 更新或创建偏好
repo.update_preference(
    preference_type: str,
    trigger_conditions: dict,
    preference_value: str,
    triggered_by_log_id: Optional[int] = None
)

# 获取匹配的偏好
repo.get_preference(
    preference_type: str,
    context: dict,
    min_confidence: float = 0.7
) -> Optional[str]

# 列出所有偏好
repo.list_all_preferences(
    preference_type: Optional[str] = None,
    enabled_only: bool = True
) -> List[Dict]

# 禁用偏好
repo.disable_preference(preference_id: int)
```

---

## 数据库管理

### 数据库位置

```
Windows: C:\Users\<用户名>\.digital_janitor\memory.db
macOS:   /Users/<用户名>/.digital_janitor/memory.db
Linux:   /home/<用户名>/.digital_janitor/memory.db
```

### 备份数据库

```bash
# 复制数据库文件即可
cp ~/.digital_janitor/memory.db memory_backup_20241215.db
```

### 清空数据

```bash
# 删除数据库文件（系统会自动重建）
rm ~/.digital_janitor/memory.db
```

### 查看数据库内容（使用 SQLite 工具）

```bash
# 安装 SQLite 命令行工具
# macOS: brew install sqlite
# Ubuntu: apt-get install sqlite3

# 打开数据库
sqlite3 ~/.digital_janitor/memory.db

# 查看表
.tables

# 查看审批日志
SELECT * FROM approval_logs ORDER BY created_at DESC LIMIT 10;

# 查看偏好
SELECT * FROM learned_preferences WHERE enabled = 1;

# 退出
.quit
```

---

## 性能考虑

### 数据库大小

- 每条审批记录约 1-2 KB
- 10,000 条记录约 10-20 MB
- SQLite 支持 TB 级数据，性能不是瓶颈

### 查询性能

- 已建立索引：`file_hash`, `doc_type`, `vendor`, `created_at`, `session_id`
- 查询 10万条记录：< 100ms

### 并发处理

- SQLite 支持多读单写
- 本项目场景（单用户）无并发问题
- 如需多用户，建议迁移到 PostgreSQL

---

## 隐私和安全

### 数据内容

- ✅ 存储：文件名、大小、类型、供应商
- ✅ 存储：AI 分析结果、用户决策
- ❌ 不存储：文件内容本身

### 数据位置

- 数据库在用户本地：`~/.digital_janitor/memory.db`
- 不会上传到云端
- 完全受用户控制

### 删除数据

```bash
# 删除所有数据
rm ~/.digital_janitor/memory.db

# 或在 Python 中
from pathlib import Path
db_path = Path.home() / '.digital_janitor' / 'memory.db'
db_path.unlink()
```

---

## 未来增强（TODO）

### 已计划功能

1. **命名模板学习**
   - 识别用户的命名偏好
   - 例如："Invoice" → "发票"

2. **日期分区规则**
   - 学习用户喜欢的日期分区方式
   - 按月、按季度、按年

3. **批量操作**
   - 批量删除某个供应商的所有记录
   - 批量导出某个时间段的数据

4. **统计图表**
   - 文件处理趋势图
   - 供应商分布饼图
   - 置信度分布柱状图

### 欢迎贡献

如有功能建议或 Bug 报告，请提交 Issue。

---

## 常见问题

### Q1: 为什么我的偏好没有被应用？

**可能原因：**
1. 置信度不够（< 0.7）
2. 样本数太少（< 2 次）
3. 供应商或文档类型不匹配

**解决方案：**
- 在 Web UI 查看学习到的偏好
- 检查置信度和样本数
- 重复相同的操作以提高置信度

### Q2: 如何删除错误的学习结果？

在 Web UI 中：
1. 进入 "🧠 学习到的偏好" 页面
2. 找到要删除的偏好
3. 点击 "🗑️ 删除" 按钮

### Q3: 数据库会无限增长吗？

不会。可以定期清理旧数据：
```python
from core.memory import MemoryDatabase
from datetime import datetime, timedelta

with MemoryDatabase() as db:
    # 删除 90 天前的记录
    cutoff = datetime.utcnow() - timedelta(days=90)
    db.session.query(ApprovalLog).filter(
        ApprovalLog.created_at < cutoff
    ).delete()
    db.session.commit()
```

### Q4: 如何导出所有数据？

在 Web UI 的 "📜 审批历史" 页面点击 "📥 导出为 CSV"。

或使用 SQLite 工具：
```bash
sqlite3 ~/.digital_janitor/memory.db
.headers on
.mode csv
.output approval_logs.csv
SELECT * FROM approval_logs;
.quit
```

---

## 技术细节

### 文件 Hash 算法

使用快速 Hash 算法（文件大小 + 头部 8KB）：
- 速度快（< 10ms）
- 足够识别文件
- 不需要读取整个文件

### 置信度更新算法

```python
初始置信度: 0.6

每次一致: confidence = min(1.0, confidence + 0.1)
每次冲突: confidence = max(0.1, confidence - 0.15)

应用阈值: 0.7
```

### 数据库Schema

完整的 Schema 定义见：`core/memory/database.py`

---

**有问题？** 查看 [主文档](./GUIDE.md) 或提交 Issue。

