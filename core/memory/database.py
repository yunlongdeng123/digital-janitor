"""
数据库模型和管理器
使用 SQLite + SQLAlchemy 实现
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class ApprovalLog(Base):
    """审批日志表 - 记录每次文件处理的完整决策链"""
    __tablename__ = 'approval_logs'
    
    # 主键和元数据
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 文件标识
    file_hash = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer)
    
    # AI 分析结果
    doc_type = Column(String, index=True)
    vendor = Column(String, index=True)
    extracted_date = Column(String)
    confidence_score = Column(Float)
    
    # 建议 vs 实际
    suggested_filename = Column(String, nullable=False)
    suggested_folder = Column(String, nullable=False)
    final_filename = Column(String, nullable=False)
    final_folder = Column(String, nullable=False)
    
    # 决策追踪
    action = Column(String, nullable=False)  # approved/modified/rejected/skipped
    user_modified_filename = Column(Boolean, default=False)
    user_modified_folder = Column(Boolean, default=False)
    modification_reason = Column(Text)
    
    # 处理信息
    processing_time_ms = Column(Integer)
    extraction_method = Column(String)
    operator = Column(String)
    
    def to_dict(self):
        """转为字典（用于 API 返回）"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'file_hash': self.file_hash,
            'original_filename': self.original_filename,
            'original_path': self.original_path,
            'file_size_bytes': self.file_size_bytes,
            'doc_type': self.doc_type,
            'vendor': self.vendor,
            'extracted_date': self.extracted_date,
            'confidence_score': self.confidence_score,
            'suggested_filename': self.suggested_filename,
            'suggested_folder': self.suggested_folder,
            'final_filename': self.final_filename,
            'final_folder': self.final_folder,
            'action': self.action,
            'user_modified_filename': self.user_modified_filename,
            'user_modified_folder': self.user_modified_folder,
            'modification_reason': self.modification_reason,
            'processing_time_ms': self.processing_time_ms,
            'extraction_method': self.extraction_method,
            'operator': self.operator
        }


class LearnedPreference(Base):
    """学习到的偏好表"""
    __tablename__ = 'learned_preferences'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 偏好类型
    preference_type = Column(String, nullable=False)  # vendor_folder/doctype_partition/naming_template
    
    # 触发条件（独立字段以提高查询效率）
    trigger_vendor = Column(String, index=True)
    trigger_doc_type = Column(String, index=True)
    trigger_conditions = Column(Text, nullable=False)  # JSON 存储完整条件
    
    # 偏好值（相对于 Archive Root 的路径）
    preference_value = Column(Text, nullable=False)
    
    # 置信度和统计
    confidence = Column(Float, default=0.5)
    sample_count = Column(Integer, default=1)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 元数据
    source = Column(String, default='auto_learned')  # auto_learned/user_defined
    enabled = Column(Boolean, default=True)
    
    # 索引
    __table_args__ = (
        Index('idx_preference_lookup', 'preference_type', 'trigger_vendor', 'trigger_doc_type'),
    )
    
    def get_trigger_conditions_dict(self):
        """解析触发条件为字典"""
        try:
            return json.loads(self.trigger_conditions)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def matches(self, context: dict) -> bool:
        """检查给定上下文是否匹配该偏好"""
        conditions = self.get_trigger_conditions_dict()
        return all(
            context.get(key) == value 
            for key, value in conditions.items()
            if value is not None
        )


class PreferenceAuditLog(Base):
    """偏好变更审计表"""
    __tablename__ = 'preference_audit_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    preference_id = Column(Integer, ForeignKey('learned_preferences.id'), nullable=False)
    action = Column(String, nullable=False)  # created/updated/disabled
    old_value = Column(Text)
    new_value = Column(Text)
    old_confidence = Column(Float)
    new_confidence = Column(Float)
    triggered_by_log_id = Column(Integer, ForeignKey('approval_logs.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)


class MemoryDatabase:
    """数据库管理器"""
    
    def __init__(self, db_path: Path = None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认为 ~/.digital_janitor/memory.db
        """
        if db_path is None:
            db_path = Path.home() / '.digital_janitor' / 'memory.db'
        
        # 确保目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建引擎
        self.db_path = db_path
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            echo=False  # 设为 True 可以看到 SQL 语句
        )
        
        # 创建所有表
        Base.metadata.create_all(self.engine)
        
        # 创建会话工厂
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        logger.info(f"Memory database initialized at: {db_path}")
    
    def close(self):
        """关闭数据库连接"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """支持 with 语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句"""
        self.close()
    
    def get_session(self):
        """获取会话（用于外部使用）"""
        return self.session

