# 📝 可编辑审批功能 - 使用指南

## 🚀 快速开始

### 1. 生成待审批文件

```bash
python run_graph_once.py --limit 1
```

这会在 `pending/` 目录下生成一个待审批的 JSON 文件。

### 2. 启动 Web UI

```bash
streamlit run app.py
```

或者使用快捷脚本（Windows）：

```bash
start_ui.bat
```

### 3. 在 UI 中审批文件

1. 打开浏览器访问 `http://localhost:8501`
2. 在 "📋 待审批队列" 页面，你会看到待审批文件
3. 展开文件卡片，向下滚动到 "✏️ 编辑审批信息" 部分
4. 修改字段（可选）：
   - **目标文件夹**：例如从 `发票/2024` 改为 `财务/2024/发票`
   - **新文件名**：例如从 `invoice_2024-12` 改为 `ABC公司_发票_2024-12`（扩展名会自动补全）
   - **供应商**：例如填写 `ABC公司`
   - **文档类型**：从下拉菜单选择
5. 点击 "✅ 批准" 按钮

---

## ✨ 功能特性

### 1. 自动扩展名补全

**问题：** 用户可能忘记输入文件扩展名

**解决：** 系统自动检测并补全

```
用户输入：invoice_2024-12_ABC
原始文件：invoice.pdf
系统补全：invoice_2024-12_ABC.pdf ✅
```

### 2. 智能学习用户偏好

**场景：** 你总是把 "ABC公司" 的发票放到 `财务/2024/ABC公司/发票` 文件夹

**系统行为：**
- 第 1 次：你手动修改文件夹 → 系统记录 `user_modified_folder=True`
- 第 2 次：系统自动学习 `ABC公司 + invoice → 财务/2024/ABC公司/发票`
- 第 3 次：系统自动推荐该文件夹（置信度提升）
- 第 4 次起：AI 直接使用学习到的文件夹

**查看学习结果：**
- 在 UI 侧边栏选择 "🧠 学习到的偏好" 页面
- 或运行测试脚本：`python test_editable_approval.py`

### 3. 修改追踪

系统会记录你是否修改了 AI 的建议：

| 操作 | Memory 中的 action 字段 |
|------|------------------------|
| 未修改任何字段，直接批准 | `approved` |
| 修改了任意字段后批准 | `modified` |
| 拒绝文件 | `rejected` |

---

## 🧪 验证功能

### 方法 1：使用测试脚本（推荐）

```bash
python test_editable_approval.py
```

这会输出：
- ✅ Memory 中的审批记录
- ✅ 学习到的偏好规则
- ✅ 统计信息

### 方法 2：在 UI 中查看

1. 侧边栏选择 "📜 审批历史"
   - 查看 `action` 列（`approved` 或 `modified`）
   - 查看 `final_filename` 和 `final_folder`（最终值）

2. 侧边栏选择 "🧠 学习到的偏好"
   - 查看供应商 → 文件夹的映射
   - 查看置信度和样本数

### 方法 3：直接查询数据库

```python
from core.memory import MemoryDatabase, ApprovalRepository

with MemoryDatabase() as db:
    repo = ApprovalRepository(db)
    logs = repo.get_recent_approvals(limit=1)
    
    log = logs[0]
    print(f"操作: {log['action']}")
    print(f"建议文件夹: {log['suggested_folder']}")
    print(f"最终文件夹: {log['final_folder']}")
    print(f"用户修改了: {log['user_modified_folder']}")
```

---

## 📊 完整工作流示例

### 场景：处理一张 ABC 公司的发票

#### 第 1 次处理

```
1. AI 分析:
   - 供应商: ABC Corp
   - 文档类型: invoice
   - 建议文件夹: 发票/2024/12
   - 建议文件名: invoice_2024-12-15_ABC_Corp.pdf

2. 你的操作（在 UI 中）:
   - 修改文件夹: 财务/2024/ABC公司/发票
   - 修改供应商: ABC公司（统一中文名称）
   - 点击 ✅ 批准

3. 系统行为:
   - 文件移动到: archive/财务/2024/ABC公司/发票/invoice_2024-12-15_ABC_Corp.pdf
   - Memory 记录: action="modified", user_modified_folder=True
   - 偏好学习: ABC公司 + invoice → 财务/2024/ABC公司/发票 (置信度 0.6)
```

#### 第 2 次处理（相同供应商）

```
1. AI 分析:
   - 供应商: ABC Corp
   - 文档类型: invoice
   - 建议文件夹: 发票/2024/12 (AI 默认规则)

2. 系统内部逻辑:
   - 查询学习偏好: 找到 ABC公司 + invoice → 财务/2024/ABC公司/发票
   - 置信度 0.6 < 0.7 (最低阈值) → 暂不应用

3. 你的操作:
   - 再次修改到: 财务/2024/ABC公司/发票
   - 点击 ✅ 批准

4. 系统行为:
   - 偏好强化: 置信度 0.6 → 0.7 ✅ 达到阈值
```

#### 第 3 次处理（自动应用偏好）

```
1. AI 分析:
   - 供应商: ABC Corp
   - 文档类型: invoice

2. 系统内部逻辑:
   - 查询学习偏好: 找到 ABC公司 + invoice → 财务/2024/ABC公司/发票
   - 置信度 0.7 ≥ 0.7 → 自动应用 🎉

3. 你的操作:
   - 不需要修改，直接点击 ✅ 批准

4. 系统行为:
   - action="approved" (没有修改)
   - 偏好强化: 置信度 0.7 → 0.8
```

---

## 🎯 最佳实践

### 1. 统一命名规范

建议在团队内统一：
- 供应商名称格式（中文 vs 英文）
- 文档类型选择（发票 vs invoice）
- 文件夹结构（按年份 vs 按供应商）

这样系统学习效果更好。

### 2. 渐进式训练

前期多修正几次，后期系统会越来越准确：

| 阶段 | 样本数 | 置信度 | 建议 |
|------|--------|--------|------|
| 初期 | 1-2 次 | 0.6-0.7 | 每次都检查并修正 |
| 成长期 | 3-5 次 | 0.7-0.9 | 偶尔抽查 |
| 成熟期 | 6+ 次 | 0.9-1.0 | 直接批准 |

### 3. 定期清理偏好

在 "🧠 学习到的偏好" 页面：
- 删除错误的学习规则
- 调整过时的文件夹映射

---

## ❓ 常见问题

### Q1: 我修改了文件名，但系统没有学习？

**A:** 文件名学习功能尚未实现（需要模式识别算法）。目前系统只学习：
- ✅ 供应商 + 文档类型 → 文件夹
- ❌ 命名模板（规划中）

### Q2: 置信度阈值 0.7 可以调整吗？

**A:** 可以！在 `run_graph_once.py` 的 `node_build_plan` 函数中修改：

```python
learned_folder = state["preference_repo"].get_preference(
    'vendor_folder',
    context,
    min_confidence=0.5  # 改为 0.5 (更激进) 或 0.8 (更保守)
)
```

### Q3: 如何批量处理相同规则的文件？

**A:** 目前每个文件需要单独审批。批量编辑功能规划在 PR#2。

临时方案：使用 `--auto-approve` 模式（适合信任度高的场景）：

```bash
python run_graph_once.py --limit 10 --auto-approve --execute
```

### Q4: 扩展名补全有时不工作？

**A:** 检查原始文件是否有扩展名。如果原始文件名是 `document`（无扩展名），系统无法补全。

### Q5: Memory 数据库在哪里？

**A:** `memory.db` 文件在项目根目录。

- 备份：复制 `memory.db`
- 重置：删除 `memory.db`（下次运行自动重建）
- 导出：在 UI 的 "📜 审批历史" 页面点击 "📥 导出为 CSV"

---

## 🔧 故障排查

### UI 报错：`DuplicateWidgetID`

**原因：** Streamlit 组件的 `key` 冲突

**解决：**
1. 刷新页面
2. 清空浏览器缓存
3. 重启 Streamlit

### 文件移动失败

**可能原因：**
1. 目标文件夹路径包含非法字符
2. 文件被其他程序占用
3. 磁盘空间不足

**解决：**
- 检查日志：`logs/ui_events.jsonl`
- 查看错误消息（UI 会显示）

### 偏好没有被应用

**检查清单：**
- [ ] 置信度是否 ≥ 0.7？
- [ ] 供应商名称是否完全匹配？（大小写敏感）
- [ ] 文档类型是否一致？
- [ ] 偏好是否被禁用？（在 UI 中查看）

---

## 📚 相关文档

- [PR1_EDITABLE_HITL_SUMMARY.md](PR1_EDITABLE_HITL_SUMMARY.md) - 技术实施总结
- [docs/MEMORY_SYSTEM.md](docs/MEMORY_SYSTEM.md) - Memory 系统设计
- [MEMORY_V1_COMPLETE.md](MEMORY_V1_COMPLETE.md) - Memory V1 完整文档

---

## 💬 反馈与支持

如遇到问题或有功能建议，请：
1. 查看本文档的常见问题部分
2. 运行 `python test_editable_approval.py` 诊断
3. 提交 Issue（附带错误日志和复现步骤）

---

**祝使用愉快！🎉**

