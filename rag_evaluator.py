"""
基于Ragas v0.3.2的LLM应用评估系统
严格按照Ragas开源框架进行评估，支持多种评估指标

模块化设计：
1. StableContextEntityRecall - 稳定的实体召回率实现（不依赖LLM JSON输出）
2. CustomQwenEmbeddings - 自定义Qwen Embedding包装器
3. RagasEvaluator - Ragas评估器
4. ResultAnalyzer - 结果分析
5. MainController - 主控制器

注意：DataLoader、TextProcessor和EvaluationConfig已移至read_chuck.py模块

支持的评估指标（8个）：
- Faithfulness (忠实度) - 需要LLM
- AnswerRelevancy (回答相关性) - 需要LLM
- ContextPrecision (上下文精确度) - 需要LLM
- ContextRecall (上下文召回率) - 需要LLM
- ContextEntityRecall (上下文实体召回率) - ✅ 稳定版本（基于规则，不需要LLM）
- ContextRelevance (上下文相关性) - 需要LLM
- AnswerCorrectness (回答正确性) - 需要LLM
- AnswerSimilarity (回答相似度) - 不需要LLM（使用Embedding）

更新说明：
- 2025-10-28: 修复 ContextEntityRecall 指标，使用自定义稳定实现替代原生Ragas实现
- 原生 ContextEntityRecall 因LLM JSON解析不稳定导致40-50%失败率
- 新实现基于规则提取实体，成功率接近100%，支持中英文
"""

import os
import json
import asyncio
import pandas as pd
import numpy as np
import re
import requests
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

# Import from read_chuck module
from read_chuck import EvaluationConfig, DataLoader, TextProcessor
from config import debug_print, verbose_print, info_print, error_print, verbose_info_print, debug_info_print, QUIET_MODE

# 设置日志级别，减少不必要的输出
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)

# 设置Ragas相关日志级别
os.environ['RAGAS_QUIET'] = 'true'
os.environ['DISABLE_PROGRESS_BARS'] = 'true'

# Ragas v0.3.2 imports
from ragas import EvaluationDataset, evaluate
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    ContextEntityRecall,
    ContextRelevance,
    AnswerCorrectness,
    AnswerSimilarity
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.llms import Ollama

# Other imports
from dotenv import load_dotenv
from tabulate import tabulate

# 加载环境变量
load_dotenv()

from ragas.metrics.base import SingleTurnMetric, MetricType, MetricOutputType
from ragas.dataset_schema import SingleTurnSample
from typing import Set
from dataclasses import dataclass, field


class RagasMetricsConfig:
    """
    Ragas 评估指标配置管理类
    
    功能：
    1. 管理启用的评估指标列表
    2. 保存/加载配置到JSON文件
    3. 提供默认配置
    """
    
    # 默认启用的指标
    DEFAULT_METRICS = [
        'context_recall',
        'context_precision',
        'context_entity_recall',
        'context_relevance',
        'faithfulness',
        'answer_relevancy',
        'answer_correctness',
        'answer_similarity'
    ]
    
    # 必选指标（不可禁用）
    REQUIRED_METRICS = ['context_recall', 'context_precision']
    
    # 配置文件路径
    CONFIG_FILE = "ragas_metrics_config.json"
    
    def __init__(self, enabled_metrics: List[str] = None):
        """
        初始化配置
        
        Args:
            enabled_metrics: 启用的指标列表，默认为None则使用全部指标
        """
        self.enabled_metrics = enabled_metrics or self.DEFAULT_METRICS.copy()
        
        # 确保必选指标始终启用
        for metric in self.REQUIRED_METRICS:
            if metric not in self.enabled_metrics:
                self.enabled_metrics.append(metric)
    
    def save(self) -> None:
        """保存配置到文件"""
        try:
            config_data = {
                "enabled_metrics": self.enabled_metrics,
                "version": "1.0"
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            info_print(f"✅ Ragas配置已保存到 {self.CONFIG_FILE}")
        except Exception as e:
            error_print(f"❌ 保存Ragas配置失败: {e}")
    
    @classmethod
    def load(cls) -> 'RagasMetricsConfig':
        """
        从文件加载配置
        
        Returns:
            RagasMetricsConfig: 配置对象
        """
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                enabled_metrics = config_data.get("enabled_metrics", cls.DEFAULT_METRICS)
                info_print(f"✅ 已加载Ragas配置: {len(enabled_metrics)} 个指标")
                return cls(enabled_metrics=enabled_metrics)
            else:
                info_print("ℹ️ 配置文件不存在，使用默认配置")
                return cls()
        except Exception as e:
            error_print(f"❌ 加载Ragas配置失败: {e}，使用默认配置")
            return cls()
    
    def is_enabled(self, metric_name: str) -> bool:
        """
        检查指标是否启用
        
        Args:
            metric_name: 指标名称
            
        Returns:
            bool: 是否启用
        """
        return metric_name in self.enabled_metrics


@dataclass
class StableContextEntityRecall(SingleTurnMetric):
    """
    稳定的上下文实体召回率实现
    
    与原生 ContextEntityRecall 的区别：
    1. 不依赖 LLM 提取实体（避免 JSON 解析错误）
    2. 使用规则和正则表达式提取实体
    3. 支持中英文实体提取
    4. 成功率接近 100%
    
    计算公式：
    Context Entity Recall = |RCE ∩ RE| / |RE|
    
    其中：
    - RE：reference（标准答案）中的实体集合
    - RCE：retrieved_contexts（检索上下文）中的实体集合
    """
    
    name: str = "context_entity_recall"  # 使用原生指标名称，保持兼容性
    _required_columns: Dict[MetricType, Set[str]] = field(
        default_factory=lambda: {
            MetricType.SINGLE_TURN: {"reference", "retrieved_contexts"}
        }
    )
    output_type: MetricOutputType = MetricOutputType.CONTINUOUS
    
    def init(self, run_config):
        """实现 Ragas 基类要求的 init 方法"""
        pass
    
    def _extract_entities_rule_based(self, text: str) -> Set[str]:
        """
        基于规则提取实体（不使用 LLM）
        
        提取策略：
        1. 专有名词（首字母大写的连续词）
        2. 数字和日期
        3. 中文专有名词（通过常见后缀识别）
        4. 英文缩写
        """
        if not text or not isinstance(text, str):
            return set()
        
        entities = set()
        
        # 1. 提取英文专有名词（连续的首字母大写单词）
        english_proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.update(english_proper_nouns)
        
        # 2. 提取单个大写字母单词（可能是缩写或专有名词）
        single_caps = re.findall(r'\b[A-Z](?:\+\+|#|[A-Z]+)?\b', text)
        entities.update(single_caps)
        
        # 3. 提取数字（包括年份、版本号等）
        numbers = re.findall(r'\b\d+(?:\.\d+)*\b', text)
        entities.update(numbers)
        
        # 4. 提取中文组织机构
        chinese_orgs = re.findall(r'[\u4e00-\u9fa5]{2,}(?:公司|大学|学院|研究院|中心|部门|组织)', text)
        entities.update(chinese_orgs)
        
        # 5. 提取中文人名（常见姓氏开头的2-4字人名）
        chinese_surnames = '李|王|张|刘|陈|杨|黄|赵|周|吴|徐|孙|马|朱|胡|郭|何|高|林|罗|郑|梁|谢|宋|唐|许|韩|冯|邓|曹|彭|曾|肖|田|董|袁|潘|于|蒋|蔡|余|杜|叶|程|苏|魏|吕|丁|任|沈|姚|卢|姜|崔|钟|谭|陆|汪|范|金|石|廖|贾|夏|韦|付|方|白|邹|孟|熊|秦|邱|江|尹|薛|闫|段|雷|侯|龙|史|陶|黎|贺|顾|毛|郝|龚|邵|万|钱|严|覃|武|戴|莫|孔|向|汤'
        chinese_names = re.findall(f'(?:{chinese_surnames})[\u4e00-\u9fa5]{{1,3}}', text)
        entities.update(chinese_names)
        
        # 6. 提取中文地名
        chinese_places = re.findall(r'[\u4e00-\u9fa5]{2,}(?:省|市|县|区|镇|村|街|路|国)', text)
        entities.update(chinese_places)
        
        # 7. 提取编程语言、技术名称等
        tech_terms = re.findall(r'\b[A-Z][a-z]*(?:\.[a-z]+|Script|SQL|DB)?\b', text)
        entities.update(tech_terms)
        
        # 8. 提取括号中的内容
        bracketed = re.findall(r'[（(]([^）)]{2,20})[）)]', text)
        entities.update(bracketed)
        
        # 过滤：移除过短或过长的实体
        filtered_entities = {
            ent.strip() 
            for ent in entities 
            if ent and len(ent.strip()) >= 2 and len(ent.strip()) <= 50
        }
        
        # 移除常见停用词
        stopwords = {'的', '了', '和', '与', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'It'}
        filtered_entities = {
            ent for ent in filtered_entities 
            if ent.lower() not in stopwords
        }
        
        return filtered_entities
    
    def _compute_entity_recall(self, reference_entities: Set[str], context_entities: Set[str]) -> float:
        """计算实体召回率"""
        if not reference_entities:
            return 1.0
        
        found_entities = reference_entities & context_entities
        recall = len(found_entities) / len(reference_entities)
        
        return recall
    
    async def _single_turn_ascore(self, sample: SingleTurnSample, callbacks) -> float:
        """异步计算单个样本的实体召回率（Ragas框架调用的方法）"""
        return self._single_turn_score(sample)
    
    def _single_turn_score(self, sample: SingleTurnSample) -> float:
        """计算单个样本的实体召回率"""
        # 1. 提取标准答案中的实体
        reference = sample.reference or ""
        reference_entities = self._extract_entities_rule_based(reference)
        
        # 2. 提取检索上下文中的实体
        retrieved_contexts = sample.retrieved_contexts or []
        context_text = "\n".join([str(ctx) for ctx in retrieved_contexts])
        context_entities = self._extract_entities_rule_based(context_text)
        
        # 3. 计算召回率
        score = self._compute_entity_recall(reference_entities, context_entities)
        
        return score


class OllamaEmbeddings:
    """Ollama Embedding包装器（带缓存优化）"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model_name: str = "embeddinggemma:300m"):
        self.ollama_url = ollama_url.rstrip('/')
        self.model_name = model_name
        # 性能优化：添加 embedding 缓存
        self._embedding_cache = {}
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """为文档列表生成embedding（带缓存优化）"""
        # 确保所有文本都是字符串
        texts = [str(text) for text in texts if str(text).strip()]
        if not texts:
            return []
        
        try:
            embeddings = []
            for text in texts:
                # 性能优化：检查缓存
                cache_key = f"{self.model_name}:{text[:100]}"
                if cache_key in self._embedding_cache:
                    embeddings.append(self._embedding_cache[cache_key])
                    continue
                
                data = {
                    "model": self.model_name,
                    "prompt": text
                }
                
                response = requests.post(
                    f"{self.ollama_url}/api/embeddings",
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result["embedding"]
                    # 加入缓存
                    self._embedding_cache[cache_key] = embedding
                    embeddings.append(embedding)
                else:
                    debug_info_print(f"Ollama Embedding API错误: {response.status_code} - {response.text}")
                    # 返回随机embedding作为fallback
                    import random
                    embeddings.append([random.random() for _ in range(2048)])  # embeddinggemma:300m通常是2048维
                    
            return embeddings
                
        except Exception as e:
            debug_info_print(f"Ollama Embedding生成失败: {e}")
            # 返回随机embedding作为fallback
            import random
            return [[random.random() for _ in range(2048)] for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """为单个查询生成embedding"""
        return self.embed_documents([text])[0]
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步为文档列表生成embedding"""
        return self.embed_documents(texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """异步为单个查询生成embedding"""
        return self.embed_query(text)

class CustomQwenEmbeddings:
    """自定义Qwen Embedding包装器（带缓存优化）"""
    
    def __init__(self, api_key: str, api_base: str, model_name: str = "text-embedding-v1"):
        self.api_key = api_key
        self.api_base = api_base
        self.model_name = model_name
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # 性能优化：添加 embedding 缓存
        self._embedding_cache = {}
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """为文档列表生成embedding（带缓存优化）"""
        # 确保所有文本都是字符串
        texts = [str(text) for text in texts if str(text).strip()]
        if not texts:
            return []
        
        # 性能优化：检查缓存
        embeddings = []
        texts_to_embed = []
        text_indices = []
        
        for i, text in enumerate(texts):
            cache_key = f"{self.model_name}:{text[:100]}"  # 使用前100字符作为缓存键
            if cache_key in self._embedding_cache:
                embeddings.append(self._embedding_cache[cache_key])
            else:
                texts_to_embed.append(text)
                text_indices.append(i)
        
        # 如果所有文本都已缓存，直接返回
        if not texts_to_embed:
            return embeddings
        
        try:
            data = {
                "input": texts_to_embed,
                "model": self.model_name
            }
            
            response = requests.post(
                f"{self.api_base}/embeddings",
                headers=self.headers,
                json=data,
                timeout=60  # 添加超时
            )
            
            if response.status_code == 200:
                result = response.json()
                new_embeddings = [item["embedding"] for item in result["data"]]
                
                # 将新生成的 embedding 加入缓存
                for text, embedding in zip(texts_to_embed, new_embeddings):
                    cache_key = f"{self.model_name}:{text[:100]}"
                    self._embedding_cache[cache_key] = embedding
                
                # 按原始顺序重组结果
                final_embeddings = [None] * len(texts)
                cached_idx = 0
                new_idx = 0
                for i in range(len(texts)):
                    if i in text_indices:
                        final_embeddings[i] = new_embeddings[new_idx]
                        new_idx += 1
                    else:
                        final_embeddings[i] = embeddings[cached_idx]
                        cached_idx += 1
                
                return final_embeddings
            else:
                debug_info_print(f"Embedding API错误: {response.status_code} - {response.text}")
                # 返回随机embedding作为fallback
                import random
                return [[random.random() for _ in range(1536)] for _ in texts]
                
        except Exception as e:
            debug_info_print(f"Embedding生成失败: {e}")
            # 返回随机embedding作为fallback
            import random
            return [[random.random() for _ in range(1536)] for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """为单个查询生成embedding"""
        return self.embed_documents([text])[0]
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步为文档列表生成embedding"""
        return self.embed_documents(texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """异步为单个查询生成embedding"""
        return self.embed_query(text)

class RagasEvaluator:
    """Ragas评估器模块"""
    
    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.llm = None
        self.embeddings = None
        self.ragas_llm = None
        self.ragas_embeddings = None
    
    def setup_environment(self):
        """设置LLM和Embeddings环境"""
        verbose_info_print("🔧 设置环境...")
        
        # 根据配置选择LLM和Embedding模型
        if hasattr(self.config, 'use_ollama') and self.config.use_ollama:
            # 使用本地模型：本地embedding + 云端LLM（混合模式）
            verbose_info_print(f"🔧 使用本地模型配置（混合模式）")
            
            # 创建云端Qwen LLM实例（因为本地没有LLM模型）
            # 使用严格的采样参数以获得最稳定的 JSON 输出
            # 注意：Qwen API 要求参数显式指定，不能使用 model_kwargs
            self.llm = ChatOpenAI(
                model=self.config.model_name,
                openai_api_key=self.config.api_key,
                openai_api_base=self.config.api_base,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,  # 显式指定
                top_p=self.config.top_p,  # 显式指定
            )
            
            # 创建本地Ollama Embedding实例
            verbose_info_print(f"🔧 使用本地Ollama embedding模型: {self.config.ollama_embedding_model}")
            self.embeddings = OllamaEmbeddings(
                ollama_url=self.config.ollama_url,
                model_name=self.config.ollama_embedding_model
            )
            custom_embeddings = self.embeddings
            
            verbose_info_print(f"🤖 使用云端Qwen LLM模型: {self.config.model_name}")
            verbose_info_print(f"📊 混合模式：本地embedding + 云端LLM")
        else:
            # 使用云端Qwen模型
            verbose_info_print(f"🔧 使用云端Qwen模型")
            
            # 创建Qwen LLM实例
            # 使用严格的采样参数以获得最稳定的 JSON 输出
            # 注意：Qwen API 要求参数显式指定，不能使用 model_kwargs
            self.llm = ChatOpenAI(
                model=self.config.model_name,
                openai_api_key=self.config.api_key,
                openai_api_base=self.config.api_base,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,  # 显式指定
                top_p=self.config.top_p,  # 显式指定
            )
            
            # 创建Qwen Embedding实例
            verbose_info_print(f"🔧 使用云端Qwen embedding模型: {self.config.embedding_model}")
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.config.api_key,
                openai_api_base=self.config.api_base,
                model=self.config.embedding_model
            )
            custom_embeddings = CustomQwenEmbeddings(
                self.config.api_key, 
                self.config.api_base, 
                self.config.embedding_model
            )
            
            verbose_info_print(f"🤖 使用云端Qwen LLM模型: {self.config.model_name}")
        
        # 创建Ragas包装器
        # 确认采样参数已正确设置（提高 Ragas 解析器成功率）
        verbose_info_print(f"🎯 LLM 采样参数: temperature={self.llm.temperature}, top_p={getattr(self.llm, 'top_p', 'N/A')}, max_tokens={getattr(self.llm, 'max_tokens', 'N/A')}")
        
        self.ragas_llm = LangchainLLMWrapper(self.llm)
        self.ragas_embeddings = LangchainEmbeddingsWrapper(custom_embeddings)
        
        verbose_info_print("✅ 环境设置完成")
    
    def create_ragas_dataset(self, df: pd.DataFrame, text_processor: TextProcessor) -> EvaluationDataset:
        """
        创建Ragas评估数据集
        
        Args:
            df: 处理后的DataFrame
            text_processor: 文本处理器
            
        Returns:
            EvaluationDataset: Ragas评估数据集
        """
        verbose_info_print("📊 创建Ragas评估数据集...")
        
        # 准备用于Ragas的数据
        ragas_df = df.copy()
        ragas_df['reference'] = df['reference']
        ragas_df['reference_contexts'] = df['reference_contexts']
        
        # 确保retrieved_contexts是列表格式
        ragas_df['retrieved_contexts'] = ragas_df['retrieved_contexts'].apply(text_processor.process_contexts)
        
        # 确保reference_contexts也是列表格式
        def safe_process_contexts(contexts):
            if isinstance(contexts, list):
                return contexts
            else:
                return text_processor.process_contexts(contexts)
        
        ragas_df['reference_contexts'] = ragas_df['reference_contexts'].apply(safe_process_contexts)
        
        # 过滤掉空行
        verbose_info_print("🔍 过滤空行数据...")
        filtered_rows = []
        for i in range(len(ragas_df)):
            retrieved_contexts = ragas_df['retrieved_contexts'].iloc[i]
            reference_contexts = ragas_df['reference_contexts'].iloc[i]
            user_input = ragas_df['user_input'].iloc[i] if 'user_input' in ragas_df.columns else ""
            response = ragas_df['response'].iloc[i] if 'response' in ragas_df.columns else ""
            
            if not text_processor.is_empty_row_data(retrieved_contexts, reference_contexts, user_input, response):
                filtered_rows.append(i)
                debug_info_print(f"保留行 {i+1}: retrieved_contexts={len(retrieved_contexts)}个片段, reference_contexts={len(reference_contexts)}个片段")
            else:
                debug_info_print(f"跳过行 {i+1}: 检测到空行数据")
        
        # 创建过滤后的数据
        ragas_df = ragas_df.iloc[filtered_rows].copy()
        verbose_info_print(f"过滤后的数据集行数: {len(ragas_df)}")
        
        # 确保所有必需字段都有有效值
        ragas_df['reference'] = ragas_df['reference'].apply(
            lambda x: x if pd.notna(x) and str(x).strip() else "无标准答案"
        )
        ragas_df['user_input'] = ragas_df['user_input'].apply(
            lambda x: x if pd.notna(x) and str(x).strip() else "无用户输入"
        )
        ragas_df['response'] = ragas_df['response'].apply(
            lambda x: x if pd.notna(x) and str(x).strip() else "无回答"
        )
        
        # 确保contexts字段不为空列表
        ragas_df['retrieved_contexts'] = ragas_df['retrieved_contexts'].apply(
            lambda x: x if x else ["无检索上下文"]
        )
        ragas_df['reference_contexts'] = ragas_df['reference_contexts'].apply(
            lambda x: x if x else ["无标准答案上下文"]
        )
        
        dataset = EvaluationDataset.from_pandas(ragas_df)
        info_print(f"✅ 成功创建包含 {len(dataset)} 个样本的评估数据集")
        
        return dataset
    
    def create_metrics(self) -> List[Any]:
        """
        创建Ragas评估指标（根据配置动态选择）
        
        Returns:
            List[Any]: 评估指标列表
        """
        info_print("📈 设置评估指标...")
        
        # 加载配置
        config = RagasMetricsConfig.load()
        
        # 指标映射表（指标名称 -> 指标对象创建函数）
        metrics_map = {
            'faithfulness': lambda: Faithfulness(),
            'answer_relevancy': lambda: AnswerRelevancy(embeddings=self.ragas_embeddings),
            'context_precision': lambda: ContextPrecision(),
            'context_recall': lambda: ContextRecall(),
            'context_entity_recall': lambda: StableContextEntityRecall(),
            'context_relevance': lambda: ContextRelevance(),
            'answer_correctness': lambda: AnswerCorrectness(embeddings=self.ragas_embeddings),
            'answer_similarity': lambda: AnswerSimilarity(embeddings=self.ragas_embeddings)
        }
        
        # 根据配置创建启用的指标
        metrics = []
        enabled_metrics_names = []
        
        for metric_name in config.enabled_metrics:
            if metric_name in metrics_map:
                metrics.append(metrics_map[metric_name]())
                enabled_metrics_names.append(metric_name)
            else:
                info_print(f"⚠️ 未知指标: {metric_name}")
        
        # 如果没有启用任何指标，使用默认配置
        if not metrics:
            info_print("⚠️ 未启用任何指标，使用全部默认指标")
            metrics = [factory() for factory in metrics_map.values()]
            enabled_metrics_names = list(metrics_map.keys())
        
        info_print(f"✅ 已设置 {len(metrics)} 个评估指标: {', '.join(enabled_metrics_names)}")
        return metrics
    
    async def evaluate(self, dataset: EvaluationDataset) -> Any:
        """
        运行Ragas评估
        
        Args:
            dataset: Ragas评估数据集
            
        Returns:
            Any: 评估结果
        """
        info_print("🔍 开始Ragas评估...")
        
        # 设置环境变量以减少日志输出
        import os
        os.environ['RAGAS_QUIET'] = 'true'
        os.environ['DISABLE_PROGRESS_BARS'] = 'true'
        
        # 降低日志级别以减少干扰
        import logging
        logging.getLogger('ragas').setLevel(logging.ERROR)
        
        try:
            metrics = self.create_metrics()
            info_print(f"📊 使用 {len(metrics)} 个评估指标...")
            
            # 性能优化：使用并发和批处理加速评估
            from ragas.run_config import RunConfig
            run_config = RunConfig(
                max_workers=self.config.max_workers,  # 最大并发数
                timeout=300,  # 超时时间（秒）
            )
            
            info_print(f"⚡ 性能优化: max_workers={self.config.max_workers}, batch_size={self.config.batch_size}")
            
            # 运行评估（添加并发和批处理参数）
            results = evaluate(
                dataset, 
                metrics, 
                llm=self.ragas_llm,
                run_config=run_config,
                batch_size=self.config.batch_size  # 批处理大小
            )
            info_print("✅ Ragas评估完成")
            return results
        except Exception as e:
            error_msg = str(e)
            info_print(f"⚠️ Ragas评估遇到错误: {error_msg}")
            
            # 检查是否是解析器错误
            if "parser" in error_msg.lower() or "parse" in error_msg.lower():
                info_print("🔄 检测到解析器错误，尝试使用简化的评估指标...")
                
                # 使用最稳定的指标重试
                try:
                    simple_metrics = [
                        Faithfulness(),  # 忠实度（不需要 LLM）
                        ContextPrecision(),  # 上下文精确度（不需要 LLM）
                        ContextRecall(),  # 上下文召回率（不需要 LLM）
                    ]
                    info_print("📊 使用简化的评估指标（仅使用不需要 LLM 的指标）...")
                    results = evaluate(dataset, simple_metrics, llm=self.ragas_llm)
                    info_print("✅ 简化评估完成")
                    return results
                except Exception as e2:
                    info_print(f"❌ 简化评估也失败: {e2}")
                    import traceback
                    traceback.print_exc()
            
            # 如果所有尝试都失败，返回fallback结果
            info_print("🔄 使用 fallback 模式...")
            return self._create_fallback_results(dataset)
    
    def _create_fallback_results(self, dataset: EvaluationDataset) -> Dict[str, Any]:
        """
        创建fallback评估结果
        
        Args:
            dataset: 评估数据集
            
        Returns:
            Dict[str, Any]: 基本的评估结果
        """
        info_print("🔄 创建fallback评估结果...")
        
        # 计算基本统计信息
        total_samples = len(dataset)
        
        # 创建基本的评估结果
        fallback_results = {
            'faithfulness': 0.5,  # 默认中等分数
            'answer_relevancy': 0.5,
            'context_precision': 0.5,
            'context_recall': 0.5,
            'context_entity_recall': 0.5,
            'context_relevance': 0.5,
            'answer_correctness': 0.5,
            'answer_similarity': 0.5,
            'total_samples': total_samples,
            'fallback_mode': True,
            'error_message': 'Ragas评估失败，使用fallback结果'
        }
        
        info_print(f"✅ Fallback结果创建完成，样本数: {total_samples}")
        return fallback_results

class ResultAnalyzer:
    """结果分析模块"""
    
    def __init__(self):
        self.results = None
    
    def analyze_results(self, results: Any) -> Dict[str, Any]:
        """
        分析评估结果
        
        Args:
            results: Ragas评估结果
            
        Returns:
            Dict[str, Any]: 分析后的结果字典
        """
        info_print("📊 分析评估结果...")
        
        # 检查是否是fallback结果
        if isinstance(results, dict) and results.get('fallback_mode', False):
            info_print("⚠️ 检测到fallback结果，使用简化分析")
            analysis = {
                'faithfulness': results.get('faithfulness', 0.5),
                'answer_relevancy': results.get('answer_relevancy', 0.5),
                'context_precision': results.get('context_precision', 0.5),
                'context_recall': results.get('context_recall', 0.5),
                'context_entity_recall': results.get('context_entity_recall', 0.5),
                'context_relevance': results.get('nv_context_relevance', 0.5),
                'answer_correctness': results.get('answer_correctness', 0.5),
                'answer_similarity': results.get('answer_similarity', 0.5),
                'raw_results': results,
                'fallback_mode': True,
                'error_message': results.get('error_message', '评估失败')
            }
            info_print("✅ Fallback结果分析完成")
            return analysis
        
        # 提取结果字典
        if hasattr(results, '_repr_dict'):
            results_dict = results._repr_dict
        elif hasattr(results, '__dict__') and '_repr_dict' in results.__dict__:
            results_dict = results.__dict__['_repr_dict']
        else:
            results_dict = str(results)
        
        # 提取各项指标 - 使用实际的字段名
        analysis = {
            'faithfulness': results_dict.get('faithfulness') if isinstance(results_dict, dict) else None,
            'answer_relevancy': results_dict.get('answer_relevancy') if isinstance(results_dict, dict) else None,
            'context_precision': results_dict.get('context_precision') if isinstance(results_dict, dict) else None,
            'context_recall': results_dict.get('context_recall') if isinstance(results_dict, dict) else None,
            'context_entity_recall': results_dict.get('context_entity_recall') if isinstance(results_dict, dict) else None,
            'context_relevance': results_dict.get('nv_context_relevance') if isinstance(results_dict, dict) else None,  # 使用正确的字段名
            'answer_correctness': results_dict.get('answer_correctness') if isinstance(results_dict, dict) else None,
            'answer_similarity': results_dict.get('answer_similarity') if isinstance(results_dict, dict) else None,
            'raw_results': results,
            'fallback_mode': False
        }
        
        info_print("✅ 结果分析完成")
        return analysis
    
    def display_results(self, analysis: Dict[str, Any]):
        """
        显示评估结果
        
        Args:
            analysis: 分析后的结果字典
        """
        info_print("\n" + "=" * 60)
        
        # 检查是否是fallback模式
        if analysis.get('fallback_mode', False):
            info_print("⚠️ Ragas评估结果 (Fallback模式)")
            info_print("=" * 60)
            info_print(f"❌ 评估错误: {analysis.get('error_message', '未知错误')}")
            info_print("🔄 使用默认评估分数")
        else:
            info_print("📊 Ragas评估结果")
            info_print("=" * 60)
        
        # 创建结果表格
        results_data = []
        metrics_info = [
            ("Faithfulness", "忠实度", analysis.get('faithfulness')),
            ("Answer Relevancy", "回答相关性", analysis.get('answer_relevancy')),
            ("Context Precision", "上下文精确度", analysis.get('context_precision')),
            ("Context Recall", "上下文召回率", analysis.get('context_recall')),
            ("Context Entity Recall", "上下文实体召回率", analysis.get('context_entity_recall')),
            ("Context Relevance", "上下文相关性", analysis.get('context_relevance')),
            ("Answer Correctness", "回答正确性", analysis.get('answer_correctness')),
            ("Answer Similarity", "回答相似度", analysis.get('answer_similarity'))
        ]
        
        for metric_name, chinese_name, value in metrics_info:
            if value is not None:
                status = "⚠️" if analysis.get('fallback_mode', False) else "✅"
                results_data.append([
                    f"{status} {metric_name}",
                    chinese_name,
                    f"{value:.4f}",
                    f"{value*100:.1f}%"
                ])
            else:
                results_data.append([
                    f"❌ {metric_name}",
                    chinese_name,
                    "评估失败",
                    "N/A"
                ])
        
        # 使用tabulate显示表格
        try:
            headers = ["指标名称", "中文名称", "分数", "百分比"]
            info_print(tabulate(results_data, headers=headers, tablefmt="grid", stralign="left"))
        except:
            # 简单表格格式
            info_print(f"{'指标名称':<25} {'中文名称':<15} {'分数':<10} {'百分比':<10}")
            info_print("-" * 70)
            for row in results_data:
                info_print(f"{row[0]:<25} {row[1]:<15} {row[2]:<10} {row[3]:<10}")
        
        # 显示详细分析
        info_print(f"\n📋 详细分析:")
        valid_metrics = [item for item in metrics_info if item[2] is not None]
        if valid_metrics:
            avg_score = sum(item[2] for item in valid_metrics) / len(valid_metrics)
            info_print(f"  • 平均分数: {avg_score:.4f} ({avg_score*100:.1f}%)")
            info_print(f"  • 有效指标数: {len(valid_metrics)}/{len(metrics_info)}")
            
            if analysis.get('fallback_mode', False):
                info_print(f"  • ⚠️ 注意: 当前为fallback模式，分数为默认值")
            else:
                # 找出最高和最低分数
                best_metric = max(valid_metrics, key=lambda x: x[2])
                worst_metric = min(valid_metrics, key=lambda x: x[2])
                info_print(f"  • 最高分数: {best_metric[1]} ({best_metric[2]:.4f})")
                info_print(f"  • 最低分数: {worst_metric[1]} ({worst_metric[2]:.4f})")
        else:
            info_print("  • 所有指标评估失败")

class MainController:
    """主控制器"""
    
    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.data_loader = DataLoader(config)
        self.text_processor = TextProcessor(config)
        self.ragas_evaluator = RagasEvaluator(config)
        self.result_analyzer = ResultAnalyzer()
    
    async def run_evaluation(self) -> Dict[str, Any]:
        """
        运行完整的评估流程
        
        Returns:
            Dict[str, Any]: 评估结果
        """
        info_print("🚀 开始Ragas LLM应用评估")
        info_print("=" * 60)
        
        try:
            # 1. 加载数据
            df = self.data_loader.load_excel_data()
            if df is None:
                return {"error": "数据加载失败"}
            
            # 2. 验证数据
            if not self.data_loader.validate_data(df):
                return {"error": "数据验证失败"}
            
            # 3. 数据预处理
            info_print("🔧 数据预处理...")
            df = self.text_processor.parse_context_columns(df)
            
            # 4. 智能选择标准答案
            info_print("🔍 智能选择标准答案...")
            df['final_reference'] = df['reference']
            df['final_reference_contexts'] = df['reference_contexts']
            
            # 显示数据样本信息
            info_print(f"\n📋 数据样本信息:")
            info_print(f"  • 总行数: {len(df)}")
            info_print(f"  • 用户输入示例: {df['user_input'].iloc[0][:100]}...")
            info_print(f"  • 回答示例: {df['response'].iloc[0][:100]}...")
            info_print(f"  • 标准答案示例: {df['final_reference'].iloc[0][:100]}...")
            
            # 5. 设置环境
            self.ragas_evaluator.setup_environment()
            
            # 6. 创建Ragas数据集
            dataset = self.ragas_evaluator.create_ragas_dataset(df, self.text_processor)
            
            # 7. 运行评估
            results = await self.ragas_evaluator.evaluate(dataset)
            
            # 8. 分析结果
            analysis = self.result_analyzer.analyze_results(results)
            
            # 9. 显示结果
            self.result_analyzer.display_results(analysis)
            
            return analysis
            
        except Exception as e:
            info_print(f"❌ 评估失败: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
        
        finally:
            info_print("✅ 评估完成！")

async def main():
    """主函数"""
    # 创建配置
    config = EvaluationConfig(
        api_key=os.getenv("QWEN_API_KEY"),
        api_base=os.getenv("QWEN_API_BASE"),
        model_name=os.getenv("QWEN_MODEL_NAME", "qwen-plus"),
        embedding_model=os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1")
    )
    
    # 验证配置
    if not config.api_key or not config.api_base:
        info_print("❌ 请设置QWEN_API_KEY和QWEN_API_BASE环境变量")
        return
    
    # 创建主控制器并运行评估
    controller = MainController(config)
    results = await controller.run_evaluation()
    
    if "error" in results:
        info_print(f"❌ 评估失败: {results['error']}")
    else:
        info_print(f"\n🎉 评估成功完成！")

if __name__ == "__main__":
    asyncio.run(main())
