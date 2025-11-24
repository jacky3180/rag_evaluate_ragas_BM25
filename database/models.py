"""
数据库模型定义
兼容MySQL和SQLite两种数据库
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.sql import func
from database.db_config import Base, get_db_type

# 根据数据库类型选择合适的数据类型
def get_numeric_type():
    """获取数值类型（MySQL使用DECIMAL，SQLite使用Float）"""
    return Float  # 统一使用Float，兼容性更好

class EvaluationResult(Base):
    """评估结果模型"""
    __tablename__ = "evaluation_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 使用String代替Enum以兼容SQLite
    evaluation_type = Column(String(10), nullable=False, comment='评估类型')
    evaluation_time = Column(DateTime, server_default=func.now(), comment='评估时间')
    description = Column(Text, comment='评估描述')
    
    # BM25和Ragas共同指标
    context_precision = Column(get_numeric_type(), comment='Context Precision')
    context_recall = Column(get_numeric_type(), comment='Context Recall')
    
    # BM25额外指标
    f1_score = Column(get_numeric_type(), comment='F1 Score')
    ndcg = Column(get_numeric_type(), comment='NDCG')
    map_score = Column(get_numeric_type(), comment='MAP Score')
    mrr_score = Column(get_numeric_type(), comment='MRR Score')
    
    # Ragas独有指标
    faithfulness = Column(get_numeric_type(), comment='Faithfulness')
    answer_relevancy = Column(get_numeric_type(), comment='Answer Relevancy')
    context_entity_recall = Column(get_numeric_type(), comment='Context Entity Recall')
    context_relevance = Column(get_numeric_type(), comment='Context Relevance')
    answer_correctness = Column(get_numeric_type(), comment='Answer Correctness')
    answer_similarity = Column(get_numeric_type(), comment='Answer Similarity')
    
    # 统计信息
    total_samples = Column(Integer, comment='总样本数')
    total_irrelevant_chunks = Column(Integer, comment='总不相关分块数')
    total_missed_chunks = Column(Integer, comment='总未召回分块数')
    
    # 详细结果JSON（SQLite会将JSON存储为TEXT）
    detailed_results = Column(JSON, comment='详细评估结果')
    
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'evaluation_type': self.evaluation_type,
            'evaluation_time': self.evaluation_time.isoformat() if self.evaluation_time else None,
            'description': self.description,
            'context_precision': float(self.context_precision) if self.context_precision is not None else None,
            'context_recall': float(self.context_recall) if self.context_recall is not None else None,
            'f1_score': float(self.f1_score) if self.f1_score is not None else None,
            'ndcg': float(self.ndcg) if self.ndcg is not None else None,
            'map_score': float(self.map_score) if self.map_score is not None else None,
            'mrr_score': float(self.mrr_score) if self.mrr_score is not None else None,
            'faithfulness': float(self.faithfulness) if self.faithfulness is not None else None,
            'answer_relevancy': float(self.answer_relevancy) if self.answer_relevancy is not None else None,
            'context_entity_recall': float(self.context_entity_recall) if self.context_entity_recall is not None else None,
            'context_relevance': float(self.context_relevance) if self.context_relevance is not None else None,
            'answer_correctness': float(self.answer_correctness) if self.answer_correctness is not None else None,
            'answer_similarity': float(self.answer_similarity) if self.answer_similarity is not None else None,
            'total_samples': self.total_samples,
            'total_irrelevant_chunks': self.total_irrelevant_chunks,
            'total_missed_chunks': self.total_missed_chunks,
            'detailed_results': self.detailed_results,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_bm25_results(cls, results: dict, description: str = ""):
        """从BM25评估结果创建记录"""
        return cls(
            evaluation_type='BM25',
            description=description,
            context_precision=results.get('context_precision'),
            context_recall=results.get('context_recall'),
            f1_score=results.get('f1_score'),
            ndcg=results.get('ndcg'),
            map_score=results.get('map_score'),
            mrr_score=results.get('mrr_score'),
            total_samples=results.get('total_samples'),
            total_irrelevant_chunks=results.get('total_irrelevant_chunks'),
            total_missed_chunks=results.get('total_missed_chunks'),
            detailed_results=results.get('detailed_results')
        )
    
    @classmethod
    def from_ragas_results(cls, results: dict, description: str = ""):
        """从Ragas评估结果创建记录"""
        return cls(
            evaluation_type='RAGAS',
            description=description,
            context_precision=results.get('context_precision'),
            context_recall=results.get('context_recall'),
            faithfulness=results.get('faithfulness'),
            answer_relevancy=results.get('answer_relevancy'),
            context_entity_recall=results.get('context_entity_recall'),
            context_relevance=results.get('context_relevance'),
            answer_correctness=results.get('answer_correctness'),
            answer_similarity=results.get('answer_similarity'),
            total_samples=results.get('total_samples'),
            total_irrelevant_chunks=results.get('total_irrelevant_chunks'),
            total_missed_chunks=results.get('total_missed_chunks'),
            detailed_results=results.get('detailed_results')
        )
