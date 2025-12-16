# 📸 OCR V2 增强功能 - 使用指南

## 🎯 新增功能概览

### 1. 本地 OCR 缓存 (SQLite)
- **位置**: `~/.digital_janitor/ocr_cache.db`
- **机制**: 基于文件 hash 避免重复处理
- **效果**: 第二次处理相同文件时，速度提升 **10-100倍**

### 2. 图片文件支持
- **支持格式**: `.png`, `.jpg`, `.jpeg`, `.webp`
- **处理方式**: 直接使用 RapidOCR（跳过 pypdf）
- **应用场景**: 扫描件、截图、照片中的文字提取

### 3. 质量评分系统
- **评分范围**: 0-100
- **自动标记**: 分数 < 60 标记为"需要审查"
- **评分依据**: 文本长度、乱码率、OCR 置信度

---

## 🚀 快速开始

### 基本使用

```python
from pathlib import Path
from utils.file_ops import extract_text_preview_enhanced

# 处理 PDF 文件
result = extract_text_preview_enhanced(Path("document.pdf"))

# 处理图片文件
result = extract_text_preview_enhanced(Path("screenshot.png"))

# 查看结果
print(f"提取文本: {result['text'][:100]}...")
print(f"提取方法: {result['method']}")
print(f"质量评分: {result['quality_score']}")
print(f"需要审查: {result['needs_review']}")
print(f"处理时间: {result['processing_time_ms']}ms")
```

### 返回值字段

```python
{
    "text": str,                    # 提取的文本
    "method": str,                  # 提取方法 (见下方说明)
    "confidence": float,            # 置信度 (0-1)
    "quality_score": int,           # 🆕 质量评分 (0-100)
    "needs_review": bool,           # 🆕 是否需要人工审查
    "page_count": int,              # 页数（PDF）
    "char_count": int,              # 字符数
    "processing_time_ms": int,      # 处理时间（缓存命中时为 0）
    "error": str | None             # 错误信息
}
```

### 提取方法 (method) 说明

| 方法 | 说明 | 速度 | 成本 |
|------|------|------|------|
| `direct` | pypdf 标准提取 | ⚡⚡⚡ 极快 | 💰 免费 |
| `rapidocr` | RapidOCR 本地识别 | ⚡⚡ 较快 | 💰 免费 |
| `vision_llm` | Vision LLM（API） | ⚡ 较慢 | 💰💰 付费 |
| `direct_fallback` | pypdf 提取失败降级 | ⚡⚡⚡ 快 | 💰 免费 |
| `rapidocr_cached` | 🆕 RapidOCR 缓存命中 | ⚡⚡⚡ 极快 | 💰 免费 |
| `vision_llm_cached` | 🆕 Vision LLM 缓存命中 | ⚡⚡⚡ 极快 | 💰 免费 |

---

## 📊 质量评分详解

### 评分算法

```
初始分数: 100

扣分项：
1. 文本长度
   - 字符数 < 50   → 扣 30 分
   - 字符数 < 100  → 扣 15 分

2. 乱码率（非常见字符占比）
   - 乱码率 > 50%  → 扣 50 分
   - 乱码率 > 30%  → 扣 30 分
   - 乱码率 > 10%  → 扣 10 分

3. OCR 置信度
   - 置信度 < 0.5  → 扣 20 分
   - 置信度 < 0.7  → 扣 10 分

最终分数 = max(0, min(100, 初始分数 - 扣分))
需要审查 = (分数 < 60)
```

### 评分示例

| 文本样本 | 长度 | 乱码率 | 置信度 | 最终分数 | 需审查 |
|----------|------|--------|--------|----------|--------|
| 完整清晰的发票内容 | 500 | 5% | 0.95 | **100** | ❌ |
| 较短但清晰的合同 | 80 | 8% | 0.85 | **75** | ❌ |
| 模糊扫描件 | 120 | 15% | 0.55 | **60** | ❌ |
| 低质量照片 | 45 | 35% | 0.45 | **10** | ✅ |
| 完全识别失败 | 0 | - | 0.0 | **0** | ✅ |

---

## 💾 缓存管理

### 缓存机制

1. **文件识别**: 使用 SHA256(文件大小 + 头部 8KB)
2. **缓存条件**: 
   - 使用了 OCR（`rapidocr` 或 `vision_llm`）
   - 提取到文本（非空）
   - 质量评分 ≥ 30（质量太差不缓存）
3. **缓存位置**: `~/.digital_janitor/ocr_cache.db`

### 缓存查询

```python
from utils.file_ops import OCRCache, compute_file_hash
from pathlib import Path

# 初始化缓存
cache = OCRCache()

# 查询特定文件
file_path = Path("document.pdf")
file_hash = compute_file_hash(file_path)
cached = cache.get(file_hash)

if cached:
    print(f"缓存命中:")
    print(f"  文本: {cached['text'][:100]}...")
    print(f"  方法: {cached['method']}")
    print(f"  质量: {cached['quality_score']}")
else:
    print("缓存未命中")
```

### 清空缓存

```python
from utils.file_ops import OCRCache

cache = OCRCache()
cache.clear()
print("✅ 缓存已清空")
```

### 手动管理缓存

```python
from utils.file_ops import OCRCache

cache = OCRCache()

# 手动写入缓存
cache.set(
    file_hash="abc123...",
    text="这是文本内容",
    method="rapidocr",
    confidence=0.85,
    quality_score=75
)

# 查询缓存
cached = cache.get("abc123...")

# 更新缓存（使用相同 hash）
cache.set(
    file_hash="abc123...",
    text="更新后的文本",
    method="vision_llm",
    confidence=0.95,
    quality_score=90
)
```

---

## 🖼️ 图片 OCR 使用

### 支持的图片格式

- **PNG**: `.png`
- **JPEG**: `.jpg`, `.jpeg`
- **WebP**: `.webp`

### 使用示例

```python
from pathlib import Path
from utils.file_ops import extract_text_preview_enhanced

# 处理截图
screenshot = Path("inbox/invoice_screenshot.png")
result = extract_text_preview_enhanced(screenshot)

if result['needs_review']:
    print(f"⚠️  图片质量较差，评分: {result['quality_score']}")
    print(f"   建议: 重新扫描或使用更清晰的图片")
else:
    print(f"✅ 提取成功，评分: {result['quality_score']}")
    print(f"   文本: {result['text'][:200]}...")
```

### 图片 OCR 最佳实践

1. **图片分辨率**: 推荐 **200-300 DPI**
2. **图片大小**: < 10MB（过大会影响处理速度）
3. **图片质量**: 避免模糊、倾斜、强光照
4. **文字对比度**: 确保文字与背景有明显对比

### 常见问题

**Q: 为什么图片 OCR 提取不到文字？**

A: 可能原因：
1. 图片过于模糊
2. 文字太小（< 12pt）
3. 背景复杂、干扰严重
4. RapidOCR 未安装或配置错误

解决方案：
- 检查 `result['error']` 字段
- 查看 `quality_score`（< 30 说明质量极差）
- 尝试提高图片分辨率
- 使用图片编辑工具增强对比度

---

## 📈 性能优化

### 缓存效果测试

```python
import time
from pathlib import Path
from utils.file_ops import extract_text_preview_enhanced

file_path = Path("document.pdf")

# 第一次处理（未缓存）
start = time.time()
result1 = extract_text_preview_enhanced(file_path)
time1 = time.time() - start

# 第二次处理（缓存命中）
start = time.time()
result2 = extract_text_preview_enhanced(file_path)
time2 = time.time() - start

print(f"第 1 次: {time1*1000:.0f}ms ({result1['method']})")
print(f"第 2 次: {time2*1000:.0f}ms ({result2['method']})")
print(f"加速比: {time1/max(time2, 0.001):.1f}x")
```

**预期结果：**
- 未缓存: 1000-5000ms（取决于文件大小和 OCR 方法）
- 缓存命中: < 10ms（直接从数据库读取）

### 批量处理优化

```python
from pathlib import Path
from utils.file_ops import extract_text_preview_enhanced

files = list(Path("inbox").glob("*.pdf"))

for i, file_path in enumerate(files, 1):
    result = extract_text_preview_enhanced(file_path)
    
    # 缓存命中时处理速度极快
    cache_hit = "_cached" in result['method']
    status = "💾 缓存" if cache_hit else "🔄 处理"
    
    print(f"[{i}/{len(files)}] {status} {file_path.name} | "
          f"质量={result['quality_score']} | "
          f"耗时={result['processing_time_ms']}ms")
```

---

## 🧪 测试验证

### 运行测试脚本

```bash
# 完整测试
python test_ocr_v2.py

# 预期输出：
# ✅ 质量评分算法
# ✅ 缓存基本功能
# ✅ 文件 Hash 计算
# ✅ 图片 OCR
# ✅ 缓存命中率
```

### 手动测试步骤

1. **准备测试文件**
   ```bash
   # 放入 inbox/
   - document.pdf          # PDF 文件
   - screenshot.png        # 图片文件
   - invoice.jpg           # 扫描件
   ```

2. **测试 PDF 处理**
   ```python
   from pathlib import Path
   from utils.file_ops import extract_text_preview_enhanced
   
   result = extract_text_preview_enhanced(Path("inbox/document.pdf"))
   assert result['text'], "文本提取失败"
   assert result['quality_score'] > 0, "质量评分失败"
   print("✅ PDF 处理测试通过")
   ```

3. **测试图片 OCR**
   ```python
   result = extract_text_preview_enhanced(Path("inbox/screenshot.png"))
   assert result['method'] in ['rapidocr', 'rapidocr_cached'], "方法错误"
   print("✅ 图片 OCR 测试通过")
   ```

4. **测试缓存**
   ```python
   # 第一次处理
   result1 = extract_text_preview_enhanced(Path("inbox/document.pdf"))
   
   # 第二次应该命中缓存
   result2 = extract_text_preview_enhanced(Path("inbox/document.pdf"))
   assert "_cached" in result2['method'], "缓存未命中"
   print("✅ 缓存测试通过")
   ```

---

## ⚙️ 配置选项

### OCR 配置 (`config/ocr_config.py`)

```python
from config.ocr_config import update_ocr_config

# 禁用 RapidOCR（图片将无法处理）
update_ocr_config(enable_rapidocr=False)

# 调整 RapidOCR 最大页数
update_ocr_config(rapidocr_max_pages=20)

# 调整 DPI（影响图片质量和速度）
update_ocr_config(rapidocr_dpi=300)  # 更高质量，更慢

# 禁用 Vision LLM（降低成本）
update_ocr_config(enable_vision_llm=False)
```

### 自定义缓存位置

```python
from pathlib import Path
from utils.file_ops import OCRCache

# 使用自定义路径
custom_cache = OCRCache(db_path=Path("my_cache/ocr.db"))

# 使用自定义缓存的提取函数（需要修改代码）
```

---

## 🔧 故障排查

### 问题 1：缓存未命中

**症状**: 多次处理同一文件，method 总是 `rapidocr` 而非 `rapidocr_cached`

**可能原因**:
1. 文件被修改（hash 变了）
2. 质量评分 < 30（不缓存）
3. 使用的是 `direct` 方法（不缓存）

**解决方案**:
```python
from utils.file_ops import compute_file_hash, OCRCache

file_hash = compute_file_hash(Path("file.pdf"))
cache = OCRCache()
cached = cache.get(file_hash)

if cached:
    print("缓存存在")
else:
    print("缓存不存在，可能原因:")
    print("  1. 从未处理过")
    print("  2. 质量太差不缓存")
    print("  3. 使用 direct 方法不缓存")
```

### 问题 2：图片 OCR 失败

**症状**: `result['error']` 不为空，或 `text` 为空

**检查清单**:
- [ ] RapidOCR 是否安装？`pip install rapidocr-onnxruntime`
- [ ] Pillow 是否安装？`pip install Pillow`
- [ ] 图片文件是否损坏？
- [ ] 图片格式是否支持？

**诊断命令**:
```python
try:
    from rapidocr_onnxruntime import RapidOCR
    from PIL import Image
    print("✅ 依赖库已安装")
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
```

### 问题 3：质量评分异常低

**症状**: 明明是清晰的文档，`quality_score` 却 < 60

**可能原因**:
1. 文本中包含大量特殊符号
2. OCR 置信度过低
3. 提取文本过短

**解决方案**:
```python
from utils.file_ops import calculate_quality_score

# 查看详细扣分
text = result['text']
confidence = result['confidence']

score, needs_review = calculate_quality_score(text, confidence)

print(f"文本长度: {len(text)}")
print(f"置信度: {confidence}")
print(f"评分: {score}")

# 如果合理，可以降低阈值
# (需要修改代码中的 needs_review = score < 60)
```

---

## 📚 进阶用法

### 批量预热缓存

```python
from pathlib import Path
from utils.file_ops import extract_text_preview_enhanced

# 批量处理文件，建立缓存
files = Path("archive").rglob("*.pdf")

for i, file_path in enumerate(files, 1):
    print(f"[{i}] 预热缓存: {file_path.name}")
    result = extract_text_preview_enhanced(file_path)
    
    if result['text']:
        print(f"    ✅ 已缓存 (质量={result['quality_score']})")
    else:
        print(f"    ⏭️  跳过 (无法提取)")

print("预热完成！后续处理速度将大幅提升。")
```

### 导出缓存统计

```python
import sqlite3
from pathlib import Path

cache_db = Path.home() / ".digital_janitor" / "ocr_cache.db"
conn = sqlite3.connect(str(cache_db))
cursor = conn.cursor()

# 统计缓存数量
cursor.execute("SELECT COUNT(*) FROM ocr_cache")
count = cursor.fetchone()[0]

# 统计各方法分布
cursor.execute("SELECT method, COUNT(*) FROM ocr_cache GROUP BY method")
methods = cursor.fetchall()

# 平均质量评分
cursor.execute("SELECT AVG(quality_score) FROM ocr_cache")
avg_quality = cursor.fetchone()[0]

print(f"缓存条目: {count}")
print(f"平均质量: {avg_quality:.1f}")
print(f"方法分布:")
for method, cnt in methods:
    print(f"  {method}: {cnt}")

conn.close()
```

---

## 🆚 与 OCR V1 对比

| 特性 | OCR V1 | OCR V2 |
|------|--------|--------|
| PDF 支持 | ✅ | ✅ |
| 图片支持 | ❌ | ✅ |
| OCR 缓存 | ❌ | ✅ |
| 质量评分 | ❌ | ✅ |
| 自动降级 | ✅ | ✅ |
| Vision LLM | ✅ | ✅ |
| 性能优化 | - | 10-100x (缓存) |

---

## 💡 最佳实践

1. **首次运行**: 允许较长的处理时间（建立缓存）
2. **批量处理**: 相同文件会自动复用缓存
3. **质量检查**: 关注 `needs_review` 标记的文件
4. **定期清理**: 如果磁盘空间紧张，可清空缓存
5. **图片质量**: 提供高质量图片以获得更好的 OCR 结果

---

**版本**: OCR V2 (feat/ocr-v2-cache-image)  
**日期**: 2024-12-16  
**维护者**: Digital Janitor Team

