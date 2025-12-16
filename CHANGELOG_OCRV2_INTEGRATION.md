# Changelog - OCR V2 集成到 run_graph_once.py

## [2024-12-16] - OCR V2 Integration

### 🎯 目标

将 OCR V2 的新功能（缓存、图片支持、质量评分）集成到主工作流 `run_graph_once.py`。

---

### 📝 改动详情

#### 1. 修改导入语句 ✅

**位置**: 第 54 行

**改动**:
```python
# Before
from utils.file_ops import discover_files, extract_text_preview, get_file_size_mb, safe_move_file

# After
from utils.file_ops import discover_files, extract_text_preview_enhanced, get_file_size_mb, safe_move_file
```

---

#### 2. 更新 `JanitorState` 定义 ✅

**位置**: 第 92-121 行

**新增字段**:
```python
extraction_metadata: Dict[str, Any]  # 🆕 OCR V2: 文本提取元数据
```

**包含内容**:
- `method`: 提取方法 (direct/rapidocr/vision_llm/cached)
- `confidence`: OCR 置信度
- `quality_score`: 质量评分 (0-100)
- `needs_review`: 是否需要人工审查
- `processing_time_ms`: 处理耗时
- `page_count`: 页数
- `char_count`: 字符数
- `error`: 错误信息

---

#### 3. 改造 `node_extract_preview` ✅

**位置**: 第 125-155 行

**改动内容**:
1. 调用 `extract_text_preview_enhanced` 替代 `extract_text_preview`
2. 处理字典返回值（OCR V2 返回字典而非字符串）
3. 保存 `state["preview"]` = result["text"]
4. 保存 `state["extraction_metadata"]` = 除 text 外的其他字段
5. 打印简短日志：显示提取方法、耗时、质量分

**新增日志示例**:
```
📄 文本提取: rapidocr | 质量=85 | 耗时=1200ms
📄 文本提取: rapidocr_cached | 质量=85 | 耗时=0ms 💾
⚠️  OCR 质量较低 (45分)，可能需要人工审查
```

---

#### 4. 改造 `node_human_review`（质量熔断）✅

**位置**: 第 257-330 行

**核心逻辑**:
```python
# 🆕 OCR V2: 检查 OCR 质量熔断
extraction_metadata = state.get("extraction_metadata", {})
ocr_needs_review = extraction_metadata.get("needs_review", False)
ocr_quality_score = extraction_metadata.get("quality_score", 100)

# 🆕 OCR V2 质量熔断：如果 OCR 质量低，强制转为人工审批
if ocr_needs_review:
    print(f"   ⚠️  OCR 质量低 ({ocr_quality_score}分)，强制转为人工审批")
    auto_approve = False  # 强制关闭自动批准
```

**熔断效果**:
- 即使用户设置了 `--auto-approve`，质量低的文件也会强制进入人工审批队列
- 在 pending JSON 中额外记录：
  - `ocr_quality_issue: True`
  - `ocr_quality_score: <分数>`
  - `extraction_method: <方法>`

**新增日志示例**:
```
⚠️  OCR 质量低 (45分)，强制转为人工审批
⏳ 计划已生成，等待 UI 审批
   文件：plan_20241216_123456_document.json
   ⚠️  原因：OCR 质量低 (45分)
```

---

#### 5. 更新 `node_apply` 日志记录 ✅

**位置**: 第 373-391 行

**新增字段**:
```python
state["record"] = {
    # ... 原有字段 ...
    # 🆕 OCR V2: 记录文本提取元数据
    "extraction_metadata": extraction_metadata,
}
```

---

#### 6. 更新 `node_skip` 日志记录 ✅

**位置**: 第 394-432 行

**改动内容**:
1. 获取 `extraction_metadata`
2. 如果因 OCR 质量问题导致的 pending，在原因中注明
3. 在日志记录中包含 `extraction_metadata`

**新增日志示例**:
```
⏳ 等待审批 (OCR质量低: 45分)：document.pdf
```

---

### 📊 改动统计

| 指标 | 数量 |
|------|------|
| 修改的函数 | 4 个 |
| 新增代码行 | ~50 行 |
| 修改代码行 | ~30 行 |

---

### 🧪 测试验证

#### 测试命令

```bash
# 基本测试（Dry-run 模式）
python run_graph_once.py --limit 3

# 自动批准模式（验证质量熔断）
python run_graph_once.py --limit 3 --auto-approve

# 真实执行模式
python run_graph_once.py --limit 1 --execute
```

#### 预期输出（正常质量文件）

```
[1/3] 🔍 Processing: document.pdf
--------------------------------------------------------------------------------
   📄 文本提取: rapidocr | 质量=85 | 耗时=1500ms

🧑‍⚖️  需要确认：document.pdf
   → 新名字：invoice_2024-12_ABC公司.pdf
   → 目标目录：财务/2024/12
   → 类别/置信度：invoice / 0.95
   🤖 自动批准模式：已批准
   🧪 Dry-run 批准：将把 document.pdf → invoice_2024-12_ABC公司.pdf
      移动到 财务/2024/12
```

#### 预期输出（低质量 OCR 文件）

```
[2/3] 🔍 Processing: scanned_photo.jpg
--------------------------------------------------------------------------------
   📄 文本提取: rapidocr | 质量=35 | 耗时=2000ms
   ⚠️  OCR 质量较低 (35分)，可能需要人工审查

🧑‍⚖️  需要确认：scanned_photo.jpg
   → 新名字：unknown_2024-12.jpg
   → 目标目录：其他/2024
   → 类别/置信度：default / 0.60
   ⚠️  OCR 质量低 (35分)，强制转为人工审批
   ⏳ 计划已生成，等待 UI 审批
      文件：plan_20241216_123456_scanned_photo.json
      ⚠️  原因：OCR 质量低 (35分)
   ⏳ 等待审批 (OCR质量低: 35分)：scanned_photo.jpg
```

#### 预期输出（缓存命中）

```
[3/3] 🔍 Processing: document.pdf
--------------------------------------------------------------------------------
   📄 文本提取: rapidocr_cached | 质量=85 | 耗时=0ms 💾

🧑‍⚖️  需要确认：document.pdf
   ...
```

---

### 📋 Pending JSON 新增字段

**位置**: `pending/plan_*.json`

**新增字段**:
```json
{
    // ... 原有字段 ...
    "ocr_quality_issue": true,
    "ocr_quality_score": 35,
    "extraction_method": "rapidocr"
}
```

**字段说明**:
- `ocr_quality_issue`: 是否存在 OCR 质量问题（导致强制人工审批）
- `ocr_quality_score`: OCR 质量评分 (0-100)
- `extraction_method`: 文本提取方法

---

### 📋 日志文件新增字段

**位置**: `logs/graph_plan_*.jsonl`

**新增字段**:
```json
{
    // ... 原有字段 ...
    "extraction_metadata": {
        "method": "rapidocr",
        "confidence": 0.85,
        "quality_score": 75,
        "needs_review": false,
        "processing_time_ms": 1500,
        "page_count": 3,
        "char_count": 2500,
        "error": null
    }
}
```

---

### 🔄 兼容性

- ✅ **向后兼容**: `extraction_metadata` 为可选字段，旧代码正常工作
- ✅ **Pending JSON 兼容**: 新增字段不影响 UI 读取
- ✅ **日志兼容**: 新增字段仅用于分析，不影响现有流程

---

### 🚀 使用建议

#### 1. 正常使用

```bash
# 处理文件（会自动使用 OCR V2 功能）
python run_graph_once.py --limit 10
```

#### 2. 测试质量熔断

```bash
# 使用 --auto-approve，但低质量文件仍会被拦截
python run_graph_once.py --limit 10 --auto-approve
```

#### 3. 查看日志中的 OCR 元数据

```python
import json

with open("logs/graph_plan_dryrun_20241216_123456.jsonl") as f:
    for line in f:
        record = json.loads(line)
        metadata = record.get("extraction_metadata", {})
        print(f"{record['original_file']}: {metadata.get('method')} | 质量={metadata.get('quality_score')}")
```

---

### 📚 相关文档

- [OCR_V2_GUIDE.md](OCR_V2_GUIDE.md) - OCR V2 功能详细指南
- [OCR_V2_COMPLETED.md](OCR_V2_COMPLETED.md) - OCR V2 实施完成报告
- [CHANGELOG_OCR_V2.md](CHANGELOG_OCR_V2.md) - OCR V2 更新日志

---

**版本**: OCR V2 Integration  
**分支**: feat/ocr-v2-cache-image  
**日期**: 2024-12-16  
**状态**: ✅ 完成

