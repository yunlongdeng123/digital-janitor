"""
仓库层 - 业务逻辑和数据访问
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc
import json
import logging

from .database import (
    MemoryDatabase, ApprovalLog, LearnedPreference, 
    PreferenceAuditLog
)

logger = logging.getLogger(__name__)


class ApprovalRepository:
    """审批日志仓库"""
    
    def __init__(self, db: MemoryDatabase):
        self.db = db
    
    def save_approval(self, log_data: dict) -> int:
        """
        保存审批记录
        
        参数示例:
        {
            'session_id': 'run_20250101_120000',
            'file_hash': 'abc123...',
            'original_filename': 'invoice.pdf',
            'original_path': '/path/to/inbox/invoice.pdf',
            'file_size_bytes': 102400,
            'doc_type': 'invoice',
            'vendor': 'ABC Corp',
            'extracted_date': '2024-12-15',
            'confidence_score': 0.95,
            'suggested_filename': 'invoice_2024-12-15_ABC_Corp.pdf',
            'suggested_folder': '财务/2024/12',
            'final_filename': 'invoice_2024-12-15_ABC_Corp.pdf',
            'final_folder': '财务/2024/12',
            'action': 'approved',  # approved/modified/rejected/skipped
            'user_modified_filename': False,
            'user_modified_folder': False,
            'modification_reason': None,
            'processing_time_ms': 1500,
            'extraction_method': 'direct',
            'operator': 'user',
        }
        
        返回: 新插入记录的 ID
        """
        try:
            # 创建日志记录
            log = ApprovalLog(**log_data)
            self.db.session.add(log)
            self.db.session.commit()
            
            logger.info(f"Approval saved: {log_data['original_filename']} -> {log_data['action']}")
            
            # 触发偏好学习
            try:
                self._trigger_preference_learning(log)
            except Exception as e:
                logger.error(f"Preference learning failed: {e}")
                # 学习失败不影响主流程
            
            return log.id
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to save approval: {e}")
            raise
    
    def get_recent_approvals(
        self, 
        limit: int = 50,
        doc_type: Optional[str] = None,
        vendor: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        action: Optional[str] = None
    ) -> List[Dict]:
        """
        获取最近的审批记录
        
        支持按 doc_type, vendor, 日期范围, action 筛选
        """
        try:
            query = self.db.session.query(ApprovalLog)
            
            if doc_type:
                query = query.filter(ApprovalLog.doc_type == doc_type)
            if vendor:
                query = query.filter(ApprovalLog.vendor.like(f'%{vendor}%'))
            if date_from:
                query = query.filter(ApprovalLog.created_at >= date_from)
            if date_to:
                query = query.filter(ApprovalLog.created_at <= date_to)
            if action:
                query = query.filter(ApprovalLog.action == action)
            
            results = query.order_by(desc(ApprovalLog.created_at)).limit(limit).all()
            return [log.to_dict() for log in results]
            
        except Exception as e:
            logger.error(f"Failed to get recent approvals: {e}")
            return []
    
    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回:
        {
            'total_approvals': 1234,
            'action_breakdown': {'approved': 800, 'modified': 400, ...},
            'top_vendors': [('ABC Corp', 50), ...],
            'avg_processing_time_ms': 1200,
            'recent_count': 100
        }
        """
        try:
            # 时间范围
            date_from = datetime.utcnow() - timedelta(days=days)
            
            # 总数
            total = self.db.session.query(func.count(ApprovalLog.id)).scalar() or 0
            
            # 最近数量
            recent_count = self.db.session.query(func.count(ApprovalLog.id)) \
                .filter(ApprovalLog.created_at >= date_from).scalar() or 0
            
            # 按 action 统计
            action_stats = self.db.session.query(
                ApprovalLog.action,
                func.count(ApprovalLog.id)
            ).group_by(ApprovalLog.action).all()
            
            # Top vendors (最近 30 天)
            top_vendors = self.db.session.query(
                ApprovalLog.vendor,
                func.count(ApprovalLog.id)
            ).filter(
                and_(
                    ApprovalLog.vendor.isnot(None),
                    ApprovalLog.created_at >= date_from
                )
            ).group_by(ApprovalLog.vendor) \
             .order_by(desc(func.count(ApprovalLog.id))) \
             .limit(10).all()
            
            # 平均处理时间
            avg_time = self.db.session.query(
                func.avg(ApprovalLog.processing_time_ms)
            ).scalar() or 0
            
            return {
                'total_approvals': total,
                'recent_count': recent_count,
                'action_breakdown': dict(action_stats),
                'top_vendors': top_vendors,
                'avg_processing_time_ms': round(avg_time, 0) if avg_time else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'total_approvals': 0,
                'recent_count': 0,
                'action_breakdown': {},
                'top_vendors': [],
                'avg_processing_time_ms': 0
            }
    
    def _trigger_preference_learning(self, log: ApprovalLog):
        """
        从审批记录中学习偏好
        
        学习规则：
        1. 如果用户修改了目录 → 学习 vendor_folder 映射
        2. 如果用户修改了文件名 → 记录（TODO: 命名模式识别）
        """
        pref_repo = PreferenceRepository(self.db)
        
        # 规则 1: Vendor → Folder 映射
        if log.user_modified_folder and log.vendor and log.doc_type:
            try:
                pref_repo.update_preference(
                    preference_type='vendor_folder',
                    trigger_conditions={
                        'vendor': log.vendor,
                        'doc_type': log.doc_type
                    },
                    preference_value=log.final_folder,
                    triggered_by_log_id=log.id
                )
                logger.info(f"Learned preference: {log.vendor} + {log.doc_type} -> {log.final_folder}")
            except Exception as e:
                logger.error(f"Failed to learn vendor_folder preference: {e}")
        
        # 规则 2: Naming Template (TODO: 需要模式识别算法)
        # if log.user_modified_filename:
        #     分析用户命名模式
        #     例如检测是否总是把 "Invoice" 改为 "发票"
        #     pass


class PreferenceRepository:
    """偏好仓库"""
    
    def __init__(self, db: MemoryDatabase):
        self.db = db
    
    def update_preference(
        self,
        preference_type: str,
        trigger_conditions: dict,
        preference_value: str,
        triggered_by_log_id: Optional[int] = None
    ):
        """
        更新或创建偏好
        
        使用增量置信度算法：
        - 新样本与现有偏好一致 → confidence += 0.1 (最高 1.0)
        - 新样本与现有偏好冲突 → confidence -= 0.15，样本多则替换
        """
        try:
            # 准备条件
            conditions_json = json.dumps(trigger_conditions, sort_keys=True, ensure_ascii=False)
            trigger_vendor = trigger_conditions.get('vendor')
            trigger_doc_type = trigger_conditions.get('doc_type')
            
            # 查找现有偏好
            existing = self.db.session.query(LearnedPreference).filter(
                and_(
                    LearnedPreference.preference_type == preference_type,
                    LearnedPreference.trigger_vendor == trigger_vendor,
                    LearnedPreference.trigger_doc_type == trigger_doc_type
                )
            ).first()
            
            if existing:
                # 更新现有偏好
                old_value = existing.preference_value
                old_confidence = existing.confidence
                
                if existing.preference_value == preference_value:
                    # 一致 → 增加置信度
                    existing.confidence = min(1.0, existing.confidence + 0.1)
                    logger.info(f"Preference reinforced: {trigger_vendor} confidence: {old_confidence:.2f} -> {existing.confidence:.2f}")
                else:
                    # 冲突 → 降低置信度
                    existing.confidence = max(0.1, existing.confidence - 0.15)
                    
                    # 如果新样本多次出现，替换旧值
                    if existing.sample_count >= 3:
                        existing.preference_value = preference_value
                        logger.info(f"Preference updated: {trigger_vendor} value changed: {old_value} -> {preference_value}")
                
                existing.sample_count += 1
                existing.last_seen = datetime.utcnow()
                
                # 记录审计日志
                audit = PreferenceAuditLog(
                    preference_id=existing.id,
                    action='updated',
                    old_value=old_value,
                    new_value=existing.preference_value,
                    old_confidence=old_confidence,
                    new_confidence=existing.confidence,
                    triggered_by_log_id=triggered_by_log_id
                )
                self.db.session.add(audit)
            
            else:
                # 创建新偏好
                new_pref = LearnedPreference(
                    preference_type=preference_type,
                    trigger_vendor=trigger_vendor,
                    trigger_doc_type=trigger_doc_type,
                    trigger_conditions=conditions_json,
                    preference_value=preference_value,
                    confidence=0.6,  # 初始置信度
                    sample_count=1
                )
                self.db.session.add(new_pref)
                self.db.session.flush()  # 获取 ID
                
                # 记录审计日志
                audit = PreferenceAuditLog(
                    preference_id=new_pref.id,
                    action='created',
                    new_value=preference_value,
                    new_confidence=0.6,
                    triggered_by_log_id=triggered_by_log_id
                )
                self.db.session.add(audit)
                
                logger.info(f"New preference created: {preference_type} - {trigger_conditions}")
            
            self.db.session.commit()
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to update preference: {e}")
            raise
    
    def get_preference(
        self,
        preference_type: str,
        context: dict,
        min_confidence: float = 0.7
    ) -> Optional[str]:
        """
        获取匹配的偏好值
        
        参数:
        - preference_type: 'vendor_folder' | 'doctype_partition' | 'naming_template'
        - context: {'vendor': 'ABC Corp', 'doc_type': 'invoice'}
        - min_confidence: 最低置信度阈值
        
        返回: 偏好值（如目标文件夹路径）或 None
        """
        try:
            # 基础查询
            query = self.db.session.query(LearnedPreference).filter(
                and_(
                    LearnedPreference.preference_type == preference_type,
                    LearnedPreference.enabled == True,
                    LearnedPreference.confidence >= min_confidence
                )
            )
            
            # 优先查找精确匹配
            vendor = context.get('vendor')
            doc_type = context.get('doc_type')
            
            if vendor and doc_type:
                exact_match = query.filter(
                    and_(
                        LearnedPreference.trigger_vendor == vendor,
                        LearnedPreference.trigger_doc_type == doc_type
                    )
                ).order_by(desc(LearnedPreference.confidence)).first()
                
                if exact_match:
                    logger.info(f"Found exact preference match: {vendor} + {doc_type} -> {exact_match.preference_value}")
                    return exact_match.preference_value
            
            # 如果没有精确匹配，尝试 vendor-only 匹配
            if vendor:
                vendor_match = query.filter(
                    LearnedPreference.trigger_vendor == vendor
                ).order_by(desc(LearnedPreference.confidence)).first()
                
                if vendor_match:
                    logger.info(f"Found vendor preference match: {vendor} -> {vendor_match.preference_value}")
                    return vendor_match.preference_value
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get preference: {e}")
            return None
    
    def list_all_preferences(
        self, 
        preference_type: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[Dict]:
        """
        列出所有偏好（用于 UI 展示和手动编辑）
        """
        try:
            query = self.db.session.query(LearnedPreference)
            
            if preference_type:
                query = query.filter(LearnedPreference.preference_type == preference_type)
            if enabled_only:
                query = query.filter(LearnedPreference.enabled == True)
            
            prefs = query.order_by(desc(LearnedPreference.confidence)).all()
            
            return [
                {
                    'id': p.id,
                    'type': p.preference_type,
                    'vendor': p.trigger_vendor,
                    'doc_type': p.trigger_doc_type,
                    'conditions': p.get_trigger_conditions_dict(),
                    'value': p.preference_value,
                    'confidence': p.confidence,
                    'sample_count': p.sample_count,
                    'last_seen': p.last_seen.isoformat() if p.last_seen else None,
                    'enabled': p.enabled
                }
                for p in prefs
            ]
            
        except Exception as e:
            logger.error(f"Failed to list preferences: {e}")
            return []
    
    def disable_preference(self, preference_id: int):
        """禁用某个偏好"""
        try:
            pref = self.db.session.query(LearnedPreference).filter(
                LearnedPreference.id == preference_id
            ).first()
            
            if pref:
                pref.enabled = False
                
                # 记录审计日志
                audit = PreferenceAuditLog(
                    preference_id=pref.id,
                    action='disabled',
                    old_value=pref.preference_value,
                    new_value=None,
                    old_confidence=pref.confidence,
                    new_confidence=0.0
                )
                self.db.session.add(audit)
                
                self.db.session.commit()
                logger.info(f"Preference disabled: {preference_id}")
                
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to disable preference: {e}")
            raise

