"""
应用数据库性能索引
自动检测数据库类型并应用相应的索引优化
"""
import os
import sys
from pathlib import Path
from sqlalchemy import text

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_config import get_db_session, get_db_type
from config import info_print, error_print

def apply_performance_indexes():
    """应用性能优化索引"""
    try:
        info_print("🚀 开始应用数据库性能优化索引...")
        
        db_type = get_db_type()
        info_print(f"📊 数据库类型: {db_type.upper()}")
        
        # 读取索引SQL文件
        sql_file = Path(__file__).parent / "add_performance_indexes.sql"
        
        if not sql_file.exists():
            error_print(f"❌ 索引SQL文件不存在: {sql_file}")
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句（按分号分割，过滤空语句和注释）
        sql_statements = []
        for stmt in sql_content.split(';'):
            stmt = stmt.strip()
            # 跳过注释和空语句
            if stmt and not stmt.startswith('--') and 'CREATE INDEX' in stmt.upper():
                sql_statements.append(stmt)
        
        info_print(f"📝 找到 {len(sql_statements)} 个索引创建语句")
        
        # 执行SQL语句
        success_count = 0
        skip_count = 0
        error_count = 0
        
        with get_db_session() as session:
            for i, sql in enumerate(sql_statements, 1):
                try:
                    # 提取索引名称用于日志
                    index_name = "unknown"
                    if "INDEX" in sql.upper():
                        parts = sql.split()
                        for j, part in enumerate(parts):
                            if part.upper() in ["INDEX", "IF"]:
                                if j + 2 < len(parts):
                                    index_name = parts[j + 2]
                                    break
                    
                    info_print(f"  [{i}/{len(sql_statements)}] 创建索引: {index_name}...")
                    session.execute(text(sql))
                    success_count += 1
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    # 如果索引已存在，不算错误
                    if 'already exists' in error_msg or 'duplicate' in error_msg:
                        info_print(f"  ⏭️  索引已存在，跳过: {index_name}")
                        skip_count += 1
                    else:
                        error_print(f"  ❌ 创建索引失败: {index_name}")
                        error_print(f"     错误: {e}")
                        error_count += 1
        
        info_print("\n" + "="*60)
        info_print("📊 索引应用结果统计:")
        info_print(f"  ✅ 成功创建: {success_count} 个")
        info_print(f"  ⏭️  已存在跳过: {skip_count} 个")
        info_print(f"  ❌ 创建失败: {error_count} 个")
        info_print("="*60)
        
        if error_count == 0:
            info_print("🎉 数据库性能优化索引应用成功！")
            return True
        else:
            error_print("⚠️  部分索引创建失败，请检查错误信息")
            return False
            
    except Exception as e:
        error_print(f"❌ 应用性能索引时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = apply_performance_indexes()
    sys.exit(0 if success else 1)

