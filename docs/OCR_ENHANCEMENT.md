# 智能 PDF 识别增强 - OCR Fallback 功能

## 功能概览

Digital Janitor 现在支持智能 PDF 识别，能够自动处理扫描件 PDF。系统会根据文档特征，智能选择最优的文本提取策略。

### 三层识别策略

```
┌─────────────────────────────────────────┐
│  1. 标准提取 (pypdf)                     │
│     ↓ 如果文本质量差                      │
│  2. OCR Fallback                        │
│     ├─ RapidOCR (本地)                  │
│     └─ Vision LLM (云端，重要文档)       │
└─────────────────────────────────────────┘
```

---

## 使用方法

### 基础使用

```python
from pathlib import Path
from utils.file_ops import extract_text_preview_enhanced

# 自动选择最优策略
result = extract_text_preview_enhanced(Path("invoice.pdf"))

print(f"提取方法: {result['method']}")
print(f"置信度: {result['confidence']}")
print(f"文本预览: {result['text'][:200]}...")
print(f"处理耗时: {result['processing_time_ms']}ms")
```

### 返回格式

```python
{
    "text": str,              # 提取的文本内容
    "method": str,            # "direct" | "rapidocr" | "vision_llm" | "direct_fallback"
    "confidence": float,      # 0.0 - 1.0
    "page_count": int,        # PDF 页数
    "char_count": int,        # 提取的字符数
    "processing_time_ms": int,# 处理耗时（毫秒）
    "error": str | None       # 错误信息（如有）
}
```

---

## 触发条件

### OCR 会在以下情况触发：

1. **完全空文本** - pypdf 无法提取任何文本
2. **字符密度过低** - 平均每页 < 100 字符
3. **空白符过多** - 空白符占比 > 90%
4. **乱码比例高** - 非常见字符 > 30%

### Vision LLM 会在以下情况触发：

1. **文档被标记为重要**（文件名包含关键词：发票、合同、报告等）
2. **文件大小适中**（100KB - 10MB）
3. **页数较少**（≤ 5 页）

---

## 配置

### 环境变量

在 `.env` 文件中配置：

```bash
# Vision LLM 配置（可选）
VISION_MODEL_NAME=Qwen/Qwen3-VL-30B-A3B-Thinking
VISION_API_KEY=your-api-key-here
VISION_API_BASE=https://api.siliconflow.cn/v1

# 如果 Vision LLM 和文本 LLM 用同一个 API
# 可以只配置 OPENAI_API_KEY 和 OPENAI_API_BASE
```

### 代码配置

修改 `config/ocr_config.py`：

```python
from config.ocr_config import OCR_CONFIG, update_ocr_config

# 查看当前配置
print(OCR_CONFIG.rapidocr_max_pages)  # 10

# 更新配置
update_ocr_config(
    rapidocr_max_pages=20,          # RapidOCR 最多处理 20 页
    vision_max_pages=5,              # Vision LLM 最多处理 5 页
    enable_vision_llm=True,          # 启用 Vision LLM
    enable_rapidocr=True,            # 启用 RapidOCR
    ocr_trigger_chars_per_page=100,  # 触发阈值
)
```

### 配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `rapidocr_max_pages` | 10 | RapidOCR 最多处理页数 |
| `rapidocr_min_confidence` | 0.5 | 最小置信度阈值 |
| `rapidocr_dpi` | 200 | 图片 DPI（影响性能和精度） |
| `vision_max_pages` | 3 | Vision LLM 最多处理页数 |
| `vision_dpi` | 150 | Vision LLM 图片 DPI |
| `ocr_trigger_chars_per_page` | 100 | 触发 OCR 的字符密度阈值 |
| `ocr_trigger_garbage_ratio` | 0.3 | 触发 OCR 的乱码比例阈值 |
| `enable_vision_llm` | True | 是否启用 Vision LLM（成本控制） |
| `enable_rapidocr` | True | 是否启用 RapidOCR |

---

## 系统依赖

### Python 包（自动安装）

```bash
pip install -r requirements.txt
```

包含：
- `rapidocr-onnxruntime>=1.3.0` - 本地 OCR 引擎
- `pdf2image>=1.16.0` - PDF 转图片
- `Pillow>=10.0.0` - 图像处理

### 系统依赖（手动安装）

`pdf2image` 需要系统安装 **poppler**：

**Windows:**
1. 下载 poppler: https://github.com/oschwartz10612/poppler-windows/releases
2. 解压到 `C:\Program Files\poppler`
3. 添加 `C:\Program Files\poppler\Library\bin` 到系统 PATH

**macOS:**
```bash
brew install poppler
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install poppler-utils
```

### 验证安装

```python
from pdf2image import convert_from_path

# 如果没有报错，说明 poppler 安装成功
print("✅ poppler 安装成功")
```

---

## 性能和成本

### 处理时间

| 方法 | 单页耗时 | 适用场景 |
|------|---------|---------|
| **Direct (pypdf)** | ~50ms | 电子版 PDF |
| **RapidOCR** | ~500ms | 普通扫描件 |
| **Vision LLM** | ~2-5s | 重要文档、复杂版式 |

### 成本

| 方法 | 成本 |
|------|------|
| **Direct** | 免费 |
| **RapidOCR** | 免费（本地计算） |
| **Vision LLM** | 按 Token 计费（~0.001-0.01元/页） |

**成本控制建议：**
1. 仅对重要文档启用 Vision LLM
2. 设置合理的 `vision_max_pages` 限制
3. 使用 `enable_vision_llm=False` 完全禁用

---

## 工作流程

### 完整处理流程

```
┌─────────────────────┐
│   读取 PDF 文件      │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  pypdf 标准提取      │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ should_use_ocr()?   │
└──────┬──────────────┘
       ↓ Yes
┌──────────────────────┐
│ is_important_doc()?  │
└──────┬──────────────┘
       ↓ Yes              ↓ No
┌─────────────┐    ┌─────────────┐
│ Vision LLM  │    │ RapidOCR    │
└─────────────┘    └─────────────┘
       ↓                  ↓
┌─────────────────────────┐
│  返回提取结果            │
└─────────────────────────┘
```

### 决策逻辑

```python
def choose_extraction_method(pdf_path, direct_text, page_count):
    """选择提取方法的伪代码"""
    
    # 1. 判断是否需要 OCR
    needs_ocr, reason = should_use_ocr(direct_text, page_count)
    
    if not needs_ocr:
        return "direct"  # 使用标准提取
    
    # 2. 判断是否使用 Vision LLM
    if is_important_document(pdf_path) and page_count <= 5:
        if VISION_LLM_ENABLED:
            return "vision_llm"
    
    # 3. 使用 RapidOCR
    if RAPIDOCR_ENABLED:
        return "rapidocr"
    
    # 4. Fallback 到原始文本
    return "direct_fallback"
```

---

## 日志和调试

### 启用详细日志

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 或针对特定模块
logging.getLogger("utils.file_ops").setLevel(logging.DEBUG)
logging.getLogger("core.llm_processor").setLevel(logging.DEBUG)
```

### 日志输出示例

```
INFO: 触发 OCR: invoice_scan.pdf - 字符密度过低（12.3 字符/页），可能是扫描件
INFO: 文档被标记为重要: invoice_scan.pdf (关键词匹配=True, 大小=523.4KB, 页数=2)
INFO: 使用 Vision LLM 处理重要文档: invoice_scan.pdf
INFO: Vision LLM 分析完成: invoice_scan.pdf | 页数=2 | Tokens=3421
INFO: 文本提取完成: invoice_scan.pdf | 方法=vision_llm | 置信度=0.95 | 字符数=1523 | 耗时=3245ms
```

---

## 常见问题

### Q1: RapidOCR 识别精度不高？

**解决方案：**
1. 提高 DPI：`update_ocr_config(rapidocr_dpi=300)`
2. 降低置信度阈值：`update_ocr_config(rapidocr_min_confidence=0.3)`
3. 对重要文档使用 Vision LLM

### Q2: Vision LLM 成本过高？

**解决方案：**
1. 减少触发条件：修改 `important_keywords` 列表
2. 限制页数：`update_ocr_config(vision_max_pages=1)`
3. 完全禁用：`update_ocr_config(enable_vision_llm=False)`

### Q3: pdf2image 报错 "Unable to find pdftoppm"？

**解决方案：**
- 需要安装 poppler（参见 "系统依赖" 部分）

### Q4: 如何查看处理了哪些文件？

**解决方案：**
查看日志文件 `logs/*.jsonl`，包含每个文件的处理方法和结果。

---

## 测试

### 运行单元测试

```bash
# 激活虚拟环境
conda activate janitor

# 运行测试
pytest tests/test_ocr_fallback.py -v

# 运行特定测试
pytest tests/test_ocr_fallback.py::TestOcrFallback::test_should_use_ocr_empty_text -v
```

### 手动测试

```python
from pathlib import Path
from utils.file_ops import extract_text_preview_enhanced

# 测试扫描 PDF
result = extract_text_preview_enhanced(Path("inbox/scanned_invoice.pdf"))

assert result["method"] in ["rapidocr", "vision_llm"]
assert result["confidence"] > 0.5
print(f"✅ 测试通过：{result['method']}")
```

---

## 最佳实践

### 1. 分阶段启用

```python
# 第一阶段：只启用 RapidOCR（免费）
update_ocr_config(
    enable_rapidocr=True,
    enable_vision_llm=False
)

# 观察效果后，第二阶段：启用 Vision LLM（部分文档）
update_ocr_config(
    enable_vision_llm=True,
    important_max_pages=2  # 只处理 2 页以内的重要文档
)
```

### 2. 监控成本

```python
# 记录 Vision LLM 调用次数
vision_count = 0
vision_tokens = 0

for file in files:
    result = extract_text_preview_enhanced(file)
    if result["method"] == "vision_llm":
        vision_count += 1
        vision_tokens += result.get("tokens_used", 0)

print(f"Vision LLM 调用次数: {vision_count}")
print(f"总 Tokens: {vision_tokens}")
print(f"预估成本: {vision_tokens * 0.000001}元")  # 假设 1M tokens = 1元
```

### 3. 优化关键词列表

```python
# 根据实际业务调整关键词
from config.ocr_config import update_ocr_config

update_ocr_config(
    important_keywords=[
        'invoice', '发票',      # 财务文档
        'contract', '合同',     # 法律文档
        'report', '报告',       # 业务报告
        '证明', 'certificate',  # 证明文件
        # 移除不重要的关键词以降低成本
    ]
)
```

---

## 技术细节

### should_use_ocr() 算法

```python
def should_use_ocr(text: str, page_count: int) -> tuple[bool, str]:
    """
    多维度判断是否需要 OCR：
    
    1. 文本密度检查
       - 计算 chars_per_page = char_count / page_count
       - 如果 < 100，触发 OCR
    
    2. 空白符检查
       - 计算 whitespace_ratio = whitespace_count / total_chars
       - 如果 > 0.9，触发 OCR
    
    3. 乱码检查
       - 统计常见字符（中文、英文、数字、标点）
       - 计算 garbage_ratio = 1 - (normal_chars / total_chars)
       - 如果 > 0.3，触发 OCR
    """
```

### RapidOCR 工作流程

```python
def extract_with_rapidocr(pdf_path: Path) -> dict:
    """
    1. pdf2image.convert_from_path() 
       - DPI=200 (平衡性能和精度)
       - 限制页数避免内存溢出
    
    2. RapidOCR.ocr(image)
       - 返回 [box, text, confidence] 列表
    
    3. 过滤低置信度结果
       - confidence >= min_confidence (默认 0.5)
    
    4. 合并所有文本
       - 按页面顺序连接
    """
```

---

## 更新日志

### v1.0 (2024-12-15)
- ✨ 新增智能 OCR fallback 机制
- ✨ 集成 RapidOCR 本地识别
- ✨ 集成 Vision LLM 多模态识别
- ✨ 新增重要文档自动判断
- ✨ 完整的配置系统和日志
- 📝 完善的文档和测试

---

## 参考资料

- [RapidOCR 官方文档](https://github.com/RapidAI/RapidOCR)
- [pdf2image 文档](https://github.com/Belval/pdf2image)
- [Qwen-VL 模型](https://github.com/QwenLM/Qwen-VL)
- [poppler 工具集](https://poppler.freedesktop.org/)

---

**有问题？** 查看 [主文档](./GUIDE.md) 或提交 Issue。

