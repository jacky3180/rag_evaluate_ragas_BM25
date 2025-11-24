-- ===================================================================
-- RAG评估系统数据库性能优化 - 索引创建脚本
-- 用途：提升查询性能，减少响应时间
-- 兼容：MySQL和SQLite
-- ===================================================================

-- BM25评估表索引
-- 优化：按评估类型查询
CREATE INDEX IF NOT EXISTS idx_bm25_evaluation_time 
ON bm25_evaluations(evaluation_time DESC);

-- 优化：按创建时间排序查询
CREATE INDEX IF NOT EXISTS idx_bm25_created_at 
ON bm25_evaluations(created_at DESC);

-- 优化：按日期范围查询
CREATE INDEX IF NOT EXISTS idx_bm25_eval_time_created 
ON bm25_evaluations(evaluation_time, created_at);

-- RAGAS评估表索引
-- 优化：按评估类型查询
CREATE INDEX IF NOT EXISTS idx_ragas_evaluation_time 
ON ragas_evaluations(evaluation_time DESC);

-- 优化：按创建时间排序查询
CREATE INDEX IF NOT EXISTS idx_ragas_created_at 
ON ragas_evaluations(created_at DESC);

-- 优化：按日期范围查询
CREATE INDEX IF NOT EXISTS idx_ragas_eval_time_created 
ON ragas_evaluations(evaluation_time, created_at);

-- 统一评估结果表索引（如果使用）
CREATE INDEX IF NOT EXISTS idx_eval_results_type_time 
ON evaluation_results(evaluation_type, evaluation_time DESC);

CREATE INDEX IF NOT EXISTS idx_eval_results_created_at 
ON evaluation_results(created_at DESC);

-- 复合索引优化时间范围查询
CREATE INDEX IF NOT EXISTS idx_eval_results_type_created 
ON evaluation_results(evaluation_type, created_at DESC);

