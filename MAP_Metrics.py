"""
RAG评估指标MAP (Mean Average Precision) 实现
用于计算检索系统中相关分块的平均精度

功能：
1. 加载RAG样本数据和分块数据
2. 使用BM25算法判断分块相关性
3. 计算每个样本的平均精度(AP)
4. 计算MAP指标
5. 按样本分组显示计算过程
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from config import debug_print, verbose_print, info_print, error_print, QUIET_MODE
from read_chuck import EvaluationConfig, DataLoader, TextProcessor
from BM25_evaluate import BM25Evaluator, BM25, find_relevant_chunks, is_chunk_relevant


class MAPEvaluator:
    """MAP (Mean Average Precision) 评估器"""
    
    def __init__(self, config: EvaluationConfig):
        """
        初始化MAP评估器
        
        Args:
            config: 评估配置
        """
        self.config = config
        self.data_loader = DataLoader(config)
        self.text_processor = TextProcessor(config)
        self.bm25_evaluator = BM25Evaluator(config)
        
        # 相关性阈值
        self.relevance_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
        
        info_print("🔧 MAP评估器初始化完成")
        info_print(f"📊 相关性阈值: {self.relevance_threshold}")
    
    def load_and_process_data(self) -> Optional[pd.DataFrame]:
        """
        加载和处理RAG样本数据
        
        Returns:
            pd.DataFrame: 处理后的数据，失败时返回None
        """
        info_print("📖 加载RAG样本数据...")
        
        # 使用BM25Evaluator的数据加载功能
        df = self.bm25_evaluator.load_and_process_data()
        if df is None:
            error_print("❌ 数据加载失败")
            return None
        
        info_print(f"✅ 成功加载 {len(df)} 个RAG样本")
        return df
    
    def get_relevant_chunks_for_query(self, query: str, reference_contexts: List[str]) -> List[str]:
        """
        获取与查询相关的参考分块
        
        Args:
            query: 用户查询
            reference_contexts: 参考分块列表
            
        Returns:
            List[str]: 相关分块列表
        """
        if not query or not reference_contexts:
            return []
        
        relevant_chunks = []
        for chunk in reference_contexts:
            # 使用BM25算法判断相关性
            is_relevant, score = is_chunk_relevant(query, chunk, threshold=-10.0)  # 使用较低的BM25阈值
            if is_relevant:
                relevant_chunks.append(chunk)
        
        return relevant_chunks
    
    def get_ranked_chunks_for_query(self, query: str, retrieved_contexts: List[str]) -> List[Tuple[str, float]]:
        """
        获取按相关性排序的检索分块
        
        Args:
            query: 用户查询
            retrieved_contexts: 检索分块列表
            
        Returns:
            List[Tuple[str, float]]: 排序后的分块列表，每个元素为(分块内容, 相关性分数)
        """
        if not query or not retrieved_contexts:
            return []
        
        # 使用BM25算法对检索分块进行排序
        ranked_chunks = find_relevant_chunks(
            query=query,
            chunks=retrieved_contexts,
            max_chunks=len(retrieved_contexts),
            threshold=-10.0  # 使用较低的阈值以包含所有分块
        )
        
        return ranked_chunks
    
    def calculate_average_precision(self, query: str, retrieved_contexts: List[str], 
                                  reference_contexts: List[str]) -> Tuple[float, Dict[str, Any]]:
        """
        计算单个查询的平均精度(AP)
        
        Args:
            query: 用户查询
            retrieved_contexts: 检索分块列表
            reference_contexts: 参考分块列表
            
        Returns:
            Tuple[float, Dict[str, Any]]: (平均精度, 详细计算过程)
        """
        # 获取相关分块
        relevant_chunks = self.get_relevant_chunks_for_query(query, reference_contexts)
        
        if not relevant_chunks:
            # 如果没有相关分块，返回0
            debug_print(f"  查询: {query[:50]}... - 无相关分块")
            return 0.0, {
                'relevant_chunks': [],
                'precision_at_k': [],
                'relevant_positions': [],
                'calculation_steps': [],
                'chunk_relevance_scores': [],
                'total_relevant': 0,
                'total_retrieved': len(retrieved_contexts) if retrieved_contexts else 0
            }
        
        if not retrieved_contexts:
            # 如果没有检索分块，返回0
            debug_print(f"  查询: {query[:50]}... - 无检索分块")
            return 0.0, {
                'relevant_chunks': relevant_chunks,
                'precision_at_k': [],
                'relevant_positions': [],
                'calculation_steps': [],
                'chunk_relevance_scores': [],
                'total_relevant': 0,
                'total_retrieved': 0
            }
        
        # 计算每个检索分块与相关分块的相关性
        chunk_relevance_scores = []
        for i, retrieved_chunk in enumerate(retrieved_contexts):
            max_relevance = 0.0
            best_ref_chunk = ""
            for ref_chunk in relevant_chunks:
                relevance = self.bm25_evaluator.calculate_relevance_score(retrieved_chunk, ref_chunk)
                if relevance > max_relevance:
                    max_relevance = relevance
                    best_ref_chunk = ref_chunk
            
            # 位置 = 总长度 - 原始index（倒序）
            position = len(retrieved_contexts) - i
            
            chunk_relevance_scores.append({
                'position': position,
                'chunk': retrieved_chunk,
                'relevance_score': max_relevance,
                'is_relevant': max_relevance > self.relevance_threshold,
                'best_ref_chunk': best_ref_chunk
            })
        
        # 计算平均精度
        relevant_count = 0
        precision_sum = 0.0
        precision_at_k = []
        relevant_positions = []
        calculation_steps = []
        
        for i, chunk_info in enumerate(chunk_relevance_scores):
            if chunk_info['is_relevant']:
                relevant_count += 1
                # 使用倒序位置计算精度
                position = chunk_info['position']
                precision_at_i = relevant_count / position
                precision_sum += precision_at_i
                precision_at_k.append(precision_at_i)
                relevant_positions.append(position)
                
                calculation_steps.append({
                    'position': position,
                    'precision': precision_at_i,
                    'relevant_count': relevant_count,
                    'total_retrieved': position
                })
        
        # 计算平均精度
        if relevant_count > 0:
            average_precision = precision_sum / relevant_count
        else:
            average_precision = 0.0
        
        return average_precision, {
            'relevant_chunks': relevant_chunks,
            'precision_at_k': precision_at_k,
            'relevant_positions': relevant_positions,
            'calculation_steps': calculation_steps,
            'chunk_relevance_scores': chunk_relevance_scores,
            'total_relevant': relevant_count,
            'total_retrieved': len(retrieved_contexts)
        }
    
    def evaluate_map(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算MAP指标
        
        Args:
            df: 处理后的数据
            
        Returns:
            Dict[str, Any]: MAP评估结果
        """
        info_print("🔍 开始MAP评估...")
        info_print("📋 评估逻辑:")
        info_print("  • MAP = 所有查询的平均精度(AP)的平均值")
        info_print("  • AP = 每个相关分块被检索到时的精度值的平均值")
        info_print("  • 精度@k = 前k个检索结果中相关分块的数量 / k")
        info_print(f"  • 相关性判断: 检索分块与参考分块的语义相似度 > {self.relevance_threshold}")
        info_print()
        
        results = {
            'average_precisions': [],
            'detailed_results': [],
            'total_queries': 0,
            'queries_with_relevant_chunks': 0,
            'queries_without_relevant_chunks': 0
        }
        
        # 计算所有样本的MAP
        for idx, row in df.iterrows():
            # 安全获取字符串值
            user_input_val = row.get('user_input', '')
            user_input = str(user_input_val) if user_input_val is not None and not pd.isna(user_input_val) else ""
            
            # 确保类型转换：从pandas Series转换为List[str]
            retrieved_contexts_raw = row['retrieved_contexts']
            reference_contexts_raw = row['reference_contexts']
            
            retrieved_contexts = retrieved_contexts_raw if isinstance(retrieved_contexts_raw, list) else list(retrieved_contexts_raw) if retrieved_contexts_raw is not None else []
            reference_contexts = reference_contexts_raw if isinstance(reference_contexts_raw, list) else list(reference_contexts_raw) if reference_contexts_raw is not None else []
            
            # 安全检查：处理空值和NaN
            if not retrieved_contexts or not reference_contexts or len(retrieved_contexts) == 0 or len(reference_contexts) == 0:
                # 对于空检索结果，平均精度为0
                results['average_precisions'].append(0.0)
                results['total_queries'] += 1
                results['queries_without_relevant_chunks'] += 1
                results['detailed_results'].append({
                    'row_index': idx,
                    'user_input': user_input,
                    'average_precision': 0.0,
                    'retrieved_count': len(retrieved_contexts) if retrieved_contexts else 0,
                    'reference_count': len(reference_contexts) if reference_contexts else 0,
                    'relevant_chunks_count': 0,
                    'calculation_details': {
                        'relevant_chunks': [],
                        'precision_at_k': [],
                        'relevant_positions': [],
                        'calculation_steps': [],
                        'chunk_relevance_scores': [],
                        'total_relevant': 0,
                        'total_retrieved': len(retrieved_contexts) if retrieved_contexts else 0
                    }
                })
                continue
            
            # 确保类型转换：从pandas Series转换为List[str]
            retrieved_contexts_list = retrieved_contexts if isinstance(retrieved_contexts, list) else list(retrieved_contexts) if retrieved_contexts is not None else []
            reference_contexts_list = reference_contexts if isinstance(reference_contexts, list) else list(reference_contexts) if reference_contexts is not None else []
            
            # 计算平均精度
            average_precision, calculation_details = self.calculate_average_precision(
                user_input, retrieved_contexts_list, reference_contexts_list
            )
            
            results['average_precisions'].append(average_precision)
            results['total_queries'] += 1
            
            if average_precision > 0:
                results['queries_with_relevant_chunks'] += 1
            else:
                results['queries_without_relevant_chunks'] += 1
            
            # 详细结果
            results['detailed_results'].append({
                'row_index': idx,
                'user_input': user_input,
                'average_precision': average_precision,
                'retrieved_count': len(retrieved_contexts),
                'reference_count': len(reference_contexts),
                'relevant_chunks_count': len(self.get_relevant_chunks_for_query(user_input, reference_contexts)),
                'calculation_details': calculation_details
            })
        
        # 按样本分组显示结果
        info_print("\n" + "=" * 80)
        info_print("📊 样本MAP评估结果")
        info_print("=" * 80)
        
        for result in results['detailed_results']:
            sample_idx = result['row_index'] + 1
            user_input = result['user_input']
            average_precision = result['average_precision']
            retrieved_count = result['retrieved_count']
            reference_count = result['reference_count']
            relevant_count = result['relevant_chunks_count']
            details = result['calculation_details']
            
            info_print(f"\n📋 样本 {sample_idx}:")
            info_print(f"  查询: {user_input}")
            info_print(f"  检索分块数: {retrieved_count}个, 参考分块数: {reference_count}个")
            info_print(f"  相关分块数: {relevant_count}个")
            
            if average_precision > 0:
                info_print(f"  📊 AP得分: {average_precision:.4f}")
                
                # 显示计算过程
                if details['calculation_steps']:
                    info_print(f"  📈 计算过程:")
                    for step in details['calculation_steps']:
                        info_print(f"    位置{step['position']}: 精度@{step['total_retrieved']} = {step['precision']:.4f} "
                                 f"(相关分块数: {step['relevant_count']}/{step['total_retrieved']})")
                
                # 显示相关分块位置
                if details['relevant_positions']:
                    info_print(f"  🎯 相关分块位置: {details['relevant_positions']}")
                    info_print(f"  📊 精度@k序列: {[f'{p:.4f}' for p in details['precision_at_k']]}")
            else:
                info_print(f"  ❌ 无相关分块")
                info_print(f"  📊 AP得分: 0.0000")
        
        # 计算MAP
        if results['average_precisions']:
            results['map'] = np.mean(results['average_precisions'])
        else:
            results['map'] = 0.0
        
        info_print(f"\n✅ MAP评估完成")
        info_print(f"📊 MAP: {results['map']:.4f}")
        info_print(f"📊 总查询数: {results['total_queries']}")
        info_print(f"📊 有相关分块的查询数: {results['queries_with_relevant_chunks']}")
        info_print(f"📊 无相关分块的查询数: {results['queries_without_relevant_chunks']}")
        
        return results
    
    def print_detailed_analysis(self, results: Dict[str, Any]):
        """
        打印详细的MAP分析结果
        
        Args:
            results: MAP评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📊 MAP详细分析")
        info_print("=" * 80)
        
        info_print("📋 MAP指标说明:")
        info_print("  • MAP (Mean Average Precision) = 平均平均精度")
        info_print("  • AP (Average Precision) = 每个相关分块被检索到时的精度值的平均值")
        info_print("  • 精度@k = 前k个检索结果中相关分块的数量 / k")
        info_print("  • 如果没有相关分块，AP为0")
        info_print(f"  • 相关性阈值: {self.relevance_threshold}")
        info_print()
        
        info_print("📊 评估结果:")
        info_print(f"1. MAP: {results['map']:.4f} ({results['map']*100:.1f}%)")
        info_print(f"2. 总查询数: {results['total_queries']}")
        info_print(f"3. 有相关分块的查询数: {results['queries_with_relevant_chunks']}")
        info_print(f"4. 无相关分块的查询数: {results['queries_without_relevant_chunks']}")
        
        if results['total_queries'] > 0:
            coverage = results['queries_with_relevant_chunks'] / results['total_queries']
            info_print(f"5. 相关分块覆盖率: {coverage:.4f} ({coverage*100:.1f}%)")
        
        # 平均精度分布统计
        average_precisions = results['average_precisions']
        if average_precisions:
            info_print(f"\n📊 平均精度分布:")
            info_print(f"  • 平均AP: {np.mean(average_precisions):.4f}")
            info_print(f"  • 最高AP: {np.max(average_precisions):.4f}")
            info_print(f"  • 最低AP: {np.min(average_precisions):.4f}")
            info_print(f"  • 标准差: {np.std(average_precisions):.4f}")
    
    def print_sample_analysis(self, results: Dict[str, Any]):
        """
        按样本打印MAP分析结果
        
        Args:
            results: MAP评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📊 样本级别MAP分析")
        info_print("=" * 80)
        
        # 按平均精度排序
        sorted_results = sorted(
            results['detailed_results'], 
            key=lambda x: x['average_precision'], 
            reverse=True
        )
        
        info_print("🔝 表现最好的样本 (前5个):")
        for i, result in enumerate(sorted_results[:5], 1):
            info_print(f"  {i}. 行 {result['row_index'] + 1}: AP {result['average_precision']:.4f}")
            info_print(f"     查询: {result['user_input'][:100]}...")
            info_print(f"     检索分块: {result['retrieved_count']}个, 参考分块: {result['reference_count']}个")
            info_print(f"     相关分块数: {result['relevant_chunks_count']}个")
            info_print()
        
        info_print("🔻 表现最差的样本 (后5个):")
        for i, result in enumerate(sorted_results[-5:], 1):
            info_print(f"  {i}. 行 {result['row_index'] + 1}: AP {result['average_precision']:.4f}")
            info_print(f"     查询: {result['user_input'][:100]}...")
            info_print(f"     检索分块: {result['retrieved_count']}个, 参考分块: {result['reference_count']}个")
            info_print(f"     相关分块数: {result['relevant_chunks_count']}个")
            info_print()
    
    def print_detailed_chunk_analysis(self, df: pd.DataFrame, max_samples: int = 3):
        """
        打印详细的分块分析
        
        Args:
            df: 数据DataFrame
            max_samples: 最大显示样本数
        """
        info_print("\n" + "=" * 80)
        info_print("🔍 详细分块分析")
        info_print("=" * 80)
        
        for idx, row in df.head(max_samples).iterrows():
            # 安全的索引转换
            sample_num = idx if isinstance(idx, int) else len(df.head(max_samples)) - list(df.head(max_samples).index).index(idx) if idx in df.head(max_samples).index else 1
            info_print(f"\n📋 样本 {sample_num + 1}:")
            
            # 安全获取字符串值
            user_input_val = row.get('user_input', '')
            user_input = str(user_input_val) if user_input_val is not None and not pd.isna(user_input_val) else ""
            
            # 确保类型转换：从pandas Series转换为List[str]
            retrieved_contexts_raw = row['retrieved_contexts']
            reference_contexts_raw = row['reference_contexts']
            
            retrieved_contexts = retrieved_contexts_raw if isinstance(retrieved_contexts_raw, list) else list(retrieved_contexts_raw) if retrieved_contexts_raw is not None else []
            reference_contexts = reference_contexts_raw if isinstance(reference_contexts_raw, list) else list(reference_contexts_raw) if reference_contexts_raw is not None else []
            
            info_print(f"查询: {user_input}")
            info_print(f"检索分块数: {len(retrieved_contexts)}")
            info_print(f"参考分块数: {len(reference_contexts)}")
            
            # 计算平均精度和详细过程
            average_precision, details = self.calculate_average_precision(
                user_input, retrieved_contexts, reference_contexts
            )
            
            info_print(f"\n📊 分块相关性分析:")
            if 'chunk_relevance_scores' in details and details['chunk_relevance_scores']:
                for i, chunk_info in enumerate(details['chunk_relevance_scores']):
                    status = "✅ 相关" if chunk_info['is_relevant'] else "❌ 不相关"
                    info_print(f"  位置{chunk_info['position']}: {status} (相关性: {chunk_info['relevance_score']:.4f})")
                    info_print(f"     检索分块: {chunk_info['chunk'][:100]}...")
                    if chunk_info['is_relevant']:
                        info_print(f"     最相关参考分块: {chunk_info['best_ref_chunk'][:80]}...")
                    info_print()
            else:
                info_print("  ❌ 无相关分块或检索分块数据")
            
            info_print(f"📊 平均精度计算:")
            if details['calculation_steps']:
                for step in details['calculation_steps']:
                    info_print(f"  位置{step['position']}: 精度@{step['total_retrieved']} = {step['precision']:.4f}")
                info_print(f"  AP = {average_precision:.4f}")
            else:
                info_print(f"  ❌ 无相关分块，AP = 0.0000")
            
            info_print("-" * 60)
    
    def run_evaluation(self) -> Dict[str, Any]:
        """
        运行完整的MAP评估
        
        Returns:
            Dict[str, Any]: MAP评估结果
        """
        info_print("🚀 开始MAP RAG评估")
        info_print("=" * 60)
        
        try:
            # 1. 加载数据
            df = self.load_and_process_data()
            if df is None:
                return {"error": "数据加载失败"}
            
            # 2. 运行MAP评估
            results = self.evaluate_map(df)
            
            # 3. 打印结果
            self.print_detailed_analysis(results)
            self.print_sample_analysis(results)
            
            # 4. 打印详细的分块分析
            self.print_detailed_chunk_analysis(df, max_samples=3)
            
            return results
            
        except Exception as e:
            error_print(f"❌ MAP评估失败: {e}")
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
    
    # 创建MAP评估器并运行评估
    evaluator = MAPEvaluator(config)
    results = evaluator.run_evaluation()
    
    if "error" in results:
        error_print(f"❌ MAP评估失败: {results['error']}")
    else:
        info_print(f"\n🎉 MAP评估成功完成！")
        info_print(f"📊 最终MAP分数: {results['map']:.4f}")


if __name__ == "__main__":
    main()
