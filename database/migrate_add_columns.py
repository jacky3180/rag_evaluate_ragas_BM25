#!/usr/bin/env python3
"""
数据库迁移脚本：为新字段添加列
用于更新现有的evaluation_results表结构
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def migrate_sqlite():
    """迁移SQLite数据库"""
    try:
        from database.db_config import get_db_session, get_db_type
        from sqlalchemy import text
        
        if get_db_type() != "sqlite":
            print("⚠️ 当前不是SQLite数据库，跳过迁移")
            return True
        
        print("🔄 开始迁移SQLite数据库...")
        
        with get_db_session() as session:
            # 检查表结构
            result = session.execute(text("PRAGMA table_info(evaluation_results)"))
            columns = [row[1] for row in result.fetchall()]
            print(f"当前列: {columns}")
            
            # 需要添加的新列
            new_columns = [
                ('f1_score', 'REAL'),
                ('ndcg', 'REAL'),
                ('map_score', 'REAL'),
                ('mrr_score', 'REAL')
            ]
            
            added_columns = []
            for col_name, col_type in new_columns:
                if col_name not in columns:
                    try:
                        sql = f"ALTER TABLE evaluation_results ADD COLUMN {col_name} {col_type}"
                        session.execute(text(sql))
                        added_columns.append(col_name)
                        print(f"✅ 添加列: {col_name}")
                    except Exception as e:
                        print(f"⚠️ 添加列 {col_name} 失败: {e}")
                else:
                    print(f"ℹ️ 列 {col_name} 已存在，跳过")
            
            if added_columns:
                print(f"\n🎉 成功添加 {len(added_columns)} 个新列: {added_columns}")
            else:
                print("\n✅ 所有列都已存在，无需迁移")
                
        return True
        
    except Exception as e:
        print(f"❌ SQLite迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def migrate_mysql():
    """迁移MySQL数据库"""
    try:
        from database.db_config import get_db_session, get_db_type
        from sqlalchemy import text
        
        if get_db_type() != "mysql":
            print("⚠️ 当前不是MySQL数据库，跳过迁移")
            return True
        
        print("🔄 开始迁移MySQL数据库...")
        
        with get_db_session() as session:
            # 检查表结构
            result = session.execute(text("DESCRIBE evaluation_results"))
            columns = [row[0] for row in result.fetchall()]
            print(f"当前列: {columns}")
            
            # 需要添加的新列
            new_columns = [
                ('f1_score', 'DECIMAL(10, 4) COMMENT "F1 Score"'),
                ('ndcg', 'DECIMAL(10, 4) COMMENT "NDCG"'),
                ('map_score', 'DECIMAL(10, 4) COMMENT "MAP Score"'),
                ('mrr_score', 'DECIMAL(10, 4) COMMENT "MRR Score"')
            ]
            
            added_columns = []
            for col_name, col_def in new_columns:
                if col_name not in columns:
                    try:
                        sql = f"ALTER TABLE evaluation_results ADD COLUMN {col_name} {col_def}"
                        session.execute(text(sql))
                        added_columns.append(col_name)
                        print(f"✅ 添加列: {col_name}")
                    except Exception as e:
                        print(f"⚠️ 添加列 {col_name} 失败: {e}")
                else:
                    print(f"ℹ️ 列 {col_name} 已存在，跳过")
            
            if added_columns:
                print(f"\n🎉 成功添加 {len(added_columns)} 个新列: {added_columns}")
            else:
                print("\n✅ 所有列都已存在，无需迁移")
                
        return True
        
    except Exception as e:
        print(f"❌ MySQL迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔄 数据库迁移：添加新字段")
    print("=" * 60)
    
    try:
        from database.db_config import get_db_type, test_connection
        
        # 测试连接
        if not test_connection():
            print("❌ 数据库连接失败！")
            return False
        
        db_type = get_db_type()
        print(f"\n📋 数据库类型: {db_type.upper()}")
        
        # 执行迁移
        if db_type == "sqlite":
            success = migrate_sqlite()
        elif db_type == "mysql":
            success = migrate_mysql()
        else:
            print(f"❌ 不支持的数据库类型: {db_type}")
            return False
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 数据库迁移完成！")
            print("=" * 60)
            print("\n💡 下一步:")
            print("1. 重启应用服务器")
            print("2. 访问 http://localhost:8000/static/history.html")
            print("3. 测试历史数据查询功能")
            
            # 测试新字段
            print("\n🧪 测试新字段...")
            try:
                from database.db_service import get_evaluation_history
                
                # 测试各个新字段
                test_fields = [
                    ('BM25', 'f1_score'),
                    ('BM25', 'ndcg'),
                    ('BM25', 'map_score'),
                    ('BM25', 'mrr_score')
                ]
                
                for eval_type, field in test_fields:
                    try:
                        data = get_evaluation_history(eval_type, field)
                        print(f"✅ {eval_type} {field}: {len(data)} 条记录")
                    except Exception as e:
                        print(f"⚠️ {eval_type} {field}: {e}")
                        
            except Exception as e:
                print(f"⚠️ 字段测试失败: {e}")
            
        return success
        
    except Exception as e:
        print(f"\n❌ 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
