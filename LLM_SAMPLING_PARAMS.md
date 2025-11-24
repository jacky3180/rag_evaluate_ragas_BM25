# LLM 采样参数配置说明

## 概述

为了确保 Ragas 评估中 LLM 输出的 JSON 格式稳定可靠，避免解析器错误，我们优化了 Qwen LLM 的采样参数配置。

## 核心参数

### 1. Temperature (温度)

**当前值**: `0.0`

**作用**: 控制输出的随机性
- `temperature = 0.0`: 完全确定性，始终选择概率最高的 token
- `temperature > 0`: 增加随机性，值越大输出越多样化

**为什么选择 0.0**:
- JSON 格式要求严格，不需要创意性输出
- 确定性输出确保每次生成的格式一致
- 最大化解析成功率

### 2. Top-P (核采样)

**当前值**: `0.1`

**作用**: Nucleus Sampling，只从累积概率达到 P 的最小 token 集合中采样
- `top_p = 0.1`: 只考虑累积概率前 10% 的 token
- `top_p = 1.0`: 考虑所有 token

**为什么选择 0.1**:
- 与 temperature=0.0 配合使用，进一步限制输出空间
- 避免低概率但格式错误的 token 被选中
- 提高 JSON 格式的一致性

### 3. Max Tokens (最大生成长度)

**当前值**: `2000`

**作用**: 限制单次生成的最大 token 数量

**为什么选择 2000**:
- 足够生成完整的评估响应
- 避免过长输出导致超时或解析失败
- 控制 API 调用成本

## 配置位置

### 1. EvaluationConfig (read_chuck.py)

```python
@dataclass
class EvaluationConfig:
    # 评估配置（LLM 输出稳定性参数）
    temperature: float = 0.0  # 使用 0.0 以获得更稳定的输出
    top_p: float = 0.1  # 降低采样多样性
    max_tokens: int = 2000  # 最大生成 token 数
```

### 2. RagasEvaluator (rag_evaluator.py)

**⚠️ 重要**：Qwen API 要求参数**显式指定**，不能使用 `model_kwargs`！

```python
# 创建 LLM 实例时应用参数
# 注意：参数必须显式指定，不能使用 model_kwargs
self.llm = ChatOpenAI(
    model=self.config.model_name,
    openai_api_key=self.config.api_key,
    openai_api_base=self.config.api_base,
    temperature=self.config.temperature,
    max_tokens=self.config.max_tokens,  # 显式指定
    top_p=self.config.top_p,  # 显式指定
)
```

### 3. StandardDatasetBuilder (standardDatasetBuild.py)

```python
# 配置 Langchain LLM
# 注意：参数必须显式指定，不能使用 model_kwargs
self.llm = ChatOpenAI(
    model=os.getenv('MODEL_NAME', 'qwen-plus'),
    api_key=os.getenv('OPENAI_API_KEY') or os.getenv('QWEN_API_KEY'),
    base_url=os.getenv('OPENAI_API_BASE'),
    temperature=0.0,
    top_p=0.1,  # 显式指定
    max_tokens=2000  # 显式指定
)
```

## 参数组合效果

| Temperature | Top-P | 效果 |
|------------|-------|------|
| 0.0 | 1.0 | 确定性输出，但仍可能选择低概率 token |
| 0.0 | 0.1 | **最稳定** - 确定性 + 高概率 token |
| 0.1 | 1.0 | 轻微随机性，可能导致格式不一致 |
| 0.7 | 0.9 | 高随机性，不适合 JSON 生成 |

当前配置 (`temperature=0.0, top_p=0.1`) 是最保守也最稳定的组合。

## Qwen 模型特性

Qwen 模型支持以下参数（通过 OpenAI 兼容 API）：

- `temperature`: 温度参数
- `top_p`: 核采样参数
- `top_k`: Top-K 采样（Qwen 可能不支持，使用 top_p 代替）
- `max_tokens`: 最大生成长度
- `presence_penalty`: 存在惩罚（降低重复）
- `frequency_penalty`: 频率惩罚（降低高频词）

### ⚠️ 重要：参数传递方式

**Qwen API 要求参数必须显式指定，不能使用 `model_kwargs`**！

```python
# ❌ 错误方式（会导致验证错误）
self.llm = ChatOpenAI(
    model="qwen-plus",
    temperature=0.0,
    model_kwargs={
        "top_p": 0.1,  # ❌ 错误
        "max_tokens": 2000  # ❌ 错误
    }
)
# 报错：Parameters {'max_tokens', 'top_p'} should be specified explicitly.

# ✅ 正确方式（显式指定参数）
self.llm = ChatOpenAI(
    model="qwen-plus",
    temperature=0.0,
    top_p=0.1,  # ✅ 正确
    max_tokens=2000  # ✅ 正确
)
```

**原因**: Qwen 的 OpenAI 兼容 API 使用了更严格的参数验证，要求某些参数必须作为构造函数的直接参数传递，而不是通过 `model_kwargs` 字典传递。

## 故障排查

### 如果仍然出现解析错误

1. **检查参数是否生效**:
   ```python
   # 在日志中查找
   🎯 LLM 采样参数: temperature=0.0, top_p=0.1
   ```

2. **尝试更保守的配置**:
   ```python
   temperature: float = 0.0
   top_p: float = 0.05  # 进一步降低到 5%
   ```

3. **检查 model_kwargs**:
   ```python
   # 确保 model_kwargs 被正确传递
   print(self.llm.model_kwargs)
   # 输出应为: {'top_p': 0.1, 'max_tokens': 2000}
   ```

4. **验证 API 支持**:
   某些 Qwen API 端点可能不支持所有参数，查看 API 文档确认。

## 性能影响

### 优点
- ✅ 大幅提高 JSON 解析成功率
- ✅ 输出一致性提高
- ✅ 减少重试次数
- ✅ 降低评估失败率

### 潜在缺点
- ⚠️ 输出缺乏多样性（对评估任务无影响）
- ⚠️ 可能在某些创意任务中表现较差（不适用于本项目）

## 总结

当前采样参数配置（`temperature=0.0, top_p=0.1, max_tokens=2000`）专门针对 Ragas 评估任务优化，确保：

1. **最高的输出稳定性** - 避免随机性导致的格式错误
2. **最佳的解析成功率** - JSON 格式严格一致
3. **最低的错误率** - 减少 `RagasOutputParserException`

这些参数不适用于需要创意性输出的任务，但对于结构化评估任务是最优选择。

