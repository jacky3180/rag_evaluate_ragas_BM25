# 数据库功能快速开始指南

本指南帮助你快速配置和使用RAG评估系统的数据库功能。

## 🚀 快速开始（使用SQLite）

SQLite是最简单的选择，无需额外安装数据库服务器。

### 1. 配置环境变量

编辑 `.env` 文件（如果没有，从 `env.example` 复制一份）：

```bash
# 设置数据库类型为SQLite
DB_TYPE=sqlite
SQLITE_DB_PATH=database/rag_evaluate.db
```

### 2. 初始化数据库

```bash
python database/init_database.py
```

你会看到类似的输出：

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

### 3. 运行测试

```bash
python test/test_database_switch.py
```

### 4. 启动Web应用

```bash
python app.py
```

### 5. 查看历史数据

访问：http://localhost:8000/static/history.html

## 📊 使用MySQL（生产环境推荐）

如果你需要更强大的数据库功能和多用户并发支持，可以使用MySQL。

### 1. 安装MySQL

根据你的操作系统安装MySQL服务器：

**Windows:**
- 下载并安装：https://dev.mysql.com/downloads/installer/

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
```

**macOS:**
```bash
brew install mysql
brew services start mysql
```

### 2. 创建数据库

登录MySQL并创建数据库：

```bash
mysql -u root -p
```

```sql
CREATE DATABASE rag_evaluate CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON rag_evaluate.* TO 'your_user'@'localhost' IDENTIFIED BY 'your_password';
FLUSH PRIVILEGES;
EXIT;
```

### 3. 配置环境变量

编辑 `.env` 文件：

```bash
# 设置数据库类型为MySQL
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=rag_evaluate
DB_CHARSET=utf8mb4
```

### 4. 初始化数据库

```bash
python database/init_database.py
```

### 5. 测试和使用

同SQLite的步骤3-5。

## 🔄 在两种数据库之间切换

### 从SQLite切换到MySQL

1. 备份SQLite数据（可选）：
```bash
cp database/rag_evaluate.db database/rag_evaluate_backup.db
```

2. 修改 `.env` 文件中的 `DB_TYPE` 为 `mysql`

3. 配置MySQL连接参数

4. 运行初始化脚本：
```bash
python database/init_database.py
```

5. 重启应用

### 从MySQL切换到SQLite

1. 备份MySQL数据（可选）：
```bash
mysqldump -u root -p rag_evaluate > backup.sql
```

2. 修改 `.env` 文件中的 `DB_TYPE` 为 `sqlite`

3. 运行初始化脚本：
```bash
python database/init_database.py
```

4. 重启应用

**注意：** 切换数据库类型不会自动迁移数据，需要手动导出导入。

## 📈 使用历史数据分析功能

系统会自动将评估结果保存到数据库。你可以通过Web界面查看历史数据：

### 访问历史数据页面

1. 启动应用：`python app.py`
2. 在浏览器中访问：http://localhost:8000/static/history.html

### 功能特性

- **趋势图表**：查看各项指标随时间的变化趋势
- **数据统计**：总评估次数、平均准确率、平均召回率等
- **日期筛选**：按日期范围筛选历史数据
- **数据表格**：查看详细的数值数据

### 支持的指标

**BM25评估：**
- Context Precision
- Context Recall
- F1-Score
- NDCG

**Ragas评估：**
- Context Precision
- Context Recall
- Faithfulness
- Answer Relevancy
- Answer Correctness
- Answer Similarity

## 🛠️ 常见问题

### Q1: 数据库文件在哪里？

**SQLite:** 默认位置 `database/rag_evaluate.db`

你可以通过 `.env` 中的 `SQLITE_DB_PATH` 修改路径。

### Q2: 如何查看SQLite数据？

推荐使用以下工具：
- **DB Browser for SQLite**: https://sqlitebrowser.org/
- **DBeaver**: https://dbeaver.io/
- **命令行**:
  ```bash
  sqlite3 database/rag_evaluate.db
  .tables
  SELECT * FROM evaluation_results LIMIT 5;
  ```

### Q3: 如何备份数据？

**SQLite:**
```bash
# 备份
cp database/rag_evaluate.db database/backup/rag_evaluate_$(date +%Y%m%d).db

# 恢复
cp database/backup/rag_evaluate_20250101.db database/rag_evaluate.db
```

**MySQL:**
```bash
# 备份
mysqldump -u root -p rag_evaluate > backup_$(date +%Y%m%d).sql

# 恢复
mysql -u root -p rag_evaluate < backup_20250101.sql
```

### Q4: 数据库太大怎么办？

可以定期清理旧数据：

```python
from database.db_service import DatabaseService

# 删除指定ID的评估记录
DatabaseService.delete_evaluation(evaluation_id)
```

或者直接在数据库中清理：

**SQLite:**
```sql
-- 删除30天前的记录
DELETE FROM evaluation_results 
WHERE created_at < datetime('now', '-30 days');

-- 优化数据库文件大小
VACUUM;
```

**MySQL:**
```sql
-- 删除30天前的记录
DELETE FROM evaluation_results 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 优化表
OPTIMIZE TABLE evaluation_results;
```

### Q5: 如何在不同环境使用不同数据库？

使用环境变量或不同的 `.env` 文件：

**开发环境 (.env.dev):**
```bash
DB_TYPE=sqlite
SQLITE_DB_PATH=database/rag_evaluate_dev.db
```

**生产环境 (.env.prod):**
```bash
DB_TYPE=mysql
DB_HOST=prod-mysql-server
DB_USER=prod_user
DB_PASSWORD=prod_password
```

然后在启动时指定：
```bash
cp .env.dev .env  # 开发环境
python app.py

cp .env.prod .env  # 生产环境
python app.py
```

## 📚 更多资源

- **详细数据库文档**: [database/README_DATABASE.md](database/README_DATABASE.md)
- **数据库测试脚本**: `test/test_database_switch.py`
- **数据库初始化**: `database/init_database.py`
- **SQLite Schema**: `database/schema_sqlite.sql`
- **MySQL Schema**: `database/schema.sql`

## 💡 最佳实践

1. **开发环境使用SQLite**：简单快速，无需配置
2. **生产环境使用MySQL**：性能更好，支持并发
3. **定期备份数据**：特别是SQLite，文件损坏会导致数据丢失
4. **监控数据库大小**：定期清理旧数据
5. **使用连接池**：系统已自动配置，无需额外设置

## 🤝 获取帮助

如果遇到问题：

1. 查看错误信息
2. 检查 `.env` 配置是否正确
3. 运行测试脚本确认问题：`python test/test_database_switch.py`
4. 查看详细文档：`database/README_DATABASE.md`

Happy Evaluating! 🎉

