# 数据库支持文档索引

欢迎使用RAG评估系统的数据库功能！本系统现已支持MySQL和SQLite两种数据库。

## 🚀 我该从哪里开始？

### 新用户（首次使用）
👉 **[快速开始指南](QUICKSTART_DATABASE.md)**
- 5分钟配置SQLite数据库
- 简单3步开始使用
- 最常见问题解答

### 需要详细配置说明
👉 **[数据库详细文档](database/README_DATABASE.md)**
- 完整的配置说明
- MySQL和SQLite对比
- 性能优化建议
- 故障排除指南

### 了解更新内容
👉 **[更改总结](DATABASE_CHANGES_SUMMARY.md)**
- 修改的文件列表
- 技术实现细节
- 迁移指南
- 测试清单

## 📚 文档列表

### 核心文档

| 文档 | 描述 | 适合人群 |
|------|------|----------|
| [QUICKSTART_DATABASE.md](QUICKSTART_DATABASE.md) | 快速开始指南 | 所有用户 |
| [database/README_DATABASE.md](database/README_DATABASE.md) | 详细配置文档 | 需要深入了解的用户 |
| [DATABASE_CHANGES_SUMMARY.md](DATABASE_CHANGES_SUMMARY.md) | 更新总结 | 开发者、升级用户 |
| [README.md](README.md) | 主文档 | 所有用户 |

### 技术文档

| 文档 | 描述 |
|------|------|
| `database/schema.sql` | MySQL表结构定义 |
| `database/schema_sqlite.sql` | SQLite表结构定义 |
| `database/db_config.py` | 数据库配置模块 |
| `database/models.py` | 数据模型定义 |
| `database/db_service.py` | 数据库操作服务 |

### 脚本和工具

| 脚本 | 用途 | 命令 |
|------|------|------|
| `database/init_database.py` | 初始化数据库 | `python database/init_database.py` |
| `database/show_config.py` | 显示当前配置 | `python database/show_config.py` |
| `test/test_database_switch.py` | 测试数据库功能 | `python test/test_database_switch.py` |

## 🎯 常见任务指南

### 初次配置

```bash
# 1. 复制环境变量模板
cp env.example .env

# 2. 编辑.env，选择数据库类型
# DB_TYPE=sqlite  # 或 mysql

# 3. 初始化数据库
python database/init_database.py

# 4. 测试功能
python test/test_database_switch.py

# 5. 启动应用
python app.py
```

详细步骤：👉 [快速开始指南](QUICKSTART_DATABASE.md)

### 查看当前配置

```bash
python database/show_config.py
```

### 切换数据库类型

```bash
# 1. 修改.env文件中的DB_TYPE
# 2. 配置相应的连接参数
# 3. 重新初始化
python database/init_database.py
# 4. 重启应用
```

详细步骤：👉 [数据库切换指南](QUICKSTART_DATABASE.md#-在两种数据库之间切换)

### 备份数据

**SQLite:**
```bash
cp database/rag_evaluate.db database/backup/rag_evaluate_$(date +%Y%m%d).db
```

**MySQL:**
```bash
mysqldump -u root -p rag_evaluate > backup_$(date +%Y%m%d).sql
```

详细说明：👉 [备份和恢复](database/README_DATABASE.md#数据备份)

### 查看历史数据

1. 启动应用：`python app.py`
2. 浏览器访问：http://localhost:8000/static/history.html

使用说明：👉 [历史数据分析](QUICKSTART_DATABASE.md#-使用历史数据分析功能)

## 🔍 按场景查找

### 我想要...

#### 快速开始开发
- ✅ 使用**SQLite**（无需配置）
- 📖 阅读：[快速开始 - SQLite配置](QUICKSTART_DATABASE.md#-快速开始使用sqlite)

#### 部署到生产环境
- ✅ 使用**MySQL**（更好的性能和并发支持）
- 📖 阅读：[快速开始 - MySQL配置](QUICKSTART_DATABASE.md#-使用mysql生产环境推荐)

#### 从旧版本升级
- 📖 阅读：[迁移指南](DATABASE_CHANGES_SUMMARY.md#-迁移指南)

#### 解决连接问题
- 📖 阅读：[故障排除](database/README_DATABASE.md#故障排除)

#### 优化性能
- 📖 阅读：[性能建议](database/README_DATABASE.md#性能建议)

#### 了解技术细节
- 📖 阅读：[技术实现](DATABASE_CHANGES_SUMMARY.md#-技术实现细节)

## ❓ 常见问题快速链接

| 问题 | 答案位置 |
|------|----------|
| 数据库文件在哪里？ | [快速开始 - Q1](QUICKSTART_DATABASE.md#q1-数据库文件在哪里) |
| 如何查看SQLite数据？ | [快速开始 - Q2](QUICKSTART_DATABASE.md#q2-如何查看sqlite数据) |
| 如何备份数据？ | [快速开始 - Q3](QUICKSTART_DATABASE.md#q3-如何备份数据) |
| 数据库太大怎么办？ | [快速开始 - Q4](QUICKSTART_DATABASE.md#q4-数据库太大怎么办) |
| 不同环境用不同数据库？ | [快速开始 - Q5](QUICKSTART_DATABASE.md#q5-如何在不同环境使用不同数据库) |
| MySQL连接失败？ | [详细文档 - MySQL问题](database/README_DATABASE.md#mysql问题) |
| SQLite数据库锁定？ | [详细文档 - SQLite问题](database/README_DATABASE.md#sqlite问题) |

## 🛠️ 工具使用

### 查看配置
```bash
python database/show_config.py
```
显示当前数据库类型、连接信息、统计数据等。

### 初始化数据库
```bash
python database/init_database.py
```
创建表结构、测试连接、验证配置。

### 测试功能
```bash
python test/test_database_switch.py
```
运行完整的功能测试套件。

## 📊 功能对比

| 功能 | SQLite | MySQL |
|------|--------|-------|
| 安装配置 | ✅ 无需安装 | ⚠️ 需安装服务器 |
| 性能 | ✅ 小数据量快速 | ✅ 大数据量优秀 |
| 并发支持 | ⚠️ 有限 | ✅ 优秀 |
| 备份 | ✅ 复制文件 | ⚠️ 需要工具 |
| 适用场景 | 开发、小型部署 | 生产、大型部署 |
| 推荐数据量 | < 10万条 | 不限 |

详细对比：👉 [数据库选择](database/README_DATABASE.md#数据库选择)

## 🎓 学习路径

### 入门用户
1. 阅读 [快速开始指南](QUICKSTART_DATABASE.md)
2. 使用SQLite配置（3步完成）
3. 运行测试脚本验证
4. 查看历史数据页面

### 进阶用户
1. 阅读 [详细配置文档](database/README_DATABASE.md)
2. 了解两种数据库的区别
3. 根据需求选择合适的数据库
4. 学习性能优化技巧

### 开发者
1. 阅读 [更改总结](DATABASE_CHANGES_SUMMARY.md)
2. 了解技术实现细节
3. 查看代码注释
4. 参与贡献和改进

## 💡 最佳实践

### 推荐配置

**开发环境:**
```env
DB_TYPE=sqlite
SQLITE_DB_PATH=database/rag_evaluate_dev.db
```

**测试环境:**
```env
DB_TYPE=sqlite
SQLITE_DB_PATH=database/rag_evaluate_test.db
```

**生产环境:**
```env
DB_TYPE=mysql
DB_HOST=prod-mysql-server
DB_USER=prod_user
DB_PASSWORD=secure_password
DB_NAME=rag_evaluate
```

### 注意事项

1. ✅ 定期备份数据
2. ✅ 监控数据库大小
3. ✅ 定期清理旧数据
4. ✅ 使用环境变量管理配置
5. ⚠️ 不要在版本控制中提交.env文件

详细说明：👉 [最佳实践](QUICKSTART_DATABASE.md#-最佳实践)

## 🤝 获取帮助

### 遇到问题？

1. **查看文档**
   - 按场景查找本索引中的相关章节
   - 阅读常见问题解答

2. **运行诊断**
   ```bash
   python database/show_config.py
   python test/test_database_switch.py
   ```

3. **检查配置**
   - 验证.env文件设置
   - 确认数据库服务状态
   - 检查连接参数

4. **查看日志**
   - 应用程序输出
   - 数据库错误信息
   - 测试脚本结果

### 联系支持

- 📧 提交Issue
- 💬 查看已有讨论
- 📖 查阅详细文档

## 📦 相关资源

### 官方文档
- SQLAlchemy: https://docs.sqlalchemy.org/
- SQLite: https://www.sqlite.org/docs.html
- MySQL: https://dev.mysql.com/doc/

### 推荐工具
- **SQLite浏览器**: [DB Browser for SQLite](https://sqlitebrowser.org/)
- **数据库管理**: [DBeaver](https://dbeaver.io/)
- **MySQL客户端**: [MySQL Workbench](https://www.mysql.com/products/workbench/)

## 🎉 开始使用

准备好了吗？从这里开始：

👉 **[快速开始指南](QUICKSTART_DATABASE.md)**

只需3步，5分钟即可完成配置！

---

**提示**: 收藏本页面以便随时查找需要的文档！

**最后更新**: 2025-10-15

