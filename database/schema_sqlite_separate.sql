-- RAG评估系统数据库表结构 (SQLite版本 - 独立表)
-- 数据库文件: rag_evaluate.db

-- 创建BM25评估结果表
CREATE TABLE IF NOT EXISTS bm25_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_time DATETIME NOT NULL,
    description TEXT,
    context_precision REAL,
    context_recall REAL,
    f1_score REAL,
    mrr REAL,
    map REAL,
    ndcg REAL,
    total_samples INTEGER,
    irrelevant_chunks_count INTEGER,
    missed_chunks_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建RAGAS评估结果表
CREATE TABLE IF NOT EXISTS ragas_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_time DATETIME NOT NULL,
    description TEXT,
    context_precision REAL,
    context_recall REAL,
    faithfulness REAL,
    answer_relevancy REAL,
    context_entity_recall REAL,
    context_relevance REAL,
    answer_correctness REAL,
    answer_similarity REAL,
    total_samples INTEGER,
    irrelevant_chunks_count INTEGER,
    missed_chunks_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_bm25_evaluation_time ON bm25_evaluations(evaluation_time);
CREATE INDEX IF NOT EXISTS idx_bm25_created_at ON bm25_evaluations(created_at);
CREATE INDEX IF NOT EXISTS idx_ragas_evaluation_time ON ragas_evaluations(evaluation_time);
CREATE INDEX IF NOT EXISTS idx_ragas_created_at ON ragas_evaluations(created_at);

