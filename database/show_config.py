#!/usr/bin/env python3
"""
显示当前数据库配置信息
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """显示数据库配置"""
    from database.db_config import db_config, get_db_type
    
    print("=" * 60)
    print("📋 当前数据库配置")
    print("=" * 60)
    
    db_type = get_db_type()
    print(f"\n数据库类型: {db_type.upper()}")
    print("-" * 60)
    
    if db_type == "sqlite":
        print(f"数据库文件路径: {db_config.sqlite_path}")
        db_path = Path(db_config.sqlite_path)
        if db_path.exists():
            file_size = db_path.stat().st_size
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.2f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.2f} MB"
            print(f"数据库文件大小: {size_str}")
            print(f"文件状态: ✅ 存在")
        else:
            print(f"文件状态: ⚠️ 不存在（将在初始化时创建）")
        print(f"\n连接字符串: {db_config.connection_string}")
        
    elif db_type == "mysql":
        print(f"主机地址: {db_config.host}")
        print(f"端口: {db_config.port}")
        print(f"用户名: {db_config.user}")
        print(f"数据库名: {db_config.database}")
        print(f"字符集: {db_config.charset}")
        print(f"\n连接字符串: mysql+pymysql://{db_config.user}:****@{db_config.host}:{db_config.port}/{db_config.database}")
    
    print("\n" + "=" * 60)
    print("🔧 测试数据库连接...")
    print("=" * 60)
    
    try:
        from database.db_config import test_connection
        if test_connection():
            print("✅ 数据库连接成功！")
            
            # 显示表统计信息
            try:
                from database.db_service import DatabaseService
                stats = DatabaseService.get_statistics()
                print("\n📊 数据库统计:")
                print(f"   总评估次数: {stats['total_evaluations']}")
                print(f"   BM25评估: {stats['bm25_evaluations']}")
                print(f"   Ragas评估: {stats['ragas_evaluations']}")
                if stats['latest_evaluation_time']:
                    print(f"   最新评估: {stats['latest_evaluation_time']}")
            except Exception as e:
                print(f"\n⚠️ 无法获取统计信息: {e}")
                print("   提示: 可能需要先运行 python database/init_database.py")
        else:
            print("❌ 数据库连接失败！")
            print("\n💡 解决方案:")
            if db_type == "sqlite":
                print("   1. 检查数据库文件路径是否有写入权限")
                print("   2. 运行: python database/init_database.py")
            else:
                print("   1. 检查MySQL服务是否运行")
                print("   2. 检查.env配置是否正确")
                print("   3. 检查用户名和密码")
                print("   4. 确保数据库已创建")
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📝 配置说明")
    print("=" * 60)
    print("\n要修改数据库配置:")
    print("1. 编辑项目根目录的 .env 文件")
    print("2. 修改 DB_TYPE 参数 (sqlite 或 mysql)")
    print("3. 配置相应的数据库连接参数")
    print("4. 运行: python database/init_database.py")
    print("5. 重启应用")
    
    print("\n📚 更多信息:")
    print("   - 快速开始: QUICKSTART_DATABASE.md")
    print("   - 详细文档: database/README_DATABASE.md")
    print("   - 更改总结: DATABASE_CHANGES_SUMMARY.md")
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

