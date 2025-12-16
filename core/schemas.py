"""
数据结构定义模块
定义 LLM 处理的输入输出数据结构
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field, field_validator


class FileAnalysis(BaseModel):
    """
    文件分析结果（LLM 输出结构）
    """
    category: str = Field(
        description="文件类别: invoice(发票), contract(合同), paper(论文), image(图片), presentation(演示文稿), default(其他)"
    )
    
    confidence: float = Field(
        ge=0.0, 
        le=1.0,
        description="分类置信度(0-1)"
    )
    
    extracted_date: Optional[str] = Field(
        default=None,
        description="提取的日期(格式: YYYY-MM 或 YYYY-MM-DD)"
    )
    
    extracted_amount: Optional[str] = Field(
        default=None,
        description="提取的金额(例如: 1580元)"
    )
    
    vendor_or_party: Optional[str] = Field(
        default=None,
        description="供应商/对方公司/作者名称"
    )
    
    title: Optional[str] = Field(
        default=None,
        description="文件标题或主题(简短描述)"
    )
    
    suggested_filename: str = Field(
        description="建议的文件名(不含扩展名)"
    )
    
    rationale: str = Field(
        description="分类理由(简短说明)"
    )
    
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="其他提取的元数据(键值对)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "category": "invoice",
                "confidence": 0.95,
                "extracted_date": "2024-03",
                "extracted_amount": "1580元",
                "vendor_or_party": "阿里云",
                "title": "云服务费用",
                "suggested_filename": "[发票]_2024-03_阿里云_云服务费用_1580元",
                "rationale": "文档包含发票关键词、税号、价税合计等信息",
                "metadata": {"tax_id": "91110000123456789X"}
            }
        }


class RenamePlan(BaseModel):
    """
    文件重命名计划（用于文件整理流程）
    """
    category: str = Field(
        description="文件类别: invoice/contract/paper/image/presentation/default"
    )
    
    new_name: str = Field(
        description="新文件名（含扩展名）"
    )
    
    dest_dir: str = Field(
        description="目标目录（相对路径）"
    )
    
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.5,
        description="分类置信度(0-1)"
    )
    
    extracted: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="提取的元数据字典"
    )
    
    rationale: str = Field(
        default="",
        description="分类理由"
    )
    
    # 验证相关字段
    is_valid: bool = Field(
        default=False,
        description="校验状态：True=通过，False=未通过"
    )
    
    validation_msg: str = Field(
        default="",
        description="校验消息（校验失败时的原因）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "category": "invoice",
                "new_name": "[发票]_2024-03_阿里云_1580元.pdf",
                "dest_dir": "archive/发票/2024/03",
                "confidence": 0.95,
                "extracted": {
                    "date_ym": "2024-03",
                    "amount": "1580元",
                    "vendor": "阿里云"
                },
                "rationale": "发票关键词命中(score=9.0)",
                "is_valid": True,
                "validation_msg": ""
            }
        }

