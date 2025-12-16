"""
LLM 处理器模块
使用大语言模型分析文件内容并提取结构化信息
支持视觉 LLM 分析扫描 PDF
"""

import os
import time
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from core.schemas import FileAnalysis

# 配置日志
logger = logging.getLogger(__name__)


# 初始化 LLM 客户端（从环境变量读取配置）
def get_llm_client() -> ChatOpenAI:
    """
    获取 LLM 客户端实例
    从环境变量读取配置：
    - LLM_MODEL: 模型名称（默认: gpt-3.5-turbo）
    - OPENAI_API_BASE: API 基础URL（可选）
    - OPENAI_API_KEY: API 密钥
    """
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    api_base = os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY", "sk-dummy")
    
    kwargs = {
        "model": model,
        "api_key": api_key,
        "temperature": 0.1,  # 低温度，更确定性的输出
    }
    
    # 如果设置了自定义 API base，添加到参数中
    if api_base:
        kwargs["base_url"] = api_base
    
    return ChatOpenAI(**kwargs)

def get_vision_llm_client() -> ChatOpenAI:
    """
    获取视觉 LLM 客户端 (Qwen-VL)
    """
    # 优先读取 VISION_ 开头的配置，如果没有则回退到默认的 OPENAI_ 配置
    model = os.getenv("VISION_MODEL_NAME", "Qwen/Qwen3-VL-30B-A3B-Thinking")
    
    # 如果视觉模型和文本模型用同一个平台（如 SiliconFlow），可以复用 API Key
    api_key = os.getenv("VISION_API_KEY", os.getenv("OPENAI_API_KEY"))
    api_base = os.getenv("VISION_API_BASE", os.getenv("OPENAI_API_BASE"))
    
    if not api_key:
        raise ValueError("未配置 API Key")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=api_base,
        temperature=0.1, # 视觉任务通常需要低温度以保证准确
        max_tokens=2048  # 视觉描述通常需要较长输出
    )


def analyze_file(text: str, filename: str, max_preview: int = 1000) -> FileAnalysis:
    """
    使用 LLM 分析文件内容，返回结构化的文件元数据
    
    Args:
        text: 文件内容预览（可能为空）
        filename: 原始文件名
        max_preview: 最大预览字符数（默认 1000）
    
    Returns:
        FileAnalysis: 结构化的文件分析结果
    
    Raises:
        Exception: 当 LLM 调用失败时抛出异常
    """
    # 获取 LLM 客户端
    llm = get_llm_client()
    
    # 使用 structured output 强制返回 FileAnalysis 格式
    structured_llm = llm.with_structured_output(FileAnalysis)
    
    # 截断文本预览
    text_preview = text[:max_preview] if text else ""
    has_content = bool(text_preview.strip())
    
    # 构建系统提示词
    system_prompt = """你是一个专业的文件归档助手。你的任务是根据文件名和文件内容预览，推断文件的元数据。

**分类规则：**
- invoice (发票): 包含发票、税号、价税合计、增值税等关键词
- contract (合同): 包含合同、协议、甲方、乙方、违约、条款等关键词
- paper (论文): 包含 abstract, references, DOI, arxiv, 学术关键词等
- image (图片): 图片文件（.png, .jpg 等）
- presentation (演示文稿): 包含幻灯片、PPT、汇报、演讲稿、Business Plan、产品发布会、培训材料等
- default (其他): 无法明确分类的文件

**提取信息：**
1. extracted_date: 日期（格式 YYYY-MM 或 YYYY-MM-DD）
2. extracted_amount: 金额（例如: 1580元）
3. vendor_or_party: 供应商/对方公司/作者名称
4. title: 文件标题或主题（简短、清晰）
5. suggested_filename: 建议的文件名，格式为 [类别]_日期_对方_标题_金额（如适用）

**注意事项：**
- 如果内容为空，仅根据文件名判断
- 置信度反映你对分类的确定程度（0-1）
- 日期优先提取 YYYY-MM 格式
- 金额需带"元"单位
- 标题要简洁，不超过 30 个字符
- rationale 简要说明分类依据"""

    # 构建用户提示词
    if has_content:
        user_prompt = f"""请分析以下文件：

**文件名**: {filename}

**文件内容预览**:
{text_preview}

请根据上述信息，提取文件的元数据并进行分类。"""
    else:
        user_prompt = f"""请分析以下文件：

**文件名**: {filename}

**注意**: 文件内容为空或无法读取，请仅根据文件名进行判断。

请根据上述信息，提取文件的元数据并进行分类。"""
    
    # 调用 LLM
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        result: FileAnalysis = structured_llm.invoke(messages)
        return result
        
    except Exception as e:
        # LLM 调用失败时，返回一个默认的 fallback 结果
        print(f"[WARN] LLM 调用失败: {e}")
        print(f"[INFO] 使用 fallback 规则处理文件: {filename}")
        
        # 返回一个保守的默认分类
        return FileAnalysis(
            category="default",
            confidence=0.3,
            extracted_date=None,
            extracted_amount=None,
            vendor_or_party=None,
            title=filename,
            suggested_filename=f"[其他]_{filename}",
            rationale=f"LLM 调用失败，使用 fallback 规则: {str(e)[:100]}",
            metadata={}
        )


def analyze_file_batch(files: list[tuple[str, str]], max_workers: int = 3) -> list[FileAnalysis]:
    """
    批量分析文件（并发处理）
    
    Args:
        files: (text, filename) 元组列表
        max_workers: 最大并发数
    
    Returns:
        FileAnalysis 结果列表
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(analyze_file, text, filename): (text, filename)
            for text, filename in files
        }
        
        for future in as_completed(future_to_file):
            text, filename = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"[ERROR] 处理文件 {filename} 失败: {e}")
                # 添加一个 fallback 结果
                results.append(FileAnalysis(
                    category="default",
                    confidence=0.2,
                    extracted_date=None,
                    extracted_amount=None,
                    vendor_or_party=None,
                    title=filename,
                    suggested_filename=f"[其他]_{filename}",
                    rationale=f"批量处理失败: {str(e)[:100]}",
                    metadata={}
                ))
    
    return results


# ==================== 视觉 LLM 分析功能 ====================


async def analyze_scanned_pdf_with_vision(
    pdf_path: Path,
    llm_instance: Optional[ChatOpenAI] = None,
    max_pages: int = 3,
    dpi: int = 150
) -> Dict[str, Any]:
    """
    使用 Vision LLM 分析扫描 PDF（异步版本）
    
    参数：
    - pdf_path: PDF 文件路径
    - llm_instance: 可选的 LLM 实例（如果为 None 则自动创建）
    - max_pages: 最多分析前 N 页
    - dpi: 图片质量（150 适合文档识别）
    
    返回格式：
    {
        "text": str,  # 提取的文本内容
        "confidence": float,  # 固定 0.95（LLM 识别）
        "pages_analyzed": int,
        "elapsed_ms": int,
        "tokens_used": int,  # 用于成本追踪
        "error": str | None
    }
    """
    start_time = time.time()
    result: Dict[str, Any] = {
        "text": "",
        "confidence": 0.95,
        "pages_analyzed": 0,
        "elapsed_ms": 0,
        "tokens_used": 0,
        "error": None
    }
    
    try:
        # 1. 导入依赖
        from pdf2image import convert_from_path
        from PIL import Image
        import io
        from config.ocr_config import OCR_CONFIG
        
        # 2. 获取 Vision LLM 实例
        if llm_instance is None:
            llm_instance = get_vision_llm_client()
        
        # 3. 转换 PDF 为图片
        try:
            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=1,
                last_page=min(max_pages, 999)
            )
            result["pages_analyzed"] = len(images)
        except Exception as e:
            result["error"] = f"PDF 转图片失败: {str(e)}"
            logger.error(result["error"])
            return result
        
        # 4. 转换图片为 base64
        image_contents = []
        for idx, image in enumerate(images, 1):
            try:
                # 转换为 JPEG 格式并编码为 base64
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=85)
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                })
                
                logger.debug(f"处理第 {idx}/{len(images)} 页，图片大小: {len(img_base64)} bytes")
                
            except Exception as e:
                logger.warning(f"处理第 {idx} 页图片失败: {e}")
                continue
        
        if not image_contents:
            result["error"] = "没有可用的图片"
            return result
        
        # 5. 构造多模态消息
        content = [
            {
                "type": "text",
                "text": "请准确提取文档中的所有文本内容，保持原有格式和结构。"
            }
        ] + image_contents
        
        message = HumanMessage(content=content)
        
        # 6. 调用 Vision LLM
        try:
            response = await llm_instance.ainvoke([message])
            result["text"] = response.content
            
            # 尝试获取 token 使用情况
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                result["tokens_used"] = usage.get('total_tokens', 0)
            
            logger.info(
                f"Vision LLM 分析完成: {pdf_path.name} | "
                f"页数={result['pages_analyzed']} | "
                f"Tokens={result['tokens_used']}"
            )
            
        except Exception as e:
            result["error"] = f"Vision LLM 调用失败: {str(e)}"
            logger.error(result["error"])
            return result
        
    except ImportError as e:
        result["error"] = f"依赖库未安装: {str(e)}"
        logger.error(result["error"])
    except Exception as e:
        result["error"] = f"Vision 分析失败: {str(e)}"
        logger.error(result["error"])
    finally:
        result["elapsed_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def analyze_scanned_pdf_with_vision_sync(
    pdf_path: Path,
    llm_instance: Optional[ChatOpenAI] = None,
    max_pages: int = 3,
    dpi: int = 150
) -> Dict[str, Any]:
    """
    使用 Vision LLM 分析扫描 PDF（同步版本）
    
    这是 analyze_scanned_pdf_with_vision 的同步包装器，
    适用于不支持 async/await 的场景。
    """
    import asyncio
    
    # 尝试获取当前事件循环
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果事件循环正在运行，创建新的事件循环
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    analyze_scanned_pdf_with_vision(pdf_path, llm_instance, max_pages, dpi)
                )
                return future.result()
        else:
            # 事件循环未运行，直接运行
            return loop.run_until_complete(
                analyze_scanned_pdf_with_vision(pdf_path, llm_instance, max_pages, dpi)
            )
    except RuntimeError:
        # 没有事件循环，创建新的
        return asyncio.run(
            analyze_scanned_pdf_with_vision(pdf_path, llm_instance, max_pages, dpi)
        )

