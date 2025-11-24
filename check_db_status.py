import sqlite3
import os
from database.db_config import db_config

# 检查数据库文件
db_path = db_config.sqlite_path
print(f"数据库配置路径: {db_path}")
print(f"数据库文件存在: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查看所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("\n数据库中的表:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 检查评估结果表
    if any(table[0] == 'evaluation_results' for table in tables):
        cursor.execute("SELECT COUNT(*) FROM evaluation_results")
        count = cursor.fetchone()[0]
        print(f"\n评估结果表中的记录数: {count}")
        
        if count > 0:
            cursor.execute("SELECT id, evaluation_type, created_at, context_precision, context_recall FROM evaluation_results")
            records = cursor.fetchall()
            print("\n评估记录详情:")
            for record in records:
                print(f"  ID: {record[0]}, 类型: {record[1]}, 时间: {record[2]}, Precision: {record[3]}, Recall: {record[4]}")
    else:
        print("\n未找到 evaluation_results 表")
    
    conn.close()
else:
    print("\n数据库文件不存在")