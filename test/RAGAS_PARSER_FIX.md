# Ragas 解析器问题修复说明

## 问题描述

运行 Ragas 评估时遇到以下错误：

```
ERROR:ragas.prompt.pydantic_prompt:Prompt fix_output_format failed to parse output
ERROR:ragas.prompt.pydantic_prompt:Prompt extract_entities_prompt failed to parse output
RagasOutputParserException(The output parser failed to parse the output including retries.)
```

## 问题原因

1. **Temperature 设置过高**：默认 temperature 为 0.1，导致 LLM 输出不够稳定
2. **ContextEntityRecall 指标问题**：该指标使用 LLM 提取实体，容易触发解析器错误
3. **Ragas 版本兼容性**：使用 Ragas 0.3.2，某些 LLM 输出格式可能不兼容

## 修复方案

### 1. 优化 LLM 采样参数（Temperature + Top-P）

**文件**: `read_chuck.py`

```python
# 修改前
temperature: float = 0.1
max_chunk_length: int = 200

# 修改后
temperature: float = 0.0  # 使用 0.0 以获得更稳定的输出，提高 Ragas 解析器成功率
top_p: float = 0.1  # 降低采样多样性，只从最高概率的 10% token 中选择
max_tokens: int = 2000  # 最大生成 token 数
max_chunk_length: int = 200
```

**参数说明**：
- `temperature=0.0`: 完全确定性输出，选择最高概率的 token
- `top_p=0.1`: Nucleus Sampling，只从累积概率最高的 10% token 中选择
- `max_tokens=2000`: 限制生成长度，避免过长输出导致解析失败

这三个参数共同作用，确保 LLM 输出的 JSON 格式最稳定可靠。

### 2. 在创建 LLM 实例时设置采样参数

**文件**: `rag_evaluator.py`

**⚠️ 重要**：Qwen API 要求参数**显式指定**，不能使用 `model_kwargs`！

```python
# 创建Qwen LLM实例
# 使用严格的采样参数以获得最稳定的 JSON 输出
# 注意：Qwen API 要求参数显式指定，不能使用 model_kwargs
self.llm = ChatOpenAI(
    model=self.config.model_name,
    openai_api_key=self.config.api_key,
    openai_api_base=self.config.api_base,
    temperature=self.config.temperature,  # 0.0
    max_tokens=self.config.max_tokens,  # 2000 - 显式指定
    top_p=self.config.top_p,  # 0.1 - 显式指定
)
```

**错误示例**（会导致验证错误）：
```python
# ❌ 错误：使用 model_kwargs 会报错
self.llm = ChatOpenAI(
    ...
    model_kwargs={
        "top_p": 0.1,
        "max_tokens": 2000
    }
)
# 报错：Parameters {'max_tokens', 'top_p'} should be specified explicitly.
```

**正确示例**：
```python
# ✅ 正确：直接作为参数传递
self.llm = ChatOpenAI(
    ...
    temperature=0.0,
    top_p=0.1,
    max_tokens=2000
)
```

### 3. 移除容易出错的 ContextEntityRecall 指标

**文件**: `rag_evaluator.py`

```python
# 使用核心指标，避免使用容易出错的 ContextEntityRecall
# ContextEntityRecall 使用 LLM 提取实体，容易触发解析器错误
metrics = [
    Faithfulness(),  # 忠实度
    AnswerRelevancy(embeddings=self.ragas_embeddings),  # 回答相关性
    ContextPrecision(),  # 上下文精确度
    ContextRecall(),  # 上下文召回率
    # 暂时移除 ContextEntityRecall，因为它容易导致解析器错误
    # ContextEntityRecall(),  # 上下文实体召回率
    ContextRelevance(),  # 上下文相关性
    AnswerCorrectness(embeddings=self.ragas_embeddings),  # 回答正确性
    AnswerSimilarity(embeddings=self.ragas_embeddings)  # 回答相似度
]
```

### 4. 增强错误处理和降级策略

**文件**: `rag_evaluator.py`

添加了更智能的错误处理：
- 检测解析器错误
- 自动降级到更稳定的指标
- 提供详细的错误信息
- 最终回退到 fallback 模式

## 测试建议

### 1. 运行诊断脚本

```bash
python test/test_ragas_parser_issue.py
```

### 2. 运行实际评估

```bash
python -m uvicorn app:app --reload
```

在 Web 界面中运行 Ragas 评估，应该不再出现解析器错误。

## 注意事项

1. **Temperature 设置为 0.0** 可能会略微降低输出的多样性，但对于评估任务来说是安全的
2. **移除 ContextEntityRecall** 意味着该指标不再计算，但其他 7 个核心指标仍然可用
3. 如果仍然遇到问题，系统会自动降级到更简单的评估模式

## 未来改进

1. 考虑实现自定义的 ContextEntityRecall 实现，绕过 Ragas 的解析器
2. 添加更多的错误重试机制
3. 考虑升级到更新版本的 Ragas（如果有的话）

## 相关文件

- `read_chuck.py` - 配置定义
- `rag_evaluator.py` - Ragas 评估器实现
- `test/test_ragas_parser_issue.py` - 诊断脚本
- `app.py` - Web 应用主文件
