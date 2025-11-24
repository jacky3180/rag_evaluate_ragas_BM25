# 数据库支持功能更新总结

## 📋 更新概述

本次更新为RAG评估系统添加了SQLite数据库支持，使系统能够同时支持MySQL和SQLite两种数据库。用户可以根据自己的需求在 `.env` 配置文件中自由选择使用哪种数据库。

## 🎯 实现目标

✅ 支持SQLite数据库  
✅ 保持对MySQL的完全兼容  
✅ 通过配置文件灵活切换数据库  
✅ 统一的数据库接口和操作  
✅ 支持history.html查询历史评测数据  
✅ 完整的文档和测试  

## 📁 修改的文件

### 1. 配置文件

#### `env.example`
- **修改内容**: 添加数据库类型选择配置
- **新增配置项**:
  - `DB_TYPE`: 数据库类型选择（mysql/sqlite）
  - `SQLITE_DB_PATH`: SQLite数据库文件路径

```env
# 数据库类型选择：mysql 或 sqlite
DB_TYPE=sqlite
# SQLite数据库文件路径（仅当DB_TYPE=sqlite时使用）
SQLITE_DB_PATH=database/rag_evaluate.db
```

### 2. 数据库模块

#### `database/db_config.py`
- **修改内容**: 完全重写以支持两种数据库
- **主要改进**:
  - 根据`DB_TYPE`动态选择数据库引擎
  - SQLite自动创建数据库文件和目录
  - 添加`get_db_type()`函数获取当前数据库类型
  - 根据数据库类型选择不同的schema文件
  - 为SQLite添加特定配置（如`check_same_thread=False`）

#### `database/models.py`
- **修改内容**: 模型定义兼容两种数据库
- **主要改进**:
  - 将`Enum`类型改为`String`类型（SQLite不支持Enum）
  - 将`DECIMAL`类型改为`Float`类型（统一数值类型）
  - 保持`JSON`类型（SQLAlchemy会自动处理）
  - 确保`to_dict()`方法正确处理所有字段类型

#### `database/db_service.py`
- **修改内容**: 数据库操作服务兼容两种数据库
- **主要改进**:
  - 统一使用`evaluation_results`表（而非分离的bm25/ragas表）
  - 使用参数化查询确保SQL语句兼容性
  - 更新`get_evaluation_history()`函数使用新表结构
  - 更新`get_evaluation_stats()`函数使用新表结构
  - 添加更好的错误处理和调试信息

#### `database/init_database.py`
- **修改内容**: 初始化脚本支持两种数据库
- **主要改进**:
  - 显示当前使用的数据库类型
  - 根据数据库类型显示不同的配置信息
  - SQLite自动创建数据库目录
  - 提供数据库特定的使用提示

### 3. 新增文件

#### `database/schema_sqlite.sql`
- **内容**: SQLite数据库表结构定义
- **特点**:
  - 使用SQLite兼容的语法
  - `TEXT CHECK`约束替代`ENUM`类型
  - 使用触发器实现`updated_at`自动更新
  - 创建索引优化查询性能

#### `database/README_DATABASE.md`
- **内容**: 完整的数据库配置和使用文档
- **包含**:
  - 两种数据库的详细配置说明
  - 数据库切换指南
  - 数据表结构说明
  - 故障排除指南
  - 性能建议
  - 备份恢复方法

#### `QUICKSTART_DATABASE.md`
- **内容**: 快速开始指南
- **包含**:
  - SQLite快速配置（3步完成）
  - MySQL详细配置步骤
  - 数据库切换指南
  - 常见问题解答
  - 最佳实践建议

#### `test/test_database_switch.py`
- **内容**: 数据库功能测试脚本
- **测试内容**:
  - 数据库连接测试
  - 保存BM25和Ragas结果
  - 查询统计信息
  - 查询历史记录
  - 根据ID和类型查询
  - 历史数据API测试
  - 统计概览API测试

#### `DATABASE_CHANGES_SUMMARY.md`
- **内容**: 本文件，更改总结文档

### 4. 更新的文档

#### `README.md`
- **修改内容**: 添加数据库配置章节
- **新增内容**:
  - SQLite和MySQL配置说明
  - 数据库初始化步骤
  - 链接到详细文档

## 🔧 技术实现细节

### 数据库兼容性处理

1. **数据类型映射**
   - MySQL `ENUM` → SQLite `TEXT` with `CHECK` constraint
   - MySQL `DECIMAL` → SQLite `REAL` (统一使用Float)
   - MySQL `JSON` → SQLite `TEXT` (SQLAlchemy自动处理)
   - MySQL `TIMESTAMP` → SQLite `DATETIME`

2. **自动更新时间戳**
   - MySQL: 使用 `ON UPDATE CURRENT_TIMESTAMP`
   - SQLite: 使用 `TRIGGER` 触发器

3. **SQL语句兼容**
   - 使用参数化查询 (`:param` 语法)
   - 避免数据库特定的函数和语法
   - 统一使用标准SQL语句

4. **连接配置**
   - MySQL: 添加连接池配置 (`pool_pre_ping`, `pool_recycle`)
   - SQLite: 添加线程安全配置 (`check_same_thread=False`)

### 统一的表结构

新的表结构 `evaluation_results` 统一存储BM25和Ragas评估结果：

```sql
CREATE TABLE evaluation_results (
    id INTEGER PRIMARY KEY,
    evaluation_type TEXT,  -- 'BM25' 或 'RAGAS'
    context_precision REAL,
    context_recall REAL,
    faithfulness REAL,     -- 仅Ragas使用
    answer_relevancy REAL, -- 仅Ragas使用
    ...
);
```

这样的设计：
- 简化了查询逻辑
- 便于统计分析
- 减少表连接操作
- 更容易维护

## 📊 功能验证

### 自动化测试

运行测试脚本验证所有功能：

```bash
python test/test_database_switch.py
```

测试覆盖：
- ✅ 数据库连接
- ✅ 表创建
- ✅ 数据插入（BM25和Ragas）
- ✅ 数据查询（按ID、类型、历史）
- ✅ 统计信息
- ✅ 历史数据API
- ✅ 统计概览API

### Web界面验证

1. 启动应用：`python app.py`
2. 访问历史数据页面：http://localhost:8000/static/history.html
3. 验证功能：
   - ✅ 图表显示
   - ✅ 数据表格
   - ✅ 日期筛选
   - ✅ 统计概览

## 🔄 迁移指南

### 从旧版本升级

如果你之前使用的是MySQL的旧表结构（`bm25_evaluations` 和 `ragas_evaluations`），需要迁移数据：

**选项1：重新初始化（推荐用于测试环境）**
```bash
# 备份旧数据（可选）
mysqldump -u root -p rag_evaluate > backup_old.sql

# 重新初始化
python database/init_database.py
```

**选项2：数据迁移（用于生产环境）**
```sql
-- 迁移BM25数据
INSERT INTO evaluation_results (
    evaluation_type, context_precision, context_recall, 
    total_samples, created_at
)
SELECT 
    'BM25', context_precision, context_recall,
    total_samples, created_at
FROM bm25_evaluations;

-- 迁移Ragas数据
INSERT INTO evaluation_results (
    evaluation_type, context_precision, context_recall,
    faithfulness, answer_relevancy, created_at
)
SELECT 
    'RAGAS', context_precision, context_recall,
    faithfulness, answer_relevancy, created_at
FROM ragas_evaluations;
```

### 切换数据库类型

**从MySQL切换到SQLite：**
1. 修改 `.env`: `DB_TYPE=sqlite`
2. 运行初始化：`python database/init_database.py`
3. 重启应用

**从SQLite切换到MySQL：**
1. 创建MySQL数据库
2. 修改 `.env`: `DB_TYPE=mysql` 并配置连接参数
3. 运行初始化：`python database/init_database.py`
4. 重启应用

## 📝 使用示例

### 配置SQLite（默认）

```bash
# .env
DB_TYPE=sqlite
SQLITE_DB_PATH=database/rag_evaluate.db
```

### 配置MySQL

```bash
# .env
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=rag_evaluate
```

### 初始化和测试

```bash
# 初始化数据库
python database/init_database.py

# 运行测试
python test/test_database_switch.py

# 启动应用
python app.py

# 访问历史数据
# 浏览器打开: http://localhost:8000/static/history.html
```

## 🎉 优势总结

### 对于开发者
- ✅ 无需配置MySQL即可开始开发
- ✅ SQLite数据文件易于备份和分享
- ✅ 快速原型开发和测试

### 对于用户
- ✅ 根据规模选择合适的数据库
- ✅ 小型部署零配置
- ✅ 大型部署高性能

### 对于系统
- ✅ 统一的数据接口
- ✅ 代码可维护性高
- ✅ 易于扩展其他数据库

## 📚 相关文档

- **快速开始**: [QUICKSTART_DATABASE.md](QUICKSTART_DATABASE.md)
- **详细文档**: [database/README_DATABASE.md](database/README_DATABASE.md)
- **主文档**: [README.md](README.md)

## 🔍 注意事项

1. **数据不会自动迁移**：切换数据库类型时，需要手动迁移数据
2. **SQLite并发限制**：SQLite不适合高并发写入场景
3. **JSON字段处理**：两种数据库的JSON处理方式略有不同，但系统已自动处理
4. **备份策略**：SQLite需要备份数据库文件，MySQL使用mysqldump
5. **性能考虑**：大数据量（>10万条记录）建议使用MySQL

## ✅ 测试清单

部署前请确认：

- [ ] `.env` 文件已正确配置
- [ ] 数据库初始化成功
- [ ] 测试脚本全部通过
- [ ] Web界面可以访问
- [ ] 历史数据页面正常显示
- [ ] 评估结果能够保存到数据库
- [ ] 历史数据查询API正常工作

## 🤝 贡献

如果发现问题或有改进建议，欢迎：
- 提交Issue
- 提交Pull Request
- 更新文档

---

**更新日期**: 2025-10-15  
**版本**: 1.0.0  
**作者**: RAG评估系统开发团队

