"""
基于BM25算法的RAG评估系统
用于计算分块级别的召回率和准确率

功能：
1. BM25算法计算文本相似度
2. 计算Precision和Recall指标
3. 分析不相关和未召回的分块
4. 相关性评分系统
"""

import os
import json
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Optional, Any, Tuple
from config import debug_print, verbose_print, info_print, error_print, QUIET_MODE
from collections import Counter
import math
from read_chuck import EvaluationConfig, DataLoader, TextProcessor

class BM25:
    """BM25算法实现"""
    
    def __init__(self, k1=1.5, b=0.75):
        """
        初始化BM25算法
        
        Args:
            k1: 控制词频饱和度的参数
            b: 控制文档长度归一化的参数
        """
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.corpus_size = 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.avgdl = 0
    
    def fit(self, corpus: List[str]):
        """
        训练BM25模型
        
        Args:
            corpus: 文档语料库
        """
        self.corpus = [self._tokenize(doc) for doc in corpus]
        self.corpus_size = len(self.corpus)
        
        # 计算文档长度
        self.doc_len = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0
        
        # 计算词频和文档频率
        self.doc_freqs = []
        df = {}
        
        for doc in self.corpus:
            frequencies = Counter(doc)
            self.doc_freqs.append(frequencies)
            
            for word in frequencies:
                df[word] = df.get(word, 0) + 1
        
        # 计算IDF
        for word, freq in df.items():
            self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5))
    
    def _tokenize(self, text: str) -> List[str]:
        """
        支持中文的分词函数
        
        Args:
            text: 输入文本
            
        Returns:
            List[str]: 分词结果
        """
        if not text:
            return []
        
        # 转换为小写
        text = text.lower()
        
        # 更细粒度的中文分词
        # 1. 提取中文字符（包括单字）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        
        # 2. 提取英文单词
        english_words = re.findall(r'[a-zA-Z]+', text)
        
        # 3. 提取数字
        numbers = re.findall(r'\d+', text)
        
        # 4. 提取书名（《》中的内容）
        book_titles = re.findall(r'《([^》]+)》', text)
        
        # 5. 提取常见的动作词和关键词
        keywords = []
        action_words = ['分享', '推荐', '读了', '读了本', '最近读了', '书籍', '书', '读书', '阅读', '读后感']
        for word in action_words:
            if word in text:
                keywords.append(word)
        
        # 合并所有token
        tokens = chinese_chars + english_words + numbers + book_titles + keywords
        
        # 去重并过滤掉长度小于1的token
        tokens = list(set([token for token in tokens if len(token) >= 1]))
        
        return tokens
    
    def score(self, query: str, doc_index: int) -> float:
        """
        计算查询与文档的BM25分数
        
        Args:
            query: 查询文本
            doc_index: 文档索引
            
        Returns:
            float: BM25分数
        """
        if doc_index >= len(self.corpus):
            return 0.0
        
        query_tokens = self._tokenize(query)
        doc_freqs = self.doc_freqs[doc_index]
        doc_len = self.doc_len[doc_index]
        
        score = 0.0
        for token in query_tokens:
            if token in doc_freqs:
                tf = doc_freqs[token]
                idf = self.idf.get(token, 0)
                
                # BM25公式
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
                score += idf * (numerator / denominator)
        
        return score
    
    def get_scores(self, query: str) -> List[float]:
        """
        获取查询对所有文档的分数
        
        Args:
            query: 查询文本
            
        Returns:
            List[float]: 所有文档的分数
        """
        return [self.score(query, i) for i in range(self.corpus_size)]

class BM25Evaluator:
    """基于BM25的RAG评估器"""
    
    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.data_loader = DataLoader(config)
        self.text_processor = TextProcessor(config)
        self.bm25 = BM25()
        
        # 相关性阈值
        self.relevance_thresholds = {
            0.0000: "完全不相关",
            0.2500: "少量相关，但信息不完整", 
            0.5000: "部分相关，有一定价值",
            0.7500: "大部分相关，基本满足需求",
            1.0000: "完全相关，完美匹配"
        }
    
    def load_and_process_data(self) -> Optional[pd.DataFrame]:
        """
        加载和处理数据
        
        Returns:
            pd.DataFrame: 处理后的数据
        """
        info_print("📖 加载数据...")
        
        # 加载数据
        df = self.data_loader.load_excel_data()
        if df is None:
            return None
        
        # 验证数据
        if not self.data_loader.validate_data(df):
            return None
        
        # 处理上下文列（避免重复处理）
        # 检查是否需要处理：如果第一个元素是字符串，则需要处理
        first_retrieved = df['retrieved_contexts'].iloc[0]
        if isinstance(first_retrieved, str):
            df = self.text_processor.parse_context_columns(df)
        
        info_print(f"✅ 成功加载 {len(df)} 行数据")
        return df
    
    def calculate_relevance_score(self, retrieved_chunk: str, reference_chunk: str) -> float:
        """
        计算检索分块与参考分块的相关性分数
        使用智能相似度算法替代BM25，确保准确性
        
        Args:
            retrieved_chunk: 检索到的分块
            reference_chunk: 参考分块
            
        Returns:
            float: 相关性分数 (0-1)
        """
        if not retrieved_chunk or not reference_chunk:
            return 0.0
        
        # 使用智能相似度算法（与Ragas评估明细保持一致）
        from app import calculate_text_similarity
        similarity = calculate_text_similarity(retrieved_chunk, reference_chunk)
        
        return similarity
    
    def _check_semantic_containment(self, retrieved_chunk: str, reference_chunk: str, threshold: float) -> bool:
        """
        检查是否是语义包含情况
        
        Args:
            retrieved_chunk: 检索到的分块
            reference_chunk: 参考分块
            threshold: 语义包含阈值
            
        Returns:
            bool: 是否是语义包含
        """
        if not retrieved_chunk or not reference_chunk:
            return False
        
        # 文本预处理
        import re
        
        def clean_text(text):
            # 移除标点符号和特殊字符，保留中文、英文、数字
            cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
            # 移除多余空格
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned.lower()
        
        clean_retrieved = clean_text(retrieved_chunk)
        clean_reference = clean_text(reference_chunk)
        
        # 分词
        words_retrieved = set(clean_retrieved.split())
        words_reference = set(clean_reference.split())
        
        if len(words_retrieved) == 0 or len(words_reference) == 0:
            return False
        
        # 计算语义包含度
        if len(words_retrieved) <= len(words_reference):
            # retrieved_chunk是较短的，计算在reference_chunk中的包含度
            contained_words = words_retrieved.intersection(words_reference)
            semantic_containment = len(contained_words) / len(words_retrieved)
        else:
            # reference_chunk是较短的，计算在retrieved_chunk中的包含度
            contained_words = words_reference.intersection(words_retrieved)
            semantic_containment = len(contained_words) / len(words_reference)
        
        return semantic_containment >= threshold
    
    def evaluate_precision_recall(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算Precision和Recall指标
        基于BM25算法判断检索分块与标准答案分块的语义一致性
        
        Args:
            df: 处理后的数据
            
        Returns:
            Dict[str, Any]: 评估结果
        """
        info_print("🔍 开始BM25评估...")
        info_print("📋 评估逻辑:")
        info_print("  • Precision = 完整含有相关信息的分块数（语义得分） / retrieved_contexts分块数")
        info_print("  • Recall = 完整含有相关信息的分块数（语义得分） / reference_contexts分块数")
        info_print("  • 完整含有相关信息的分块数 = 所有相关分块的语义相似度得分之和")
        similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
        info_print(f"  • 相关性判断: 检索分块与参考分块的语义相似度 > {similarity_threshold}")
        info_print()
        
        results = {
            'precision_scores': [],
            'recall_scores': [],
            'irrelevant_chunks': [],  # 不相关的检索分块
            'missed_chunks': [],      # 未召回的参考分块
            'relevant_chunks': [],    # 相关的检索分块
            'detailed_results': []
        }
        
        for idx, row in df.iterrows():
            info_print(f"处理第 {idx + 1}/{len(df)} 行...")
            
            user_input = str(row['user_input']) if pd.notna(row['user_input']) else ""
            retrieved_contexts = row['retrieved_contexts']
            reference_contexts = row['reference_contexts']
            
            if not retrieved_contexts or not reference_contexts:
                info_print(f"  跳过行 {idx + 1}: 缺少上下文数据")
                continue
            
            # 计算检索分块与参考分块的语义相似度矩阵
            similarity_matrix = []
            for retrieved_chunk in retrieved_contexts:
                chunk_similarities = []
                for reference_chunk in reference_contexts:
                    similarity = self.calculate_relevance_score(retrieved_chunk, reference_chunk)
                    chunk_similarities.append(similarity)
                similarity_matrix.append(chunk_similarities)
            
            # 找出每个检索分块的最佳匹配参考分块
            relevant_retrieved = []  # 被判定为相关的检索分块
            matched_references = set()  # 已被匹配的参考分块索引
            total_relevance_score = 0.0  # 总相关性得分
            
            for i, retrieved_chunk in enumerate(retrieved_contexts):
                max_similarity = max(similarity_matrix[i]) if similarity_matrix[i] else 0
                best_ref_idx = similarity_matrix[i].index(max_similarity) if similarity_matrix[i] else -1
                
                # 判断是否相关（从环境变量读取阈值）
                similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
                if max_similarity > similarity_threshold:
                    # 检查是否是语义包含情况
                    semantic_containment_threshold = float(os.getenv("SEMANTIC_CONTAINMENT_THRESHOLD", "0.9"))
                    is_semantic_containment = self._check_semantic_containment(retrieved_chunk, reference_contexts[best_ref_idx], semantic_containment_threshold)
                    
                    relevant_chunk_info = {
                        'retrieved_chunk': retrieved_chunk,
                        'reference_chunk': reference_contexts[best_ref_idx],
                        'relevance_score': max_similarity,
                        'row_index': idx,
                        'retrieved_idx': i,
                        'reference_idx': best_ref_idx,
                        'user_input': user_input,
                        'is_semantic_containment': is_semantic_containment,
                        'semantic_containment_threshold': semantic_containment_threshold
                    }
                    relevant_retrieved.append(relevant_chunk_info)
                    # 累加相关性得分
                    total_relevance_score += max_similarity
                    # 添加到results['relevant_chunks']中，与irrelevant_chunks保持一致
                    results['relevant_chunks'].append(relevant_chunk_info)
                    matched_references.add(best_ref_idx)
                else:
                    # 不相关的检索分块
                    results['irrelevant_chunks'].append({
                        'retrieved_chunk': retrieved_chunk,
                        'max_relevance': max_similarity,
                        'row_index': idx,
                        'user_input': user_input,
                        'retrieved_idx': i
                    })
            
            # 找出未被召回的参考分块
            # 未召回分块：reference_contexts中存在分块，在retrieved_contexts中的分块没有存在（即找不到相似度大于阈值的）
            for j, reference_chunk in enumerate(reference_contexts):
                # 找到该参考分块与所有检索分块的最大相似度
                max_similarity = 0
                best_retrieved_idx = -1
                for i in range(len(retrieved_contexts)):
                    if similarity_matrix[i][j] > max_similarity:
                        max_similarity = similarity_matrix[i][j]
                        best_retrieved_idx = i
                
                # 如果最大相似度小于等于阈值，认为是未召回分块
                if max_similarity <= similarity_threshold:
                    results['missed_chunks'].append({
                        'reference_chunk': reference_chunk,
                        'max_relevance': max_similarity,
                        'row_index': idx,
                        'user_input': user_input,
                        'reference_idx': j,
                        'best_retrieved_idx': best_retrieved_idx
                    })
            
            # 计算Precision和Recall
            # Precision = 完整含有相关信息的分块数（语义得分） / retrieved_contexts分块数
            # Recall = 完整含有相关信息的分块数（语义得分） / reference_contexts分块数
            precision = total_relevance_score / len(retrieved_contexts) if retrieved_contexts else 0
            recall = total_relevance_score / len(reference_contexts) if reference_contexts else 0
            
            results['precision_scores'].append(precision)
            results['recall_scores'].append(recall)
            
            # 详细结果
            results['detailed_results'].append({
                'row_index': idx,
                'user_input': user_input,
                'precision': precision,
                'recall': recall,
                'retrieved_count': len(retrieved_contexts),
                'reference_count': len(reference_contexts),
                'relevant_count': len(relevant_retrieved),
                'total_relevance_score': total_relevance_score,
                'matched_reference_count': len(matched_references),
                'relevant_chunks': relevant_retrieved,
                'similarity_matrix': similarity_matrix
            })
            
            info_print(f"  检索分块: {len(retrieved_contexts)}个, 参考分块: {len(reference_contexts)}个")
            info_print(f"  含有相关信息的分块: {len(relevant_retrieved)}个, 总语义得分: {total_relevance_score:.4f}, 召回分块: {len(matched_references)}个")
            info_print(f"  Precision: {precision:.4f}, Recall: {recall:.4f}")
        
        # 计算平均指标
        results['avg_precision'] = np.mean(results['precision_scores']) if results['precision_scores'] else 0
        results['avg_recall'] = np.mean(results['recall_scores']) if results['recall_scores'] else 0
        results['avg_f1'] = 2 * (results['avg_precision'] * results['avg_recall']) / (results['avg_precision'] + results['avg_recall']) if (results['avg_precision'] + results['avg_recall']) > 0 else 0
        
        info_print(f"\n✅ BM25评估完成")
        info_print(f"📊 平均Precision: {results['avg_precision']:.4f}")
        info_print(f"📊 平均Recall: {results['avg_recall']:.4f}")
        info_print(f"📊 平均F1: {results['avg_f1']:.4f}")
        
        return results
    
    def print_sample_analysis(self, results: Dict[str, Any]):
        """
        按样本打印不相关和未召回的分块分析
        
        Args:
            results: 评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📊 分块信息详细分析")
        info_print("=" * 80)
        
        # 按样本组织数据
        sample_data = {}
        
        # 组织不含有相关信息的分块
        for chunk_info in results['irrelevant_chunks']:
            row_idx = chunk_info['row_index']
            if row_idx not in sample_data:
                sample_data[row_idx] = {
                    'user_input': chunk_info['user_input'],
                    'irrelevant_chunks': [],
                    'missed_chunks': []
                }
            sample_data[row_idx]['irrelevant_chunks'].append(chunk_info)
        
        # 组织未召回分块
        for chunk_info in results['missed_chunks']:
            row_idx = chunk_info['row_index']
            if row_idx not in sample_data:
                sample_data[row_idx] = {
                    'user_input': chunk_info['user_input'],
                    'irrelevant_chunks': [],
                    'missed_chunks': []
                }
            sample_data[row_idx]['missed_chunks'].append(chunk_info)
        
        # 按样本打印
        for sample_idx, (row_idx, data) in enumerate(sample_data.items(), 1):
            info_print(f"\n样本{sample_idx} (行 {row_idx + 1}):")
            info_print(f"用户query: {data['user_input']}")
            info_print()
            
            # 打印不含有相关信息的分块
            if data['irrelevant_chunks']:
                info_print(f"1. 不含有相关信息的分块 ({len(data['irrelevant_chunks'])}个):")
                for i, chunk_info in enumerate(data['irrelevant_chunks'], 1):
                    info_print(f"   {i}. 检索分块: {chunk_info['retrieved_chunk'][:150]}...")
                    info_print(f"      相关性分数: {chunk_info['max_relevance']:.4f} ({self._get_relevance_level(chunk_info['max_relevance'])})")
                info_print()
            else:
                info_print("1. 不含有相关信息的分块: 无")
                info_print()
            
            # 打印未召回分块
            if data['missed_chunks']:
                info_print(f"2. 未召回分块 ({len(data['missed_chunks'])}个):")
                for i, chunk_info in enumerate(data['missed_chunks'], 1):
                    info_print(f"   {i}. 参考分块: {chunk_info['reference_chunk'][:150]}...")
                    info_print(f"      相关性分数: {chunk_info['max_relevance']:.4f} ({self._get_relevance_level(chunk_info['max_relevance'])})")
                info_print()
            else:
                info_print("2. 未召回分块: 无")
                info_print()
            
            info_print("-" * 60)
    
    def print_summary_metrics(self, results: Dict[str, Any]):
        """
        打印汇总信息
        
        Args:
            results: 评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📈 汇总信息")
        info_print("=" * 80)
        
        info_print("📋 评估指标定义:")
        info_print("  • Precision = 完整含有相关信息的分块数 / retrieved_contexts分块数")
        info_print("  • Recall = 完整含有相关信息的分块数 / reference_contexts分块数")
        similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
        info_print(f"  • 相关性判断: 检索分块与参考分块的语义相似度 > {similarity_threshold}")
        info_print()
        
        info_print("📊 评估结果:")
        info_print(f"1. Precision: {results['avg_precision']:.4f} ({results['avg_precision']*100:.1f}%)")
        info_print(f"2. Recall: {results['avg_recall']:.4f} ({results['avg_recall']*100:.1f}%)")
        info_print(f"3. F1分数: {results['avg_f1']:.4f} ({results['avg_f1']*100:.1f}%)")
        
        info_print(f"\n📊 统计信息:")
        info_print(f"  • 评估样本数: {len(results['precision_scores'])} 个")
        info_print(f"  • 不相关检索分块总数: {len(results['irrelevant_chunks'])} 个")
        info_print(f"  • 未召回参考分块总数: {len(results['missed_chunks'])} 个")
        
        # 相关性分布统计
        irrelevant_scores = [chunk['max_relevance'] for chunk in results['irrelevant_chunks']]
        missed_scores = [chunk['max_relevance'] for chunk in results['missed_chunks']]
        
        if irrelevant_scores:
            info_print(f"\n🚫 不相关检索分块相关性分布:")
            info_print(f"  • 平均分数: {np.mean(irrelevant_scores):.4f}")
            info_print(f"  • 最高分数: {np.max(irrelevant_scores):.4f}")
            info_print(f"  • 最低分数: {np.min(irrelevant_scores):.4f}")
        
        if missed_scores:
            info_print(f"\n❌ 未召回参考分块相关性分布:")
            info_print(f"  • 平均分数: {np.mean(missed_scores):.4f}")
            info_print(f"  • 最高分数: {np.max(missed_scores):.4f}")
            info_print(f"  • 最低分数: {np.min(missed_scores):.4f}")
    
    def _get_relevance_level(self, score: float) -> str:
        """
        根据分数获取相关性等级
        
        Args:
            score: 相关性分数
            
        Returns:
            str: 相关性等级描述
        """
        if score >= 1.0:
            return self.relevance_thresholds[1.0000]
        elif score >= 0.75:
            return self.relevance_thresholds[0.7500]
        elif score >= 0.5:
            return self.relevance_thresholds[0.5000]
        elif score >= 0.25:
            return self.relevance_thresholds[0.2500]
        else:
            return self.relevance_thresholds[0.0000]
    





    
    def print_evaluation_summary(self, results: Dict[str, Any]):
        """
        打印评估总结（已弃用，使用print_summary_metrics和print_sample_analysis替代）
        
        Args:
            results: 评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📊 BM25评估总结")
        info_print("=" * 80)
        
        info_print(f"📈 平均Precision: {results['avg_precision']:.4f} ({results['avg_precision']*100:.1f}%)")
        info_print(f"📈 平均Recall: {results['avg_recall']:.4f} ({results['avg_recall']*100:.1f}%)")
        info_print(f"📈 平均F1分数: {results['avg_f1']:.4f} ({results['avg_f1']*100:.1f}%)")
        
        info_print(f"\n📊 详细统计:")
        info_print(f"  • 不相关的检索分块: {len(results['irrelevant_chunks'])} 个")
        info_print(f"  • 未召回的参考分块: {len(results['missed_chunks'])} 个")
        info_print(f"  • 评估样本数: {len(results['precision_scores'])} 个")
    
    def run_evaluation(self) -> Dict[str, Any]:
        """
        运行完整的BM25评估
        
        Returns:
            Dict[str, Any]: 评估结果
        """
        info_print("🚀 开始BM25 RAG评估")
        info_print("=" * 60)
        
        try:
            # 1. 加载数据
            df = self.load_and_process_data()
            if df is None:
                return {"error": "数据加载失败"}
            
            # 2. 运行评估
            results = self.evaluate_precision_recall(df)
            
            # 3. 打印结果
            self.print_summary_metrics(results)
            self.print_sample_analysis(results)
            
            return results
            
        except Exception as e:
            info_print(f"❌ 评估失败: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

def main():
    """主函数"""
    # 创建配置
    config = EvaluationConfig(
        api_key=os.getenv("QWEN_API_KEY", "dummy_key"),
        api_base=os.getenv("QWEN_API_BASE", "dummy_base")
    )
    
    # 创建评估器并运行评估
    evaluator = BM25Evaluator(config)
    results = evaluator.run_evaluation()
    
    if "error" in results:
        info_print(f"❌ 评估失败: {results['error']}")
    else:
        info_print(f"\n🎉 BM25评估成功完成！")

def find_relevant_chunks(query: str, chunks: List[str], max_chunks: int = 10, threshold: float = -10.0) -> List[Tuple[str, float]]:
    """
    使用BM25算法查找与查询相关的分块
    
    Args:
        query: 查询文本
        chunks: 分块列表
        max_chunks: 最大返回分块数
        threshold: 相关性阈值
        
    Returns:
        List[Tuple[str, float]]: 相关分块列表，每个元素为(分块内容, 相关性分数)
    """
    if not chunks or not query:
        return []
    
    # 创建BM25实例
    bm25 = BM25()
    bm25.fit(chunks)
    
    # 计算所有分块的BM25分数
    scores = bm25.get_scores(query)
    
    # 创建(分块, 分数)对并排序
    chunk_scores = [(chunks[i], scores[i]) for i in range(len(chunks))]
    chunk_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 过滤掉低于阈值的分块
    relevant_chunks = [(chunk, score) for chunk, score in chunk_scores if score > threshold]
    
    # 返回前max_chunks个最相关的分块
    return relevant_chunks[:max_chunks]

def is_chunk_relevant(query: str, chunk: str, threshold: float = -10.0) -> Tuple[bool, float]:
    """
    判断单个分块是否与查询相关
    
    Args:
        query: 查询文本
        chunk: 分块内容
        threshold: 相关性阈值
        
    Returns:
        Tuple[bool, float]: (是否相关, 相关性分数)
    """
    if not chunk or not query:
        return False, 0.0
    
    # 创建BM25实例
    bm25 = BM25()
    bm25.fit([chunk])
    
    # 计算BM25分数
    score = bm25.score(query, 0)
    
    return score > threshold, score

if __name__ == "__main__":
    main()
