"""
BM25评估表迁移脚本
为bm25_evaluations表添加F1-Score、MRR、MAP、NDCG四个指标列
"""

import pymysql
from datetime import datetime
from typing import Dict, Any, Optional

class DatabaseConfig:
    """数据库配置"""
    def __init__(self):
        self.host = 'localhost'
        self.port = 3306
        self.user = 'root'
        self.password = 'root'
        self.database = 'rag_evaluate'
        self.charset = 'utf8mb4'

def migrate_bm25_table():
    """迁移BM25表，添加新指标列"""
    config = DatabaseConfig()
    connection = None
    
    try:
        # 连接数据库
        connection = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            charset=config.charset,
            autocommit=True
        )
        
        cursor = connection.cursor()
        
        print("🚀 开始BM25表迁移...")
        
        # 检查表是否存在
        cursor.execute("SHOW TABLES LIKE 'bm25_evaluations'")
        if not cursor.fetchone():
            print("❌ bm25_evaluations表不存在，请先运行数据库初始化")
            return False
        
        # 检查列是否已存在
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'bm25_evaluations' AND COLUMN_NAME IN ('f1_score', 'mrr', 'map', 'ndcg')
        """, (config.database,))
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"📊 已存在的列: {existing_columns}")
        
        # 添加缺失的列
        columns_to_add = []
        
        if 'f1_score' not in existing_columns:
            columns_to_add.append("ADD COLUMN f1_score DECIMAL(10, 6) DEFAULT NULL COMMENT 'F1-Score'")
        
        if 'mrr' not in existing_columns:
            columns_to_add.append("ADD COLUMN mrr DECIMAL(10, 6) DEFAULT NULL COMMENT 'MRR'")
        
        if 'map' not in existing_columns:
            columns_to_add.append("ADD COLUMN map DECIMAL(10, 6) DEFAULT NULL COMMENT 'MAP'")
        
        if 'ndcg' not in existing_columns:
            columns_to_add.append("ADD COLUMN ndcg DECIMAL(10, 6) DEFAULT NULL COMMENT 'NDCG'")
        
        if columns_to_add:
            # 执行ALTER TABLE语句
            alter_sql = f"ALTER TABLE bm25_evaluations {', '.join(columns_to_add)}"
            print(f"🔧 执行SQL: {alter_sql}")
            
            cursor.execute(alter_sql)
            print("✅ 成功添加新列")
        else:
            print("✅ 所有列已存在，无需迁移")
        
        # 验证表结构
        cursor.execute("DESCRIBE bm25_evaluations")
        columns = cursor.fetchall()
        
        print("\n📋 当前表结构:")
        for column in columns:
            print(f"   - {column[0]}: {column[1]} {column[2] if column[2] else ''}")
        
        print("\n🎉 BM25表迁移完成！")
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def main():
    """主函数"""
    print("=" * 60)
    print("🔄 BM25评估表迁移工具")
    print("=" * 60)
    
    success = migrate_bm25_table()
    
    if success:
        print("\n✅ 迁移成功完成！")
        print("现在可以保存包含F1-Score、MRR、MAP、NDCG的BM25评估结果了。")
    else:
        print("\n❌ 迁移失败，请检查错误信息。")

if __name__ == "__main__":
    main()
