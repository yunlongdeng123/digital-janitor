from __future__ import annotations

import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple, List

import yaml
from pydantic import BaseModel, Field

# ----------------------------
# 1) 数据结构：把 LLM/规则输出“结构化”
# ----------------------------
class RenamePlan(BaseModel):
    category: str = Field(description="invoice/contract/paper/image/default")
    new_name: str
    dest_dir: str
    confidence: float = Field(ge=0.0, le=1.0)
    extracted: Dict[str, str] = Field(default_factory=dict)
    rationale: str = ""


# ----------------------------
# 2) 配置读取
# ----------------------------
def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ----------------------------
# 3) 扫描 inbox
# ----------------------------
def discover_files(inbox: Path) -> List[Path]:
    files: List[Path] = []
    for p in inbox.iterdir():
        if p.is_file() and not p.name.startswith("."):
            files.append(p)
    return sorted(files, key=lambda x: x.name.lower())


# ----------------------------
# 4) 文本抽取：只取前 N 字符（避免慢/贵）
# ----------------------------
def extract_text_preview(path: Path, limit: int = 1000) -> str:
    ext = path.suffix.lower()

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            chunks = []
            for page in reader.pages[:10]:  # 前 10 页通常够用了
                t = page.extract_text() or ""
                if t:
                    chunks.append(t)
                if sum(len(c) for c in chunks) >= limit:
                    break
            return ("\n".join(chunks)).strip()[:limit]
        except Exception as e:
            return f""  # PDF 解析失败先返回空，别让流程崩掉

    if ext == ".docx":
        try:
            import docx
            doc = docx.Document(str(path))
            text = "\n".join(p.text for p in doc.paragraphs if p.text)
            return text.strip()[:limit]
        except Exception:
            return ""

    if ext in [".txt", ".md"]:
        try:
            return path.read_text(encoding="utf-8", errors="ignore").strip()[:limit]
        except Exception:
            return ""

    # 图片 OCR 先不强依赖（Step 2/3 再加），这里先留接口
    if ext in [".png", ".jpg", ".jpeg", ".webp"]:
        return ""

    return ""


# ----------------------------
# 5) 规则 baseline：分类 + 字段抽取
#    后面接 LLM，只需要替换这个函数即可
# ----------------------------
# 关键词列表
KW_INVOICE = ["发票", "价税合计", "税号", "开票", "invoice", "VAT", "增值税", "销方", "购方"]
KW_CONTRACT = ["合同", "协议", "甲方", "乙方", "违约", "条款", "contract", "agreement", "签订", "生效日期"]
KW_PAPER = ["abstract", "introduction", "references", "doi", "arxiv", "论文", "参考文献", "keywords", "citation"]

INVALID_WIN_CHARS = r'<>:"/\\|?*'

# 英文月份映射
MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def safe_filename(s: str, max_len: int = 120) -> str:
    """
    文件名安全处理函数：
    - 去除 Windows 非法字符
    - 将多个空格替换为单个下划线
    - 将多个下划线替换为单个下划线
    - 返回处理后的文件名
    """
    s = s.strip()
    s = re.sub(f"[{re.escape(INVALID_WIN_CHARS)}]", "_", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s[:max_len].strip("_")


def extract_date(text: str, fallback_name: str) -> Optional[str]:
    """
    日期提取函数，支持多种格式：
    - 数字格式: 2025-01-18 / 2025/01 / 2025年1月
    - 英文月份: Jan 2025, January 2025, 15 Jan 2025
    """
    combined = text + " " + fallback_name
    
    # Pattern 1: 标准数字格式 YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD
    patterns_numeric = [
        r"(20\d{2})[-/\.](0?[1-9]|1[0-2])[-/\.](0?[1-9]|[12]\d|3[01])",
        r"(20\d{2})[-/\.](0?[1-9]|1[0-2])",
        r"(20\d{2})年(0?[1-9]|1[0-2])月",
    ]
    for pat in patterns_numeric:
        m = re.search(pat, combined)
        if m:
            y = int(m.group(1))
            mth = int(m.group(2))
            return f"{y:04d}-{mth:02d}"

    # Pattern 2: 英文月份 + 日 + 逗号 + 年 (Dec 14, 2025 / December 14, 2025)
    month_names = "|".join(sorted(MONTH_MAP.keys(), key=len, reverse=True))
    m = re.search(rf"\b({month_names})\b\s+\d{{1,2}},\s*(20\d{{2}})", combined, re.IGNORECASE)
    if m:
        month_str = m.group(1).lower()
        year = int(m.group(2))
        month = MONTH_MAP.get(month_str)
        if month:
            return f"{year:04d}-{month:02d}"

    
    # Pattern 3: 英文月份格式 (Jan 2025, January 2025, 15 Jan 2025)
    # 匹配: 数字? 月份名 数字(年份)
    month_pattern = r"(?:\d{1,2}\s+)?(" + "|".join(MONTH_MAP.keys()) + r")\s+(20\d{2})"
    m = re.search(month_pattern, combined, re.IGNORECASE)
    if m:
        month_str = m.group(1).lower()
        year = int(m.group(2))
        month = MONTH_MAP.get(month_str)
        if month:
            return f"{year:04d}-{month:02d}"
    
    # Pattern 4: 文件名中的简化格式 YYYY_MM 或 YYYY-MM
    m = re.search(r"(20\d{2})[-_](0[1-9]|1[0-2])", fallback_name)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    
    return None


def extract_amount(text: str) -> Optional[str]:
    """
    金额提取函数：
    Priority 1: 带货币符号的金额 (¥/￥)
    Priority 2: 带单位的金额 (元/CNY/RMB)
    避免将长数字串（如发票号）误认为金额
    """
    
    def parse_amount(num_str: str) -> Optional[str]:
        """解析金额字符串，返回格式化结果"""
        num_str = num_str.replace(",", "").replace(" ", "")
        try:
            val = float(num_str)
            # 过滤不合理的金额（年份、发票号等）
            if val < 1 or val > 10_000_000:
                return None
            # 整数就别带 .0
            if abs(val - int(val)) < 1e-9:
                return f"{int(val)}元"
            return f"{val:.2f}元"
        except Exception:
            return None
    
    # Priority 1: 匹配带货币符号的金额 (¥/￥ + 数字)
    # 使用 \d+ 而不是 \d{1,3} 避免截断
    pattern_currency = r"[¥￥]\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)"
    m = re.search(pattern_currency, text)
    if m:
        result = parse_amount(m.group(1))
        if result:
            return result
    
    # Priority 2: 匹配带单位的金额 (数字 + 元/人民币/CNY/RMB)
    # 避免误匹配发票号等长数字串
    pattern_unit = r"(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:元|人民币|CNY|RMB)"
    matches = re.finditer(pattern_unit, text)
    for m in matches:
        # 检查前后字符，避免是连续数字的一部分
        start_pos = m.start()
        end_pos = m.end()
        # 前面不能是数字
        if start_pos > 0 and text[start_pos-1].isdigit():
            continue
        # 后面如果紧跟数字，跳过
        if end_pos < len(text) and text[end_pos].isdigit():
            continue
        result = parse_amount(m.group(1))
        if result:
            return result
    
    # Priority 3: 如果文本中包含"价税合计"/"总计"等关键词，尝试提取其后的数字
    keywords = ["价税合计", "总计", "合计金额", "应付金额", "total"]
    for kw in keywords:
        if kw in text.lower():
            # 在关键词后 100 字符内查找金额
            idx = text.lower().find(kw)
            snippet = text[idx:idx+100]
            pattern_after_kw = r"[¥￥]?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:元|人民币)?"
            m = re.search(pattern_after_kw, snippet)
            if m:
                result = parse_amount(m.group(1))
                if result:
                    return result
    
    return None


def guess_source(text: str, filename: str) -> str:
    """
    猜测文件来源函数：
    - 从文本中猜测文件来源
    - 从文件名中猜测文件来源
    - 返回猜测的文件来源
    """
    candidates = ["京东", "淘宝", "拼多多", "美团", "微信", "支付宝", "滴滴", "携程"]
    for c in candidates:
        if c in text or c in filename:
            return c
    return "未知来源"


def classify(text: str, path: Path) -> Tuple[str, float, str]:
    """
    优化的分类函数：使用打分制（Scoring）而非 if-else 顺序匹配
    - 统计每个类别的关键词命中次数
    - 文件名命中给予额外加分
    - 返回得分最高的分类
    """
    t = text.lower()
    name = path.name.lower()
    ext = path.suffix.lower()

    # 图片特殊处理：先归 image，但如果发票关键词高分命中，可归为 invoice
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]:
        invoice_score = sum(1 for kw in KW_INVOICE if kw.lower() in t or kw.lower() in name)
        if invoice_score >= 2:  # 至少命中 2 个发票关键词
            return "invoice", 0.75, f"图片但发票关键词高分命中(score={invoice_score})"
        return "image", 0.60, "图片默认归类"

    # 打分制：统计每个类别的关键词命中次数
    scores = {
        "invoice": 0,
        "contract": 0,
        "paper": 0,
    }
    
    # 文本内容匹配（每个关键词 +1 分）
    for kw in KW_INVOICE:
        if kw.lower() in t:
            scores["invoice"] += 1
    
    for kw in KW_CONTRACT:
        if kw.lower() in t:
            scores["contract"] += 1
    
    for kw in KW_PAPER:
        if kw.lower() in t:
            scores["paper"] += 1
    
    # 文件名匹配（额外加分，权重 x2）
    for kw in KW_INVOICE:
        if kw.lower() in name:
            scores["invoice"] += 2
    
    for kw in KW_CONTRACT:
        if kw.lower() in name:
            scores["contract"] += 2
    
    for kw in KW_PAPER:
        if kw.lower() in name:
            scores["paper"] += 2
    
    # 文件扩展名加分
    if ext == ".pdf":
        # PDF 更可能是发票或合同
        scores["invoice"] += 0.5
        scores["contract"] += 0.5
    
    # 找出得分最高的类别
    max_score = max(scores.values())
    
    if max_score == 0:
        # 没有任何命中，归为默认
        return "default", 0.50, "未命中关键词，默认归类"
    
    # 返回得分最高的类别
    winner = max(scores, key=scores.get)
    confidence = min(0.95, 0.60 + max_score * 0.05)  # 分数越高，置信度越高，最高 0.95
    
    details = f"{winner}关键词命中(score={max_score:.1f})"
    
    return winner, confidence, details


def propose_plan(path: Path, text_preview: str, archive_root: Path) -> RenamePlan:
    """
    文件重命名函数：
    - 使用打分制分类
    - 支持多种日期格式提取
    - 金额提取更鲁棒，避免误匹配
    - 标题提取更智能，避免重复金额
    - 归档路径更灵活，支持按年月归档
    - 文件名生成更安全，避免 Windows 非法字符
    """
    cat, conf, why = classify(text_preview, path)

    date_ym = extract_date(text_preview, path.stem) or "未知日期"
    amount = extract_amount(text_preview) or ""
    source = guess_source(text_preview, path.name)

    # 标题：优先取文本第一行，否则用文件名
    title = (text_preview.strip().splitlines()[0] if text_preview.strip() else path.stem)
    title = safe_filename(title, max_len=60)
    if not title:
        title = safe_filename(path.stem, max_len=60)

    cat_cn = {
        "invoice": "发票",
        "contract": "合同",
        "paper": "论文",
        "image": "图片",
        "default": "其他",
    }.get(cat, "其他")

    # 归档路径：archive/<类别>/<年>/<月>/
    if re.match(r"20\d{2}-\d{2}", date_ym):
        y, m = date_ym.split("-")
        dest_dir = archive_root / cat_cn / y / m
    else:
        dest_dir = archive_root / cat_cn / "未知日期"

    parts = [f"[{cat_cn}]", date_ym, source, title]

    # 金额去重（Deduplication）：如果标题/原文件名里已经出现了金额数字，就别再 append
    if amount:
        amt_core = re.sub(r"[^\d.]", "", amount)  # 例如 "35.50元" -> "35.50"
        already_in_title = bool(amt_core) and (amt_core in title)
        already_in_name = bool(amt_core) and (amt_core in path.stem)
        if not (already_in_title or already_in_name):
            parts.append(amount)

    new_stem = safe_filename("_".join([p for p in parts if p]), max_len=120)
    new_name = f"{new_stem}{path.suffix.lower()}"

    return RenamePlan(
        category=cat,
        new_name=new_name,
        dest_dir=str(dest_dir),
        confidence=conf,
        extracted={"date_ym": date_ym, "amount": amount, "source": source, "title": title},
        rationale=why,
    )


def main():
    """
    主函数：
    - 解析命令行参数
    - 加载配置
    - 确保目录存在
    - 扫描文件
    - 生成计划
    - 写入计划
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="config.yaml")
    ap.add_argument("--preview", type=int, default=1000)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--write_plan", action="store_true", help="把计划写到 logs/ 里（jsonl）")
    args = ap.parse_args()

    # 增强日志：打印配置加载信息
    config_path = Path(args.config)
    print(f"[INFO] Loading config from [{config_path.resolve()}]...")
    
    try:
        cfg = load_config(config_path)
        print(f"[OK] Config loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        return

    # 修复 Bug：直接使用字典访问，config.yaml 中 paths 是字典而非列表
    try:
        inbox = Path(cfg["paths"]["inbox"])
        archive = Path(cfg["paths"]["archive"])
        logs = Path(cfg["paths"]["logs"])
        dry_run = bool(cfg.get("dry_run", True))
    except KeyError as e:
        print(f"[ERROR] Config missing required key: {e}")
        print(f"[HINT] Make sure config.yaml has 'paths' with 'inbox', 'archive', 'logs' keys.")
        return

    # 确保目录存在
    print(f"[INFO] Ensuring directories exist...")
    inbox.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Directories ready.")

    # 扫描文件
    print(f"[INFO] Scanning inbox for files...")
    files = discover_files(inbox)[: args.limit]
    if not files:
        print(f"[WARN] inbox 为空：{inbox.resolve()}")
        print(f"[HINT] 请将需要整理的文件放入 inbox 目录")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = logs / f"plan_{ts}.jsonl"

    print("")
    print(f"=== Digital Janitor Step1 ===")
    print(f"inbox   : {inbox.resolve()}")
    print(f"archive : {archive.resolve()}")
    print(f"dry_run : {dry_run}")
    print(f"files   : {len(files)}")
    print("")

    lines = []
    for p in files:
        text = extract_text_preview(p, limit=args.preview)
        plan = propose_plan(p, text, archive_root=archive)

        print(f"- FILE: {p.name}")
        print(f"  category   : {plan.category}  (conf={plan.confidence:.2f}, {plan.rationale})")
        print(f"  suggest    : {plan.new_name}")
        print(f"  dest_dir   : {plan.dest_dir}")
        print(f"  extracted  : {plan.extracted}")
        print(f"  action     : {'PRINT-ONLY (dry_run)' if dry_run else 'WILL-APPLY (but Step1 still not applying)'}")
        print("")

        record = {"file": str(p), "preview": text[:200], "plan": plan.model_dump()}
        lines.append(record)

    if args.write_plan:
        with out_path.open("w", encoding="utf-8") as f:
            for r in lines:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[OK] plan 写入：{out_path.resolve()}")


if __name__ == "__main__":
    main()
