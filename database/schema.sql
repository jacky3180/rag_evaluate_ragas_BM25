-- RAG评估系统数据库表结构
-- 数据库名: rag_evaluate

USE rag_evaluate;

-- 创建评估结果表
CREATE TABLE IF NOT EXISTS evaluation_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evaluation_type ENUM('BM25', 'RAGAS') NOT NULL COMMENT '评估类型',
    evaluation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '评估时间',
    description TEXT COMMENT '评估描述',
    
    -- BM25和Ragas共同指标
    context_precision DECIMAL(10, 4) COMMENT 'Context Precision',
    context_recall DECIMAL(10, 4) COMMENT 'Context Recall',
    
    -- BM25额外指标
    f1_score DECIMAL(10, 4) COMMENT 'F1 Score',
    ndcg DECIMAL(10, 4) COMMENT 'NDCG',
    map_score DECIMAL(10, 4) COMMENT 'MAP Score',
    mrr_score DECIMAL(10, 4) COMMENT 'MRR Score',
    
    -- Ragas独有指标
    faithfulness DECIMAL(10, 4) COMMENT 'Faithfulness',
    answer_relevancy DECIMAL(10, 4) COMMENT 'Answer Relevancy',
    context_entity_recall DECIMAL(10, 4) COMMENT 'Context Entity Recall',
    context_relevance DECIMAL(10, 4) COMMENT 'Context Relevance',
    answer_correctness DECIMAL(10, 4) COMMENT 'Answer Correctness',
    answer_similarity DECIMAL(10, 4) COMMENT 'Answer Similarity',
    
    -- 统计信息
    total_samples INT COMMENT '总样本数',
    total_irrelevant_chunks INT COMMENT '总不相关分块数',
    total_missed_chunks INT COMMENT '总未召回分块数',
    
    -- 详细结果JSON
    detailed_results JSON COMMENT '详细评估结果',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_evaluation_type (evaluation_type),
    INDEX idx_evaluation_time (evaluation_time),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评估结果表';

-- 创建评估历史查询视图
CREATE OR REPLACE VIEW evaluation_history AS
SELECT 
    id,
    evaluation_type,
    evaluation_time,
    description,
    context_precision,
    context_recall,
    f1_score,
    ndcg,
    map_score,
    mrr_score,
    faithfulness,
    answer_relevancy,
    context_entity_recall,
    context_relevance,
    answer_correctness,
    answer_similarity,
    total_samples,
    total_irrelevant_chunks,
    total_missed_chunks,
    created_at
FROM evaluation_results
ORDER BY evaluation_time DESC;
