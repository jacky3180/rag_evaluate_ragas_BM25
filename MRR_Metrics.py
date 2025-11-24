"""
RAG评估指标MRR (Mean Reciprocal Rank) 实现
用于计算检索系统中相关分块的排序质量

功能：
1. 加载RAG样本数据和分块数据
2. 使用BM25算法判断分块相关性
3. 计算每个样本的相关分块排序位置
4. 计算MRR指标
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from config import debug_print, verbose_print, info_print, error_print, QUIET_MODE
from read_chuck import EvaluationConfig, DataLoader, TextProcessor
from BM25_evaluate import BM25Evaluator, BM25, find_relevant_chunks, is_chunk_relevant


class MRREvaluator:
    """MRR (Mean Reciprocal Rank) 评估器"""
    
    def __init__(self, config: EvaluationConfig):
        """
        初始化MRR评估器
        
        Args:
            config: 评估配置
        """
        self.config = config
        self.data_loader = DataLoader(config)
        self.text_processor = TextProcessor(config)
        self.bm25_evaluator = BM25Evaluator(config)
        
        # 相关性阈值
        self.relevance_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
        
        info_print("🔧 MRR评估器初始化完成")
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
    
    def calculate_reciprocal_rank(self, query: str, retrieved_contexts: List[str], 
                                reference_contexts: List[str]) -> float:
        """
        计算单个查询的倒数排名
        
        Args:
            query: 用户查询
            retrieved_contexts: 检索分块列表
            reference_contexts: 参考分块列表
            
        Returns:
            float: 倒数排名分数
        """
        # 获取相关分块
        relevant_chunks = self.get_relevant_chunks_for_query(query, reference_contexts)
        
        if not relevant_chunks:
            # 如果没有相关分块，返回0
            debug_print(f"  查询: {query[:50]}... - 无相关分块")
            return 0.0
        
        if not retrieved_contexts:
            # 如果没有检索分块，返回0
            debug_print(f"  查询: {query[:50]}... - 无检索分块")
            return 0.0
        
        # 计算每个检索分块的位置（基于原始index的倒序）
        # 最后一个分块（index最大）的位置是1，第一个分块（index最小）的位置是len(retrieved_contexts)
        chunk_positions = {}
        for i, chunk in enumerate(retrieved_contexts):
            # 位置 = 总长度 - 原始index
            position = len(retrieved_contexts) - i
            chunk_positions[chunk] = position
        
        # 找到第一个相关分块的位置
        best_position = float('inf')  # 初始化一个很大的值
        best_chunk = None
        
        for chunk in retrieved_contexts:
            # 检查这个检索分块是否与任何参考分块相关
            for ref_chunk in relevant_chunks:
                # 使用BM25Evaluator的相关性计算方法
                relevance_score = self.bm25_evaluator.calculate_relevance_score(chunk, ref_chunk)
                
                if relevance_score > self.relevance_threshold:
                    # 找到相关分块，记录位置
                    position = chunk_positions[chunk]
                    if position < best_position:
                        best_position = position
                        best_chunk = chunk
        
        if best_chunk is not None:
            # 找到第一个相关分块，返回倒数排名
            reciprocal_rank = 1.0 / best_position
            return reciprocal_rank
        
        # 如果没有找到相关分块，返回0
        return 0.0
    
    def evaluate_mrr(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算MRR指标
        
        Args:
            df: 处理后的数据
            
        Returns:
            Dict[str, Any]: MRR评估结果
        """
        info_print("🔍 开始MRR评估...")
        info_print("📋 评估逻辑:")
        info_print("  • MRR = 所有查询的倒数排名平均值")
        info_print("  • 倒数排名 = 1 / 第一个相关分块的排名位置")
        info_print(f"  • 相关性判断: 检索分块与参考分块的语义相似度 > {self.relevance_threshold}")
        info_print()
        
        results = {
            'reciprocal_ranks': [],
            'detailed_results': [],
            'total_queries': 0,
            'queries_with_relevant_chunks': 0,
            'queries_without_relevant_chunks': 0
        }
        
        # 先计算所有样本的MRR，不打印详细信息
        for idx, row in df.iterrows():
            user_input = str(row['user_input']) if pd.notna(row['user_input']) else ""
            retrieved_contexts = row['retrieved_contexts']
            reference_contexts = row['reference_contexts']
            
            if not retrieved_contexts or not reference_contexts:
                # 对于空检索结果，倒数排名为0
                results['reciprocal_ranks'].append(0.0)
                results['total_queries'] += 1
                results['queries_without_relevant_chunks'] += 1
                results['detailed_results'].append({
                    'row_index': idx,
                    'user_input': user_input,
                    'reciprocal_rank': 0.0,
                    'retrieved_count': len(retrieved_contexts) if retrieved_contexts else 0,
                    'reference_count': len(reference_contexts) if reference_contexts else 0,
                    'relevant_chunks_count': 0,
                    'first_relevant_position': None
                })
                continue
            
            # 计算倒数排名
            reciprocal_rank = self.calculate_reciprocal_rank(
                user_input, retrieved_contexts, reference_contexts
            )
            
            results['reciprocal_ranks'].append(reciprocal_rank)
            results['total_queries'] += 1
            
            # 计算第一个相关分块的位置
            first_relevant_position = None
            if reciprocal_rank > 0:
                first_relevant_position = int(1 / reciprocal_rank)
                results['queries_with_relevant_chunks'] += 1
            else:
                results['queries_without_relevant_chunks'] += 1
            
            # 详细结果
            results['detailed_results'].append({
                'row_index': idx,
                'user_input': user_input,
                'reciprocal_rank': reciprocal_rank,
                'retrieved_count': len(retrieved_contexts),
                'reference_count': len(reference_contexts),
                'relevant_chunks_count': len(self.get_relevant_chunks_for_query(user_input, reference_contexts)),
                'first_relevant_position': first_relevant_position
            })
        
        # 按样本分组显示结果
        info_print("\n" + "=" * 80)
        info_print("📊 样本MRR评估结果")
        info_print("=" * 80)
        
        for result in results['detailed_results']:
            sample_idx = result['row_index'] + 1
            user_input = result['user_input']
            reciprocal_rank = result['reciprocal_rank']
            first_position = result['first_relevant_position']
            retrieved_count = result['retrieved_count']
            reference_count = result['reference_count']
            
            info_print(f"\n📋 样本 {sample_idx}:")
            info_print(f"  查询: {user_input}")
            info_print(f"  检索分块数: {retrieved_count}个, 参考分块数: {reference_count}个")
            
            if first_position is not None:
                info_print(f"  📍 第一个相关分块位置: {first_position}")
                info_print(f"  📊 MRR得分: {reciprocal_rank:.4f}")
            else:
                info_print(f"  ❌ 无相关分块")
                info_print(f"  📊 MRR得分: 0.0000")
        
        # 计算MRR
        if results['reciprocal_ranks']:
            results['mrr'] = np.mean(results['reciprocal_ranks'])
        else:
            results['mrr'] = 0.0
        
        info_print(f"\n✅ MRR评估完成")
        info_print(f"📊 MRR: {results['mrr']:.4f}")
        info_print(f"📊 总查询数: {results['total_queries']}")
        info_print(f"📊 有相关分块的查询数: {results['queries_with_relevant_chunks']}")
        info_print(f"📊 无相关分块的查询数: {results['queries_without_relevant_chunks']}")
        
        return results
    
    def print_detailed_analysis(self, results: Dict[str, Any]):
        """
        打印详细的MRR分析结果
        
        Args:
            results: MRR评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📊 MRR详细分析")
        info_print("=" * 80)
        
        info_print("📋 MRR指标说明:")
        info_print("  • MRR (Mean Reciprocal Rank) = 平均倒数排名")
        info_print("  • 倒数排名 = 1 / 第一个相关分块的排名位置")
        info_print("  • 如果没有相关分块，倒数排名为0")
        info_print(f"  • 相关性阈值: {self.relevance_threshold}")
        info_print()
        
        info_print("📊 评估结果:")
        info_print(f"1. MRR: {results['mrr']:.4f} ({results['mrr']*100:.1f}%)")
        info_print(f"2. 总查询数: {results['total_queries']}")
        info_print(f"3. 有相关分块的查询数: {results['queries_with_relevant_chunks']}")
        info_print(f"4. 无相关分块的查询数: {results['queries_without_relevant_chunks']}")
        
        if results['total_queries'] > 0:
            coverage = results['queries_with_relevant_chunks'] / results['total_queries']
            info_print(f"5. 相关分块覆盖率: {coverage:.4f} ({coverage*100:.1f}%)")
        
        # 倒数排名分布统计
        reciprocal_ranks = results['reciprocal_ranks']
        if reciprocal_ranks:
            info_print(f"\n📊 倒数排名分布:")
            info_print(f"  • 平均倒数排名: {np.mean(reciprocal_ranks):.4f}")
            info_print(f"  • 最高倒数排名: {np.max(reciprocal_ranks):.4f}")
            info_print(f"  • 最低倒数排名: {np.min(reciprocal_ranks):.4f}")
            info_print(f"  • 标准差: {np.std(reciprocal_ranks):.4f}")
            
            # 排名位置分布
            rank_positions = [1/rr for rr in reciprocal_ranks if rr > 0]
            if rank_positions:
                info_print(f"\n📊 相关分块排名位置分布:")
                info_print(f"  • 平均排名位置: {np.mean(rank_positions):.2f}")
                info_print(f"  • 最佳排名位置: {int(np.min(rank_positions))}")
                info_print(f"  • 最差排名位置: {int(np.max(rank_positions))}")
    
    def print_sample_analysis(self, results: Dict[str, Any]):
        """
        按样本打印MRR分析结果
        
        Args:
            results: MRR评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📊 样本级别MRR分析")
        info_print("=" * 80)
        
        # 按倒数排名排序
        sorted_results = sorted(
            results['detailed_results'], 
            key=lambda x: x['reciprocal_rank'], 
            reverse=True
        )
        
        info_print("🔝 表现最好的样本 (前5个):")
        for i, result in enumerate(sorted_results[:5], 1):
            rank_pos = int(1/result['reciprocal_rank']) if result['reciprocal_rank'] > 0 else "无相关分块"
            info_print(f"  {i}. 行 {result['row_index'] + 1}: 倒数排名 {result['reciprocal_rank']:.4f} (排名位置: {rank_pos})")
            info_print(f"     查询: {result['user_input'][:100]}...")
            info_print(f"     检索分块: {result['retrieved_count']}个, 参考分块: {result['reference_count']}个")
            info_print(f"     相关分块数: {result['relevant_chunks_count']}个")
            info_print()
        
        info_print("🔻 表现最差的样本 (后5个):")
        for i, result in enumerate(sorted_results[-5:], 1):
            rank_pos = int(1/result['reciprocal_rank']) if result['reciprocal_rank'] > 0 else "无相关分块"
            info_print(f"  {i}. 行 {result['row_index'] + 1}: 倒数排名 {result['reciprocal_rank']:.4f} (排名位置: {rank_pos})")
            info_print(f"     查询: {result['user_input'][:100]}...")
            info_print(f"     检索分块: {result['retrieved_count']}个, 参考分块: {result['reference_count']}个")
            info_print(f"     相关分块数: {result['relevant_chunks_count']}个")
            info_print()
    
    def print_detailed_chunk_ranking(self, df: pd.DataFrame, max_samples: int = 3):
        """
        打印详细的分块排序分析
        
        Args:
            df: 数据DataFrame
            max_samples: 最大显示样本数
        """
        info_print("\n" + "=" * 80)
        info_print("🔍 详细分块排序分析")
        info_print("=" * 80)
        
        for idx, row in df.head(max_samples).iterrows():
            info_print(f"\n📋 样本 {idx + 1}:")
            user_input = str(row['user_input']) if pd.notna(row['user_input']) else ""
            retrieved_contexts = row['retrieved_contexts']
            reference_contexts = row['reference_contexts']
            
            info_print(f"查询: {user_input}")
            info_print(f"检索分块数: {len(retrieved_contexts)}")
            info_print(f"参考分块数: {len(reference_contexts)}")
            
            # 显示分块位置信息（基于原始index的倒序）
            info_print(f"\n📊 分块位置信息 (基于原始index倒序):")
            for i, chunk in enumerate(retrieved_contexts):
                position = len(retrieved_contexts) - i
                info_print(f"  分块{i} (原始index): 位置{position}")
                info_print(f"     内容: {chunk[:100]}...")
                
                # 检查与参考分块的相关性
                max_relevance = 0.0
                best_ref_chunk = ""
                for ref_chunk in reference_contexts:
                    relevance = self.bm25_evaluator.calculate_relevance_score(chunk, ref_chunk)
                    if relevance > max_relevance:
                        max_relevance = relevance
                        best_ref_chunk = ref_chunk
                
                if max_relevance > self.relevance_threshold:
                    info_print(f"     ✅ 相关性: {max_relevance:.4f} (相关)")
                    info_print(f"     🎯 最相关参考分块: {best_ref_chunk[:80]}...")
                else:
                    info_print(f"     ❌ 相关性: {max_relevance:.4f} (不相关)")
                info_print()
            
            # 计算倒数排名
            reciprocal_rank = self.calculate_reciprocal_rank(user_input, retrieved_contexts, reference_contexts)
            if reciprocal_rank > 0:
                rank_position = int(1 / reciprocal_rank)
                info_print(f"📍 第一个相关分块位置: {rank_position}")
                info_print(f"📊 倒数排名: {reciprocal_rank:.4f}")
            else:
                info_print(f"❌ 无相关分块，倒数排名: 0.0000")
            
            info_print("-" * 60)
    
    def run_evaluation(self) -> Dict[str, Any]:
        """
        运行完整的MRR评估
        
        Returns:
            Dict[str, Any]: MRR评估结果
        """
        info_print("🚀 开始MRR RAG评估")
        info_print("=" * 60)
        
        try:
            # 1. 加载数据
            df = self.load_and_process_data()
            if df is None:
                return {"error": "数据加载失败"}
            
            # 2. 运行MRR评估
            results = self.evaluate_mrr(df)
            
            # 3. 打印结果
            self.print_detailed_analysis(results)
            self.print_sample_analysis(results)
            
            # 4. 打印详细的分块排序分析
            self.print_detailed_chunk_ranking(df, max_samples=3)
            
            return results
            
        except Exception as e:
            error_print(f"❌ MRR评估失败: {e}")
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
    
    # 创建MRR评估器并运行评估
    evaluator = MRREvaluator(config)
    results = evaluator.run_evaluation()
    
    if "error" in results:
        error_print(f"❌ MRR评估失败: {results['error']}")
    else:
        info_print(f"\n🎉 MRR评估成功完成！")
        info_print(f"📊 最终MRR分数: {results['mrr']:.4f}")


if __name__ == "__main__":
    main()
