# Core 模块文档

核心功能模块，包含数据结构、LLM 处理器和校验器。

## 模块结构

```
core/
├── __init__.py          # 模块初始化和导出
├── schemas.py           # 数据结构定义
├── llm_processor.py     # LLM 处理器
├── validator.py         # 校验器
├── test_llm.py         # LLM 测试脚本
└── test_validator.py   # 校验器测试脚本
```

## 数据结构

### FileAnalysis

LLM 分析结果的数据结构：

```python
from core.schemas import FileAnalysis

analysis = FileAnalysis(
    category="invoice",
    confidence=0.95,
    extracted_date="2024-03",
    extracted_amount="1580元",
    vendor_or_party="阿里云",
    title="云服务费用",
    suggested_filename="[发票]_2024-03_阿里云_云服务费用_1580元",
    rationale="文档包含发票关键词、税号、价税合计等信息",
    metadata={"tax_id": "91110000123456789X"}
)
```

### RenamePlan

文件重命名计划的数据结构：

```python
from core.schemas import RenamePlan

plan = RenamePlan(
    category="invoice",
    new_name="[发票]_2024-03_阿里云_1580元.pdf",
    dest_dir="archive/发票/2024/03",
    confidence=0.95,
    extracted={"date_ym": "2024-03", "amount": "1580元"},
    rationale="发票关键词命中(score=9.0)",
    is_valid=True,
    validation_msg="校验通过"
)
```

## LLM 处理器

使用大语言模型分析文件内容并提取结构化信息。

### 基础使用

```python
from core.llm_processor import analyze_file

# 分析单个文件
text = "发票内容..."
filename = "invoice.pdf"
result = analyze_file(text, filename)

print(f"类别: {result.category}")
print(f"置信度: {result.confidence}")
print(f"建议文件名: {result.suggested_filename}")
```

### 批量处理

```python
from core.llm_processor import analyze_file_batch

files = [
    ("发票内容1", "invoice1.pdf"),
    ("合同内容2", "contract2.pdf"),
]

results = analyze_file_batch(files, max_workers=3)
```

### 环境配置

需要设置以下环境变量：

```bash
# .env 文件
OPENAI_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-3.5-turbo  # 可选
OPENAI_API_BASE=https://api.openai.com/v1  # 可选
```

## 校验器

对重命名计划进行安全性和有效性校验。

### 基础使用

```python
from core.schemas import RenamePlan
from core.validator import validate_plan

# 创建计划
plan = RenamePlan(
    category="invoice",
    new_name="发票<>:*.pdf",  # 包含非法字符
    dest_dir="../../../etc",  # 危险路径
    confidence=0.95
)

# 校验
result = validate_plan(plan)

if result.is_valid:
    print("✅ 校验通过")
else:
    print(f"❌ 校验失败: {result.validation_msg}")
```

### 批量校验

```python
from core.validator import validate_plans_batch, get_validation_stats

plans = [plan1, plan2, plan3]

# 批量校验
results = validate_plans_batch(plans)

# 获取统计
stats = get_validation_stats(results)
print(f"通过: {stats['valid']}/{stats['total']}")
print(f"失败: {stats['invalid']}")
```

### 校验规则

#### 文件名校验

- ✅ 自动清理 Windows 非法字符：`<>:"/\|?*`
- ✅ 去除首尾空格和点号
- ✅ 检测 Windows 保留名称：CON, PRN, AUX, NUL, COM1-9, LPT1-9
- ✅ 检查文件名长度（最大 255 字符）

#### 路径校验

- ✅ 防止目录穿越：禁止 `..` 父目录引用
- ✅ 强制相对路径：禁止绝对路径
- ✅ 检测危险前缀：`/`, `\`, `C:`, `D:` 等
- ✅ 检查路径中的非法字符

## 测试

### 运行 LLM 测试

```bash
# 需要先配置 .env 文件
python core/test_llm.py
```

### 运行校验器测试

```bash
python core/test_validator.py
```

## 集成示例

完整的文件处理流程：

```python
from pathlib import Path
from core.llm_processor import analyze_file
from core.schemas import RenamePlan
from core.validator import validate_plan

# 1. 读取文件
file_path = Path("inbox/document.pdf")
text = file_path.read_text(encoding="utf-8", errors="ignore")[:1000]

# 2. LLM 分析
analysis = analyze_file(text, file_path.name)

# 3. 构建重命名计划
plan = RenamePlan(
    category=analysis.category,
    new_name=f"{analysis.suggested_filename}{file_path.suffix}",
    dest_dir=f"archive/{analysis.category}/2024",
    confidence=analysis.confidence,
    extracted={
        "date": analysis.extracted_date,
        "amount": analysis.extracted_amount,
        "vendor": analysis.vendor_or_party
    },
    rationale=analysis.rationale
)

# 4. 校验计划
validated_plan = validate_plan(plan)

# 5. 执行重命名（如果校验通过）
if validated_plan.is_valid:
    dest_path = Path(validated_plan.dest_dir) / validated_plan.new_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.rename(dest_path)
    print(f"✅ 文件已移动: {dest_path}")
else:
    print(f"❌ 校验失败: {validated_plan.validation_msg}")
```

## 依赖

- `pydantic>=2.5.0` - 数据验证
- `langchain-openai>=0.1.0` - LLM 集成（可选）
- `langchain-core>=0.2.0` - LangChain 核心（可选）
- `python-dotenv>=1.0.0` - 环境变量管理

## 注意事项

1. **LLM 模块**：如果未安装 `langchain-openai`，只能使用 schemas 和 validator 模块
2. **API 密钥**：使用 LLM 功能需要配置有效的 OpenAI API 密钥
3. **编码问题**：Windows 环境下运行测试脚本时已处理 UTF-8 编码问题
4. **安全性**：校验器会自动防护常见的安全风险（目录穿越、非法字符等）

## 版本

当前版本: 0.1.0

