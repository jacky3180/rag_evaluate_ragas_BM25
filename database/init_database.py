#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建数据库表和测试连接
支持MySQL和SQLite两种数据库
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_config import test_connection, create_tables, db_config, get_db_type
from database.db_service import DatabaseService

def main():
    """主函数"""
    print("开始初始化RAG评估系统数据库...")
    print("=" * 50)
    
    # 显示数据库配置
    db_type = get_db_type()
    print("数据库配置:")
    print(f"   数据库类型: {db_type.upper()}")
    
    if db_type == "mysql":
        print(f"   主机: {db_config.host}")
        print(f"   端口: {db_config.port}")
        print(f"   用户: {db_config.user}")
        print(f"   数据库: {db_config.database}")
    elif db_type == "sqlite":
        print(f"   数据库文件: {db_config.sqlite_path}")
        # 确保SQLite数据库目录存在
        db_path = Path(db_config.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"   数据库路径已创建: {db_path.parent}")
    print()
    
    # 测试数据库连接
    print("测试数据库连接...")
    if test_connection():
        print("数据库连接成功！")
    else:
        print("数据库连接失败！")
        if db_type == "mysql":
            print("请检查:")
            print("1. MySQL服务是否启动")
            print("2. 数据库配置是否正确")
            print("3. 用户权限是否足够")
        elif db_type == "sqlite":
            print("请检查:")
            print("1. SQLite数据库文件路径是否正确")
            print("2. 是否有文件读写权限")
        return False
    
    # 创建数据库表
    print(f"\n创建{db_type.upper()}数据库表...")
    if create_tables():
        print(f"{db_type.upper()}数据库表创建成功！")
    else:
        print(f"{db_type.upper()}数据库表创建失败！")
        return False
    
    # 测试数据库服务
    print("\n测试数据库服务...")
    try:
        stats = DatabaseService.get_statistics()
        print("数据库服务测试成功！")
        print(f"   当前记录数: {stats['total_evaluations']}")
        print(f"   BM25评估: {stats['bm25_evaluations']}")
        print(f"   Ragas评估: {stats['ragas_evaluations']}")
    except Exception as e:
        print(f"数据库服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("数据库初始化完成！")
    print("\n使用说明:")
    print("1. 启动Web应用: python app.py")
    print("2. 访问: http://localhost:8000")
    print("3. 运行评估后可以保存结果到数据库")
    
    if db_type == "sqlite":
        print(f"\n提示: SQLite数据库文件位于: {db_config.sqlite_path}")
        print("   可以使用SQLite工具(如DB Browser for SQLite)查看数据")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
