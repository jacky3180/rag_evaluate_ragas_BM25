#!/usr/bin/env python3
"""
数据库切换测试脚本
测试MySQL和SQLite两种数据库的功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试数据
test_bm25_result = {
    'context_precision': 0.85,
    'context_recall': 0.90,
    'f1_score': 0.874,
    'ndcg': 0.88,
    'map_score': 0.82,
    'mrr_score': 0.91,
    'total_samples': 10,
    'total_irrelevant_chunks': 2,
    'total_missed_chunks': 1,
    'detailed_results': {
        'test': 'data',
        'sample_results': [
            {'question': 'test1', 'precision': 0.9},
            {'question': 'test2', 'precision': 0.8}
        ]
    }
}

test_ragas_result = {
    'context_precision': 0.88,
    'context_recall': 0.92,
    'faithfulness': 0.85,
    'answer_relevancy': 0.87,
    'context_entity_recall': 0.90,
    'context_relevance': 0.86,
    'answer_correctness': 0.84,
    'answer_similarity': 0.89,
    'total_samples': 8,
    'total_irrelevant_chunks': 1,
    'total_missed_chunks': 0,
    'detailed_results': {
        'test': 'ragas_data',
        'sample_results': [
            {'question': 'test1', 'faithfulness': 0.9},
            {'question': 'test2', 'faithfulness': 0.8}
        ]
    }
}

def test_database_operations():
    """测试数据库基本操作"""
    from database.db_config import test_connection, create_tables, get_db_type
    from database.db_service import DatabaseService, get_evaluation_history, get_evaluation_stats
    
    print("=" * 60)
    print("🧪 数据库功能测试")
    print("=" * 60)
    
    # 1. 显示当前数据库类型
    db_type = get_db_type()
    print(f"\n📋 当前数据库类型: {db_type.upper()}")
    
    # 2. 测试连接
    print("\n🔗 测试数据库连接...")
    if not test_connection():
        print("❌ 数据库连接失败！")
        return False
    print("✅ 数据库连接成功！")
    
    # 3. 创建表（如果不存在）
    print("\n📊 确保数据库表存在...")
    create_tables()
    print("✅ 数据库表检查完成！")
    
    # 4. 测试保存BM25结果
    print("\n💾 测试保存BM25评估结果...")
    bm25_id = DatabaseService.save_bm25_result(test_bm25_result, "测试BM25评估")
    if bm25_id:
        print(f"✅ BM25结果保存成功！ID: {bm25_id}")
    else:
        print("❌ BM25结果保存失败！")
        return False
    
    # 5. 测试保存Ragas结果
    print("\n💾 测试保存Ragas评估结果...")
    ragas_id = DatabaseService.save_ragas_result(test_ragas_result, "测试Ragas评估")
    if ragas_id:
        print(f"✅ Ragas结果保存成功！ID: {ragas_id}")
    else:
        print("❌ Ragas结果保存失败！")
        return False
    
    # 6. 测试查询统计信息
    print("\n📊 测试查询统计信息...")
    stats = DatabaseService.get_statistics()
    print("✅ 统计信息查询成功！")
    print(f"   总评估次数: {stats['total_evaluations']}")
    print(f"   BM25评估: {stats['bm25_evaluations']}")
    print(f"   Ragas评估: {stats['ragas_evaluations']}")
    
    # 7. 测试查询历史记录
    print("\n📜 测试查询评估历史...")
    history = DatabaseService.get_evaluation_history(limit=5)
    print(f"✅ 历史记录查询成功！共 {len(history)} 条记录")
    
    # 8. 测试根据ID查询
    print("\n🔍 测试根据ID查询...")
    result = DatabaseService.get_evaluation_by_id(bm25_id)
    if result:
        print(f"✅ ID查询成功！类型: {result['evaluation_type']}")
    else:
        print("❌ ID查询失败！")
        return False
    
    # 9. 测试根据类型查询
    print("\n🔍 测试根据类型查询...")
    bm25_results = DatabaseService.get_evaluations_by_type('BM25', limit=5)
    ragas_results = DatabaseService.get_evaluations_by_type('RAGAS', limit=5)
    print(f"✅ 类型查询成功！BM25: {len(bm25_results)} 条, Ragas: {len(ragas_results)} 条")
    
    # 10. 测试历史数据API（用于图表）
    print("\n📈 测试历史数据API...")
    try:
        bm25_precision_history = get_evaluation_history('BM25', 'context_precision')
        ragas_recall_history = get_evaluation_history('RAGAS', 'context_recall')
        print(f"✅ 历史数据API成功！")
        print(f"   BM25 Precision: {len(bm25_precision_history)} 条")
        print(f"   Ragas Recall: {len(ragas_recall_history)} 条")
    except Exception as e:
        print(f"❌ 历史数据API失败: {e}")
        return False
    
    # 11. 测试统计概览API
    print("\n📊 测试统计概览API...")
    try:
        eval_stats = get_evaluation_stats()
        print(f"✅ 统计概览API成功！")
        print(f"   总评估: {eval_stats['total_evaluations']}")
        print(f"   平均准确率: {eval_stats['avg_precision']:.2%}")
        print(f"   平均召回率: {eval_stats['avg_recall']:.2%}")
    except Exception as e:
        print(f"❌ 统计概览API失败: {e}")
        return False
    
    # 12. 测试删除功能（可选，取消注释以测试）
    # print("\n🗑️ 测试删除功能...")
    # if DatabaseService.delete_evaluation(bm25_id):
    #     print(f"✅ 删除成功！ID: {bm25_id}")
    # else:
    #     print("❌ 删除失败！")
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)
    
    return True

def main():
    """主函数"""
    try:
        success = test_database_operations()
        if success:
            print("\n✅ 数据库功能正常！")
            print("\n💡 提示:")
            print("1. 可以通过修改 .env 文件中的 DB_TYPE 来切换数据库")
            print("2. 支持的数据库类型: sqlite, mysql")
            print("3. 切换后需要重新运行 database/init_database.py")
            return 0
        else:
            print("\n❌ 测试失败！请检查数据库配置")
            return 1
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

