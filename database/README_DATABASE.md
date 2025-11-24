# RAG评估系统数据库配置说明

## 概述

RAG评估系统现在支持两种数据库：
- **MySQL**: 适合生产环境，支持多用户并发访问
- **SQLite**: 适合开发和小型部署，无需额外配置

## 数据库选择

### 配置方法

在项目根目录的 `.env` 文件中设置 `DB_TYPE` 参数：

```bash
# 使用SQLite（默认）
DB_TYPE=sqlite
SQLITE_DB_PATH=database/rag_evaluate.db

# 或使用MySQL
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=rag_evaluate
DB_CHARSET=utf8mb4
```

### SQLite配置

**优点：**
- 无需安装数据库服务器
- 配置简单，开箱即用
- 数据存储在单个文件中，便于备份和迁移
- 适合单用户环境和小型应用

**配置示例：**
```bash
DB_TYPE=sqlite
SQLITE_DB_PATH=database/rag_evaluate.db
```

**注意事项：**
- SQLite数据库文件会自动创建
- 确保目录有读写权限
- 不适合高并发场景

### MySQL配置

**优点：**
- 支持多用户并发访问
- 性能更好，适合大数据量
- 更完善的事务支持
- 适合生产环境

**配置示例：**
```bash
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=rag_evaluate
DB_CHARSET=utf8mb4
```

**前置条件：**
1. 安装MySQL服务器
2. 创建数据库：
   ```sql
   CREATE DATABASE rag_evaluate CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. 确保用户有足够权限

## 数据库初始化

### 1. 配置环境变量

复制 `env.example` 为 `.env` 并配置数据库参数：

```bash
cp env.example .env
# 编辑 .env 文件，设置数据库配置
```

### 2. 运行初始化脚本

```bash
python database/init_database.py
```

初始化脚本会：
- 测试数据库连接
- 创建所需的表结构
- 验证数据库服务

### 3. 验证安装

初始化成功后，你会看到类似输出：

```
🚀 开始初始化RAG评估系统数据库...
==================================================
📋 数据库配置:
   数据库类型: SQLITE
   数据库文件: database/rag_evaluate.db

🔗 测试数据库连接...
✅ 数据库连接成功！

📊 创建SQLITE数据库表...
✅ SQLITE数据库表创建成功！

🧪 测试数据库服务...
✅ 数据库服务测试成功！
   当前记录数: 0
   BM25评估: 0
   Ragas评估: 0

==================================================
🎉 数据库初始化完成！
```

## 数据库切换

如果需要切换数据库类型：

1. 修改 `.env` 文件中的 `DB_TYPE` 参数
2. 配置相应的数据库连接参数
3. 重新运行初始化脚本
4. 重启应用程序

**注意：** 切换数据库类型不会迁移已有数据，需要手动导出导入。

## 数据表结构

系统使用统一的表结构 `evaluation_results`，包含以下字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键，自增 |
| evaluation_type | STRING | 评估类型 (BM25/RAGAS) |
| evaluation_time | DATETIME | 评估时间 |
| description | TEXT | 评估描述 |
| context_precision | FLOAT | 上下文准确率 |
| context_recall | FLOAT | 上下文召回率 |
| faithfulness | FLOAT | 忠实度 (仅Ragas) |
| answer_relevancy | FLOAT | 答案相关性 (仅Ragas) |
| context_entity_recall | FLOAT | 实体召回率 (仅Ragas) |
| context_relevance | FLOAT | 上下文相关性 (仅Ragas) |
| answer_correctness | FLOAT | 答案正确性 (仅Ragas) |
| answer_similarity | FLOAT | 答案相似度 (仅Ragas) |
| total_samples | INTEGER | 总样本数 |
| total_irrelevant_chunks | INTEGER | 不相关分块数 |
| total_missed_chunks | INTEGER | 未召回分块数 |
| detailed_results | JSON | 详细结果 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

## 历史数据查询

系统支持通过Web界面查询历史评估数据：

1. 启动应用：`python app.py`
2. 访问：`http://localhost:8000/static/history.html`
3. 查看各项指标的历史趋势图表

## 故障排除

### SQLite问题

**问题：** 数据库文件无法创建
- 检查目录权限
- 确保路径正确
- 检查磁盘空间

**问题：** 数据库锁定
- SQLite不支持高并发写入
- 考虑切换到MySQL

### MySQL问题

**问题：** 连接失败
- 检查MySQL服务是否运行
- 验证主机、端口、用户名和密码
- 检查防火墙设置

**问题：** 权限不足
```sql
GRANT ALL PRIVILEGES ON rag_evaluate.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

## 数据备份

### SQLite备份

```bash
# 直接复制数据库文件
cp database/rag_evaluate.db database/rag_evaluate_backup.db
```

### MySQL备份

```bash
# 使用mysqldump
mysqldump -u root -p rag_evaluate > backup.sql

# 恢复
mysql -u root -p rag_evaluate < backup.sql
```

## 性能建议

### SQLite
- 适合单用户、小数据量（< 10万条记录）
- 定期清理旧数据
- 考虑使用WAL模式提高并发性能

### MySQL
- 定期优化表：`OPTIMIZE TABLE evaluation_results;`
- 监控慢查询
- 适当调整连接池大小
- 定期备份数据

## 技术细节

### 兼容性处理

系统通过以下方式实现两种数据库的兼容：

1. **数据类型映射**
   - MySQL的ENUM → SQLite的TEXT + CHECK约束
   - MySQL的DECIMAL → SQLite的REAL
   - MySQL的JSON → SQLite的TEXT

2. **SQL语句兼容**
   - 使用参数化查询
   - 避免数据库特定语法
   - 统一使用SQLAlchemy ORM

3. **自动更新时间戳**
   - MySQL: `ON UPDATE CURRENT_TIMESTAMP`
   - SQLite: TRIGGER触发器

### 依赖包

```
SQLAlchemy>=2.0.0
PyMySQL>=1.0.0  # 仅MySQL需要
```

## 更多信息

如有问题，请查看：
- SQLAlchemy文档：https://docs.sqlalchemy.org/
- SQLite文档：https://www.sqlite.org/docs.html
- MySQL文档：https://dev.mysql.com/doc/

