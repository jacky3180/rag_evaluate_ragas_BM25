import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_service import DatabaseService

# 检查 RAGAS 评估结果
print("=== RAGAS 评估结果 ===")
ragas_results = DatabaseService.get_evaluations_by_type('RAGAS')
print(f"RAGAS 评估结果数量: {len(ragas_results)}")

for i, r in enumerate(ragas_results[:5]):
    print(f"ID: {r['id']}, 时间: {r['evaluation_time']}, Precision: {r['context_precision']}, Recall: {r['context_recall']}")

print("\n=== BM25 评估结果 ===")
bm25_results = DatabaseService.get_evaluations_by_type('BM25')
print(f"BM25 评估结果数量: {len(bm25_results)}")

for i, r in enumerate(bm25_results[:5]):
    print(f"ID: {r['id']}, 时间: {r['evaluation_time']}, Precision: {r['context_precision']}, Recall: {r['context_recall']}")