#!/usr/bin/env python3
"""
快速修复数据库脚本
删除旧的SQLite数据库并重新创建包含所有字段的新数据库
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    print("=" * 60)
    print("快速修复数据库")
    print("=" * 60)
    
    try:
        from database.db_config import db_config, get_db_type
        
        db_type = get_db_type()
        print(f"\n当前数据库类型: {db_type.upper()}")
        
        if db_type != "sqlite":
            print("当前不是SQLite数据库，无需修复")
            return True
        
        # 检查数据库文件是否存在
        db_path = Path(db_config.sqlite_path)
        if db_path.exists():
            print(f"\n删除旧数据库文件: {db_path}")
            db_path.unlink()  # 删除文件
            print("旧数据库文件已删除")
        else:
            print(f"\n数据库文件不存在: {db_path}")
        
        print(f"\n重新创建数据库...")
        
        # 重新初始化数据库
        from database.init_database import main as init_main
        success = init_main()
        
        if success:
            print(f"\n数据库重新创建成功！")
            
            # 添加测试数据
            print(f"\n添加测试数据...")
            try:
                from test.test_database_switch import test_database_operations
                test_success = test_database_operations()
                if test_success:
                    print("测试数据添加成功！")
                else:
                    print("测试数据添加失败，但数据库结构正确")
            except Exception as e:
                print(f"测试数据添加失败: {e}")
            
            print(f"\n" + "=" * 60)
            print("数据库修复完成！")
            print("=" * 60)
            print(f"\n下一步:")
            print(f"1. 重启应用: python app.py")
            print(f"2. 访问: http://localhost:8000/static/history.html")
            print(f"3. 测试历史数据查询功能")
            
            return True
        else:
            print(f"\n数据库创建失败！")
            return False
            
    except Exception as e:
        print(f"\n修复过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
