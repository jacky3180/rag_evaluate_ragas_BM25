-- RAG评估系统数据库表结构 (SQLite版本)
-- 数据库文件: rag_evaluate.db

-- 创建评估结果表
CREATE TABLE IF NOT EXISTS evaluation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_type TEXT NOT NULL CHECK(evaluation_type IN ('BM25', 'RAGAS')),
    evaluation_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    
    -- BM25和Ragas共同指标
    context_precision REAL,
    context_recall REAL,
    
    -- BM25额外指标
    f1_score REAL,
    ndcg REAL,
    map_score REAL,
    mrr_score REAL,
    
    -- Ragas独有指标
    faithfulness REAL,
    answer_relevancy REAL,
    context_entity_recall REAL,
    context_relevance REAL,
    answer_correctness REAL,
    answer_similarity REAL,
    
    -- 统计信息
    total_samples INTEGER,
    total_irrelevant_chunks INTEGER,
    total_missed_chunks INTEGER,
    
    -- 详细结果JSON (SQLite原生支持JSON)
    detailed_results TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_evaluation_type ON evaluation_results(evaluation_type);
CREATE INDEX IF NOT EXISTS idx_evaluation_time ON evaluation_results(evaluation_time);
CREATE INDEX IF NOT EXISTS idx_created_at ON evaluation_results(created_at);

-- 创建触发器以实现updated_at自动更新
CREATE TRIGGER IF NOT EXISTS update_evaluation_results_timestamp 
AFTER UPDATE ON evaluation_results
BEGIN
    UPDATE evaluation_results SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 创建评估历史查询视图
CREATE VIEW IF NOT EXISTS evaluation_history AS
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

