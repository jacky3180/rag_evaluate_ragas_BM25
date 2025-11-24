#!/usr/bin/env python3
"""
诊断历史数据查询问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """诊断数据库和历史数据"""
    print("=" * 70)
    print("🔍 历史数据查询诊断")
    print("=" * 70)
    
    # 1. 检查数据库配置
    print("\n📋 步骤1: 检查数据库配置")
    print("-" * 70)
    try:
        from database.db_config import db_config, get_db_type, test_connection
        db_type = get_db_type()
        print(f"✅ 数据库类型: {db_type.upper()}")
        
        if db_type == "sqlite":
            print(f"✅ 数据库文件: {db_config.sqlite_path}")
            db_path = Path(db_config.sqlite_path)
            if db_path.exists():
                file_size = db_path.stat().st_size
                print(f"✅ 文件大小: {file_size / 1024:.2f} KB")
            else:
                print(f"❌ 数据库文件不存在！")
                return False
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False
    
    # 2. 测试连接
    print("\n🔗 步骤2: 测试数据库连接")
    print("-" * 70)
    try:
        if test_connection():
            print("✅ 数据库连接成功")
        else:
            print("❌ 数据库连接失败")
            return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False
    
    # 3. 检查表是否存在
    print("\n📊 步骤3: 检查数据表")
    print("-" * 70)
    try:
        from database.db_config import get_db_session
        from sqlalchemy import text
        
        with get_db_session() as session:
            # 检查evaluation_results表
            if db_type == "sqlite":
                result = session.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='evaluation_results'"
                ))
            else:
                result = session.execute(text(
                    "SHOW TABLES LIKE 'evaluation_results'"
                ))
            
            if result.fetchone():
                print("✅ evaluation_results 表存在")
            else:
                print("❌ evaluation_results 表不存在！需要运行初始化脚本")
                print("   运行: python database/init_database.py")
                return False
    except Exception as e:
        print(f"❌ 表检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 检查数据
    print("\n📈 步骤4: 检查数据记录")
    print("-" * 70)
    try:
        from database.db_service import DatabaseService
        stats = DatabaseService.get_statistics()
        
        print(f"总评估记录: {stats['total_evaluations']}")
        print(f"BM25评估: {stats['bm25_evaluations']}")
        print(f"Ragas评估: {stats['ragas_evaluations']}")
        
        if stats['total_evaluations'] == 0:
            print("\n⚠️ 数据库中没有评估记录！")
            print("   需要先运行评估并保存结果到数据库")
            print("\n💡 快速添加测试数据:")
            print("   运行: python test/test_database_switch.py")
            return False
        else:
            print("✅ 数据库中有评估记录")
    except Exception as e:
        print(f"❌ 数据检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 测试历史数据API
    print("\n🔎 步骤5: 测试历史数据API")
    print("-" * 70)
    try:
        from database.db_service import get_evaluation_history
        
        # 测试BM25 Precision
        bm25_precision = get_evaluation_history('BM25', 'context_precision')
        print(f"BM25 Precision 记录数: {len(bm25_precision)}")
        if len(bm25_precision) > 0:
            print(f"  示例记录: {bm25_precision[0]}")
        
        # 测试BM25 Recall
        bm25_recall = get_evaluation_history('BM25', 'context_recall')
        print(f"BM25 Recall 记录数: {len(bm25_recall)}")
        
        # 测试Ragas Precision
        ragas_precision = get_evaluation_history('RAGAS', 'context_precision')
        print(f"Ragas Precision 记录数: {len(ragas_precision)}")
        
        # 测试Ragas Recall
        ragas_recall = get_evaluation_history('RAGAS', 'context_recall')
        print(f"Ragas Recall 记录数: {len(ragas_recall)}")
        
        if all(len(x) == 0 for x in [bm25_precision, bm25_recall, ragas_precision, ragas_recall]):
            print("\n⚠️ 所有指标都没有数据！")
        else:
            print("\n✅ 历史数据API正常工作")
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. 查看原始数据
    print("\n📝 步骤6: 查看原始数据样本")
    print("-" * 70)
    try:
        from database.db_config import get_db_session
        from sqlalchemy import text
        
        with get_db_session() as session:
            # 查询最近5条记录
            result = session.execute(text(
                "SELECT id, evaluation_type, context_precision, context_recall, created_at "
                "FROM evaluation_results ORDER BY created_at DESC LIMIT 5"
            ))
            
            rows = result.fetchall()
            if rows:
                print("最近5条记录:")
                for row in rows:
                    print(f"  ID:{row[0]} | 类型:{row[1]} | Precision:{row[2]} | Recall:{row[3]} | 时间:{row[4]}")
            else:
                print("❌ 没有找到任何记录")
                
    except Exception as e:
        print(f"❌ 数据查看失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 7. 检查数据格式
    print("\n🔍 步骤7: 检查数据格式")
    print("-" * 70)
    try:
        from database.db_config import get_db_session
        from sqlalchemy import text
        
        with get_db_session() as session:
            # 检查created_at字段格式
            result = session.execute(text(
                "SELECT created_at, typeof(created_at) as type FROM evaluation_results LIMIT 1"
            ))
            
            row = result.fetchone()
            if row:
                print(f"created_at 值: {row[0]}")
                print(f"created_at 类型: {row[1]}")
            
            # 检查数值字段
            result = session.execute(text(
                "SELECT context_precision, context_recall FROM evaluation_results "
                "WHERE context_precision IS NOT NULL LIMIT 1"
            ))
            
            row = result.fetchone()
            if row:
                print(f"context_precision 值: {row[0]} (类型: {type(row[0])})")
                print(f"context_recall 值: {row[1]} (类型: {type(row[1])})")
                
                # 检查数值范围
                if row[0] is not None:
                    if 0 <= row[0] <= 1:
                        print("✅ context_precision 数值范围正常 (0-1)")
                    else:
                        print(f"⚠️ context_precision 数值范围异常: {row[0]}")
                
    except Exception as e:
        print(f"⚠️ 数据格式检查失败: {e}")
    
    print("\n" + "=" * 70)
    print("🎯 诊断完成")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print("\n✅ 诊断成功！如果history.html仍然没有数据，请:")
            print("1. 确保已重启应用服务器 (python app.py)")
            print("2. 清除浏览器缓存后重新加载页面")
            print("3. 检查浏览器控制台是否有JavaScript错误")
            print("4. 确认数据库中有评估记录")
        else:
            print("\n❌ 诊断发现问题，请按照上述提示解决")
        
    except Exception as e:
        print(f"\n❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

