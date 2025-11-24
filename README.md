# RAG评估系统

基于Ragas v0.3.2和BM25算法的综合RAG评估系统，支持多种评估指标和评估方法。

## 🚀 功能特性

### 🎯 支持的评估指标
- **Faithfulness** (忠实度) - 评估回答是否忠实于检索到的上下文
- **Answer Relevancy** (回答相关性) - 评估回答与问题的相关性
- **Context Precision** (上下文精确度) - 评估检索到的上下文的精确度
- **Context Recall** (上下文召回率) - 评估检索到的上下文的召回率
- **Context Entity Recall** (上下文实体召回率) - 评估实体级别的召回率
- **Context Relevance** (上下文相关性) - 评估上下文与问题的相关性
- **Answer Correctness** (回答正确性) - 评估回答的正确性
- **Answer Similarity** (回答相似度) - 评估回答与标准答案的相似度

### 🔧 评估方法
- **Ragas评估** - 基于LLM的语义评估，更准确但成本较高
- **BM25评估** - 基于传统信息检索的快速评估，成本低但精度相对较低
- **混合评估** - 结合两种方法的优势

### 🏗️ 模块化设计
- **DataLoader** - 数据加载和解析模块
- **TextProcessor** - 文本处理和分块模块
- **RagasEvaluator** - Ragas评估器模块
- **BM25Evaluator** - BM25评估器模块
- **ResultAnalyzer** - 结果分析模块
- **WebInterface** - Web界面和API接口

## 📦 安装依赖

### 快速安装
```bash
pip install -r requirements.txt
```

### 手动安装
```bash
# 核心依赖
pip install ragas==0.3.2
pip install langchain-openai
pip install fastapi uvicorn
pip install pandas numpy scikit-learn

# 可选依赖
pip install pymysql SQLAlchemy  # 数据库支持
pip install nltk jieba          # 中文文本处理
pip install openpyxl xlsxwriter # Excel文件处理
```

## ⚙️ 环境配置

### 1. 复制环境变量模板
```bash
cp env.example .env
```

### 2. 编辑 `.env` 文件
```env
# ==================== 必需配置 ====================
# Qwen API配置
QWEN_API_KEY=your_qwen_api_key_here
QWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL_NAME=qwen-plus
QWEN_EMBEDDING_MODEL=text-embedding-v1

# 数据文件路径
EXCEL_FILE_PATH=standardDataset/standardDataset.xlsx

# ==================== 可选配置 ====================
# Ollama本地模型配置
USE_OLLAMA=false
OLLAMA_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=embeddinggemma:300m
OLLAMA_LLM_MODEL=qwen2.5:7b

# 相似度阈值配置
SIMILARITY_THRESHOLD=0.5
SEMANTIC_CONTAINMENT_THRESHOLD=0.9

# 数据库配置（如果使用数据库功能）
# 数据库类型选择：mysql 或 sqlite
DB_TYPE=sqlite
# SQLite数据库文件路径（仅当DB_TYPE=sqlite时使用）
SQLITE_DB_PATH=database/rag_evaluate.db
# MySQL配置（仅当DB_TYPE=mysql时使用）
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=rag_evaluate
DB_CHARSET=utf8mb4
```

### 3. 数据库配置

系统支持两种数据库：**SQLite**（推荐用于开发和小型部署）和**MySQL**（推荐用于生产环境）

#### 使用SQLite（默认，无需额外配置）
```env
DB_TYPE=sqlite
SQLITE_DB_PATH=database/rag_evaluate.db
```

**优点：**
- 无需安装数据库服务器
- 配置简单，开箱即用
- 数据存储在单个文件中，便于备份

#### 使用MySQL
```env
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=rag_evaluate
```

**前置条件：**
1. 安装MySQL服务器
2. 创建数据库：
```sql
CREATE DATABASE rag_evaluate CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**初始化数据库：**
```bash
python database/init_database.py
```

详细配置说明请参考：[database/README_DATABASE.md](database/README_DATABASE.md)

### 4. 环境变量说明

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `QWEN_API_KEY` | ✅ | - | Qwen API密钥 |
| `QWEN_API_BASE` | ✅ | - | Qwen API基础URL |
| `EXCEL_FILE_PATH` | ✅ | standardDataset/standardDataset.xlsx | 数据文件路径 |
| `SIMILARITY_THRESHOLD` | ❌ | 0.5 | BM25相似度阈值 |
| `SEMANTIC_CONTAINMENT_THRESHOLD` | ❌ | 0.9 | 语义包含度阈值 |
| `USE_OLLAMA` | ❌ | false | 是否使用本地Ollama模型 |
| `QUIET_MODE` | ❌ | true | 静默模式，减少输出 |
| `VERBOSE_LOGGING` | ❌ | false | 详细日志输出 |
| `DISABLE_PROGRESS_BARS` | ❌ | true | 禁用进度条显示 |
| `DISABLE_DETAILED_LOGS` | ❌ | true | 禁用详细日志 |

## 数据格式

Excel文件需要包含以下列：

| 列名 | 描述 | 示例 |
|------|------|------|
| user_input | 用户输入问题 | "都有谁读了《三体》？" |
| retrieved_contexts | 检索到的上下文 | ["上下文1", "上下文2"] |
| response | 系统回答 | "根据文档内容，读过《三体》的同学包括..." |
| reference_contexts | 标准答案上下文 | ["标准上下文1", "标准上下文2"] |
| reference | 标准答案 | "王多多和张悦都读过《三体》..." |

## 🚀 使用方法

### 1. Web界面（推荐）

```bash
# 启动Web服务器
python run_server.py

# 访问 http://localhost:8000
```

### 2. 命令行使用

```bash
# Ragas评估
python rag_evaluator.py

# BM25评估
python BM25_evaluate.py



### 3. Python API使用

```python
import asyncio
from rag_evaluator import EvaluationConfig, MainController

async def main():
    # 创建配置
    config = EvaluationConfig(
        api_key="your_api_key",
        api_base="your_api_base",
        excel_file_path="your_data.xlsx"
    )
    
    # 创建主控制器并运行评估
    controller = MainController(config)
    results = await controller.run_evaluation()
    
    if "error" not in results:
        print("评估成功完成！")
    else:
        print(f"评估失败: {results['error']}")

asyncio.run(main())
```

### 4. 模块化使用

```python
from read_chuck import DataLoader, TextProcessor, EvaluationConfig
from rag_evaluator import RagasEvaluator, ResultAnalyzer
from BM25_evaluate import BM25Evaluator

# 创建各个模块
config = EvaluationConfig(api_key="key", api_base="base")
data_loader = DataLoader(config)
text_processor = TextProcessor(config)
ragas_evaluator = RagasEvaluator(config)
bm25_evaluator = BM25Evaluator(config)
result_analyzer = ResultAnalyzer()

# 使用各个模块
df = data_loader.load_excel_data()
df = text_processor.parse_context_columns(df)

# Ragas评估
ragas_results = await ragas_evaluator.evaluate(dataset)

# BM25评估
bm25_results = bm25_evaluator.run_evaluation()
```

### 自定义配置

```python
config = EvaluationConfig(
    api_key="your_api_key",
    api_base="your_api_base",
    model_name="qwen-max",  # 使用更强的模型
    embedding_model="text-embedding-v2",  # 使用更新的embedding模型
    temperature=0.05,  # 更低的温度
    max_chunk_length=300,  # 更大的文本块
    excel_file_path="custom_data.xlsx"
)
```

## 📊 项目结构

```
rag_evaluate/
├── 📁 static/                 # Web界面静态文件
│   ├── index.html            # 主页面
│   ├── history.html          # 历史记录页面
│   ├── style.css             # 样式文件
│   └── script.js             # 前端脚本
├── 📁 database/              # 数据库相关
│   ├── db_config.py          # 数据库配置
│   ├── db_service.py         # 数据库服务
│   └── models.py             # 数据模型
├── 📁 test/                  # 测试文件
├── 📁 standardDataset/       # 标准数据集
├── 📁 knowledgeDoc/          # 知识文档
├── 📁 exampleExcel/          # 示例Excel文件
├── app.py                    # FastAPI主应用
├── rag_evaluator.py          # Ragas评估器
├── BM25_evaluate.py          # BM25评估器
├── read_chuck.py             # 数据处理模块
├── standardDatasetBuild.py   # 标准数据集构建
├── run_server.py             # 服务器启动脚本
├── requirements.txt          # 依赖包列表
├── env.example               # 环境变量模板
└── README.md                 # 项目说明
```

## 输出示例

```
============================================================
📊 Ragas评估结果
============================================================
+-----------------------+------------------+----------+----------+
| 指标名称              | 中文名称         | 分数     | 百分比   |
+=======================+==================+==========+==========+
| Faithfulness          | 忠实度           | 0.7847   | 78.5%    |
+-----------------------+------------------+----------+----------+
| Answer Relevancy      | 回答相关性       | 0.8666   | 86.7%    |
+-----------------------+------------------+----------+----------+
| Context Precision     | 上下文精确度     | 0.3750   | 37.5%    |
+-----------------------+------------------+----------+----------+
| Context Recall        | 上下文召回率     | 0.5833   | 58.3%    |
+-----------------------+------------------+----------+----------+
| Context Entity Recall | 上下文实体召回率 | 0.5243   | 52.4%    |
+-----------------------+------------------+----------+----------+
| Context Relevance     | 上下文相关性     | 评估失败 | N/A      |
+-----------------------+------------------+----------+----------+
| Answer Correctness    | 回答正确性       | 0.5858   | 58.6%    |
+-----------------------+------------------+----------+----------+
| Answer Similarity     | 回答相似度       | 0.8553   | 85.5%    |
+-----------------------+------------------+----------+----------+

📋 详细分析:
  • 平均分数: 0.6536 (65.4%)
  • 有效指标数: 7/8
  • 最高分数: 回答相关性 (0.8666)
  • 最低分数: 上下文精确度 (0.3750)
```

## 架构设计

### 类图

```
EvaluationConfig
├── api_key: str
├── api_base: str
├── model_name: str
├── embedding_model: str
├── temperature: float
├── max_chunk_length: int
└── excel_file_path: str

DataLoader
├── config: EvaluationConfig
├── load_excel_data() -> pd.DataFrame
└── validate_data(df) -> bool

TextProcessor
├── config: EvaluationConfig
├── split_text_into_chunks(text) -> List[str]
├── process_contexts(contexts_str) -> List[str]
├── parse_context_columns(df) -> pd.DataFrame
└── is_empty_row_data(...) -> bool

RagasEvaluator
├── config: EvaluationConfig
├── llm: ChatOpenAI
├── embeddings: OpenAIEmbeddings
├── setup_environment()
├── create_ragas_dataset(df) -> EvaluationDataset
├── create_metrics() -> List[Any]
└── evaluate(dataset) -> Any

ResultAnalyzer
├── analyze_results(results) -> Dict[str, Any]
└── display_results(analysis)

MainController
├── config: EvaluationConfig
├── data_loader: DataLoader
├── text_processor: TextProcessor
├── ragas_evaluator: RagasEvaluator
├── result_analyzer: ResultAnalyzer
└── run_evaluation() -> Dict[str, Any]
```

## 技术特点

1. **严格按照Ragas v0.3.2** - 使用官方API和指标
2. **模块化设计** - 每个功能独立封装，易于维护和扩展
3. **配置驱动** - 通过配置文件管理所有参数
4. **错误处理** - 完善的异常处理和错误提示
5. **中文优化** - 针对中文文本的优化处理
6. **可扩展性** - 易于添加新的评估指标和功能

## ⚡ 性能优化

### 🚀 新增性能优化功能

**v1.0.0 性能优化版本已发布！** 🎉

通过数据库索引、API缓存、批量查询等多层次优化，系统整体性能提升约 **70%**：

- ⚡ 页面加载速度提升 **71%** (2.8s → 0.8s)
- 🚀 API调用减少 **75%** (8个 → 2个)
- 💾 数据库查询减少 **75%**
- 📊 图表渲染提升 **58%**
- 🎯 缓存命中率 **85%+**

**快速启用优化**:
```bash
# 1. 应用数据库索引（必需）
python database/apply_performance_indexes.py

# 2. 重启服务
python run_server.py

# 3. 验证效果
python test_performance.py
```

**详细文档**:
- 📖 [性能优化详细文档](PERFORMANCE_OPTIMIZATION.md)
- 🚀 [快速启动指南](PERFORMANCE_QUICKSTART.md)
- 📊 [优化总结](PERFORMANCE_SUMMARY.md)

### 快速运行模式
```bash
# 设置环境变量启用静默模式
export QUIET_MODE=true
export VERBOSE_LOGGING=false
export DISABLE_PROGRESS_BARS=true
export DISABLE_DETAILED_LOGS=true

# 运行评估
python run_server.py
```

### 性能优化配置
- `QUIET_MODE=true` - 启用静默模式，大幅减少控制台输出
- `VERBOSE_LOGGING=false` - 关闭详细日志，只显示关键信息
- `DISABLE_PROGRESS_BARS=true` - 禁用进度条，减少I/O开销
- `DISABLE_DETAILED_LOGS=true` - 禁用详细日志，提升运行速度

### 调试模式
```bash
# 启用调试模式查看详细信息
export DEBUG=true
export VERBOSE_LOGGING=true
export QUIET_MODE=false
```

### 缓存管理
```bash
# 查看缓存统计
curl http://localhost:8000/api/cache/stats

# 清空缓存（数据更新后建议执行）
curl -X POST http://localhost:8000/api/cache/clear
```

## 注意事项

1. 确保Excel文件格式正确，包含所有必需列
2. 设置正确的API密钥和基础URL
3. 确保网络连接正常，能够访问Qwen API
4. 评估过程可能需要较长时间，请耐心等待
5. 某些指标可能因为数据质量问题而评估失败
6. 使用静默模式可以显著提升运行速度

## 故障排除

### 常见问题

1. **API连接失败**
   - 检查API密钥和基础URL是否正确
   - 确认网络连接正常

2. **Excel文件读取失败**
   - 检查文件路径是否正确
   - 确认文件格式和列名是否正确

3. **评估指标失败**
   - 检查数据质量，确保没有空值
   - 确认上下文格式正确

4. **内存不足**
   - 减少数据量或增加系统内存
   - 调整文本块大小参数

## 开源指南

- 🎯 贡献流程、编码规范与提交要求请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)
- 🤝 社区协作遵循 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- 🛡️ 漏洞上报与披露流程详见 [`SECURITY.md`](SECURITY.md)
- 📝 版本更新记录位于 [`CHANGELOG.md`](CHANGELOG.md)

## 贡献

欢迎通过 Issue 和 Pull Request 共建项目。在提交前请确保：
- 遵循贡献指南中的封装、配置和测试要求
- 变更已更新相关文档和示例
- 未包含敏感信息或临时调试文件

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

