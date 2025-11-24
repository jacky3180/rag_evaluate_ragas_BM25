"""
数据库配置模块
支持MySQL和SQLite两种数据库
"""
import os
from typing import Optional
from pydantic import BaseModel
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from pathlib import Path

# 加载.env文件
try:
    import dotenv
    dotenv.load_dotenv()
    print("✅ .env 文件加载成功")
except ImportError:
    print("⚠️  python-dotenv 未安装，无法加载 .env 文件")

class DatabaseConfig(BaseModel):
    """数据库配置类"""
    db_type: str = "sqlite"  # mysql 或 sqlite
    # MySQL配置
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "root"
    database: str = "rag_evaluate"
    charset: str = "utf8mb4"
    # SQLite配置
    sqlite_path: str = "database/rag_evaluate.db"
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """从环境变量创建配置"""
        config = cls(
            db_type=os.getenv("DB_TYPE", "sqlite").lower(),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "root"),
            database=os.getenv("DB_NAME", "rag_evaluate"),
            charset=os.getenv("DB_CHARSET", "utf8mb4"),
            sqlite_path=os.getenv("SQLITE_DB_PATH", "database/rag_evaluate.db")
        )
        print(f"🔧 数据库配置: 类型={config.db_type}, 主机={config.host}, 端口={config.port}, 数据库={config.database}")
        return config
    
    @property
    def connection_string(self) -> str:
        """获取数据库连接字符串"""
        if self.db_type == "sqlite":
            # 确保SQLite数据库目录存在
            db_path = Path(self.sqlite_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{self.sqlite_path}"
        elif self.db_type == "mysql":
            return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")

# 全局数据库配置
db_config = DatabaseConfig.from_env()

# SQLAlchemy配置
engine_kwargs: dict = {
    "echo": False,  # 设置为True可以看到SQL语句
}

# 根据数据库类型添加特定配置
if db_config.db_type == "mysql":
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 3600
    })
elif db_config.db_type == "sqlite":
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False}  # SQLite特定配置
    })

engine = create_engine(db_config.connection_string, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db_session():
    """获取数据库会话的上下文管理器"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def test_connection() -> bool:
    """测试数据库连接"""
    try:
        with get_db_session() as session:
            result = session.execute(text("SELECT 1"))
            row = result.fetchone()
            if row is not None:
                return row[0] == 1
            return False
    except Exception as e:
        print(f"数据库连接测试失败: {e}")
        return False

def create_tables():
    """创建数据库表"""
    try:
        # 根据数据库类型选择不同的schema文件
        if db_config.db_type == "sqlite":
            schema_file = "database/schema_sqlite_separate.sql"  # 使用独立表结构
        elif db_config.db_type == "mysql":
            schema_file = "database/schema.sql"
        else:
            raise ValueError(f"不支持的数据库类型: {db_config.db_type}")
        
        # 检查schema文件是否存在
        if not os.path.exists(schema_file):
            print(f"Schema文件不存在: {schema_file}")
            return False
        
        # 读取并执行SQL文件
        with open(schema_file, "r", encoding="utf-8") as f:
            sql_content = f.read()
        
        # 根据数据库类型使用不同的分割策略
        if db_config.db_type == "sqlite":
            # SQLite: 直接执行SQL语句
            sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            with get_db_session() as session:
                for sql in sql_statements:
                    if sql:
                        session.execute(text(sql))
            
            print("SQLite数据库表创建成功")
            return True
        else:
            # MySQL: 分割SQL语句并执行
            sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            with get_db_session() as session:
                for sql in sql_statements:
                    if sql:
                        session.execute(text(sql))
            
            print(f"{db_config.db_type.upper()}数据库表创建成功")
            return True
    except Exception as e:
        print(f"数据库表创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_db_type() -> str:
    """获取当前数据库类型"""
    return db_config.db_type
