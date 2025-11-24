"""
RAG评估指标NDCG (Normalized Discounted Cumulative Gain) 实现
用于计算检索系统中相关分块的排序质量

功能：
1. 加载RAG样本数据和分块数据
2. 使用BM25算法判断分块相关性
3. 计算每个样本的DCG和IDCG
4. 计算NDCG指标
5. 按样本分组显示计算过程
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from config import debug_print, verbose_print, info_print, error_print, QUIET_MODE
from read_chuck import EvaluationConfig, DataLoader, TextProcessor
from BM25_evaluate import BM25Evaluator, BM25, find_relevant_chunks, is_chunk_relevant


class NDCGEvaluator:
    """NDCG (Normalized Discounted Cumulative Gain) 评估器"""
    
    def __init__(self, config: EvaluationConfig):
        """
        初始化NDCG评估器
        
        Args:
            config: 评估配置
        """
        self.config = config
        self.data_loader = DataLoader(config)
        self.text_processor = TextProcessor(config)
        self.bm25_evaluator = BM25Evaluator(config)
        
        # 相关性阈值
        self.relevance_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
        
        info_print("🔧 NDCG评估器初始化完成")
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
    
    def calculate_relevance_scores(self, query: str, retrieved_contexts: List[str], 
                                 reference_contexts: List[str]) -> List[float]:
        """
        计算检索分块的相关性分数
        
        Args:
            query: 用户查询
            retrieved_contexts: 检索分块列表
            reference_contexts: 参考分块列表
            
        Returns:
            List[float]: 每个检索分块的相关性分数
        """
        if not retrieved_contexts or not reference_contexts:
            return []
        
        relevance_scores = []
        for retrieved_chunk in retrieved_contexts:
            max_relevance = 0.0
            for ref_chunk in reference_contexts:
                # 使用BM25Evaluator的相关性计算方法
                relevance = self.bm25_evaluator.calculate_relevance_score(retrieved_chunk, ref_chunk)
                if relevance > max_relevance:
                    max_relevance = relevance
            
            # 将相关性分数转换为二进制相关性（0或1）
            binary_relevance = 1.0 if max_relevance > self.relevance_threshold else 0.0
            relevance_scores.append(binary_relevance)
        
        return relevance_scores
    
    def calculate_dcg(self, relevance_scores: List[float]) -> float:
        """
        计算DCG (Discounted Cumulative Gain)
        使用倒序位置计算，但保持NDCG评估逻辑：相关分块越靠前得分越高
        
        Args:
            relevance_scores: 相关性分数列表
            
        Returns:
            float: DCG值
        """
        if not relevance_scores:
            return 0.0
        
        dcg = 0.0
        for i, relevance in enumerate(relevance_scores):
            # 倒序位置计算：index=0→位置3, index=1→位置2, index=2→位置1
            # 但NDCG评估仍然遵循"相关分块越靠前得分越高"的原则
            position = len(relevance_scores) - i
            # DCG公式: DCG = Σ(2^relevance - 1) / log2(position + 1)
            dcg += (2**relevance - 1) / np.log2(position + 1)
        
        return dcg
    
    def calculate_idcg(self, relevance_scores: List[float]) -> float:
        """
        计算IDCG (Ideal Discounted Cumulative Gain)
        
        Args:
            relevance_scores: 相关性分数列表
            
        Returns:
            float: IDCG值
        """
        if not relevance_scores:
            return 0.0
        
        # 将相关性分数按降序排列（理想排序）
        ideal_scores = sorted(relevance_scores, reverse=True)
        
        # 计算理想排序的DCG，使用正向位置
        idcg = 0.0
        for i, relevance in enumerate(ideal_scores):
            position = i + 1  # 理想排序中，位置就是i+1
            # DCG公式: DCG = Σ(2^relevance - 1) / log2(position + 1)
            idcg += (2**relevance - 1) / np.log2(position + 1)
        
        return idcg
    
    def calculate_ndcg(self, query: str, retrieved_contexts: List[str], 
                      reference_contexts: List[str]) -> Tuple[float, Dict[str, Any]]:
        """
        计算单个查询的NDCG
        
        Args:
            query: 用户查询
            retrieved_contexts: 检索分块列表
            reference_contexts: 参考分块列表
            
        Returns:
            Tuple[float, Dict[str, Any]]: (NDCG值, 详细计算过程)
        """
        if not retrieved_contexts or not reference_contexts:
            return 0.0, {
                'relevance_scores': [],
                'dcg': 0.0,
                'idcg': 0.0,
                'ndcg': 0.0,
                'calculation_steps': []
            }
        
        # 计算相关性分数
        relevance_scores = self.calculate_relevance_scores(query, retrieved_contexts, reference_contexts)
        
        # 计算DCG
        dcg = self.calculate_dcg(relevance_scores)
        
        # 计算IDCG
        idcg = self.calculate_idcg(relevance_scores)
        
        # 计算NDCG
        if idcg > 0:
            ndcg = dcg / idcg
        else:
            ndcg = 0.0
        
        # 生成计算步骤
        calculation_steps = []
        for i, (chunk, relevance) in enumerate(zip(retrieved_contexts, relevance_scores)):
            # 倒序位置计算：index=0→位置3, index=1→位置2, index=2→位置1
            position = len(retrieved_contexts) - i
            gain = 2**relevance - 1
            discount = np.log2(position + 1)
            dcg_contribution = gain / discount
            
            calculation_steps.append({
                'position': position,
                'chunk': chunk,
                'relevance': relevance,
                'gain': gain,
                'discount': discount,
                'dcg_contribution': dcg_contribution
            })
        
        return ndcg, {
            'relevance_scores': relevance_scores,
            'dcg': dcg,
            'idcg': idcg,
            'ndcg': ndcg,
            'calculation_steps': calculation_steps,
            'total_chunks': len(retrieved_contexts),
            'relevant_chunks': sum(relevance_scores)
        }
    
    def evaluate_ndcg(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算NDCG指标
        
        Args:
            df: 处理后的数据
            
        Returns:
            Dict[str, Any]: NDCG评估结果
        """
        info_print("🔍 开始NDCG评估...")
        info_print("📋 评估逻辑:")
        info_print("  • NDCG = DCG / IDCG")
        info_print("  • DCG = Σ(2^relevance - 1) / log2(position + 1)")
        info_print("  • IDCG = 理想排序下的DCG值")
        info_print(f"  • 相关性判断: 检索分块与参考分块的语义相似度 > {self.relevance_threshold}")
        info_print()
        
        results = {
            'ndcg_scores': [],
            'detailed_results': [],
            'total_queries': 0,
            'queries_with_relevant_chunks': 0,
            'queries_without_relevant_chunks': 0
        }
        
        # 计算所有样本的NDCG
        for idx, row in df.iterrows():
            user_input = str(row['user_input']) if pd.notna(row['user_input']) else ""
            retrieved_contexts = row['retrieved_contexts']
            reference_contexts = row['reference_contexts']
            
            if not retrieved_contexts or not reference_contexts:
                # 对于空检索结果，NDCG为0
                results['ndcg_scores'].append(0.0)
                results['total_queries'] += 1
                results['queries_without_relevant_chunks'] += 1
                results['detailed_results'].append({
                    'row_index': idx,
                    'user_input': user_input,
                    'ndcg': 0.0,
                    'dcg': 0.0,
                    'idcg': 0.0,
                    'retrieved_count': len(retrieved_contexts) if retrieved_contexts else 0,
                    'reference_count': len(reference_contexts) if reference_contexts else 0,
                    'relevant_chunks_count': 0,
                    'calculation_details': {
                        'relevance_scores': [],
                        'dcg': 0.0,
                        'idcg': 0.0,
                        'ndcg': 0.0,
                        'calculation_steps': []
                    }
                })
                continue
            
            # 计算NDCG
            ndcg, calculation_details = self.calculate_ndcg(
                user_input, retrieved_contexts, reference_contexts
            )
            
            results['ndcg_scores'].append(ndcg)
            results['total_queries'] += 1
            
            if ndcg > 0:
                results['queries_with_relevant_chunks'] += 1
            else:
                results['queries_without_relevant_chunks'] += 1
            
            # 详细结果
            results['detailed_results'].append({
                'row_index': idx,
                'user_input': user_input,
                'ndcg': ndcg,
                'dcg': calculation_details['dcg'],
                'idcg': calculation_details['idcg'],
                'retrieved_count': len(retrieved_contexts),
                'reference_count': len(reference_contexts),
                'relevant_chunks_count': calculation_details['relevant_chunks'],
                'calculation_details': calculation_details
            })
        
        # 按样本分组显示结果
        info_print("\n" + "=" * 80)
        info_print("📊 样本NDCG评估结果")
        info_print("=" * 80)
        
        for result in results['detailed_results']:
            sample_idx = result['row_index'] + 1
            user_input = result['user_input']
            ndcg = result['ndcg']
            dcg = result['dcg']
            idcg = result['idcg']
            retrieved_count = result['retrieved_count']
            reference_count = result['reference_count']
            relevant_count = result['relevant_chunks_count']
            details = result['calculation_details']
            
            info_print(f"\n📋 样本 {sample_idx}:")
            info_print(f"  查询: {user_input}")
            info_print(f"  检索分块数: {retrieved_count}个, 参考分块数: {reference_count}个")
            info_print(f"  相关分块数: {relevant_count}个")
            
            if ndcg > 0:
                info_print(f"  📊 NDCG得分: {ndcg:.4f}")
                info_print(f"  📊 DCG: {dcg:.4f}")
                info_print(f"  📊 IDCG: {idcg:.4f}")
                
                # 显示计算过程
                if details['calculation_steps']:
                    info_print(f"  📈 计算过程:")
                    for step in details['calculation_steps']:
                        status = "✅ 相关" if step['relevance'] > 0 else "❌ 不相关"
                        info_print(f"    位置{step['position']}: {status} (相关性: {step['relevance']:.0f})")
                        info_print(f"      增益: 2^{step['relevance']:.0f} - 1 = {step['gain']:.0f}")
                        info_print(f"      折损: log2({step['position'] + 1}) = {step['discount']:.4f}")
                        info_print(f"      DCG贡献: {step['dcg_contribution']:.4f}")
                        info_print(f"      分块: {step['chunk'][:100]}...")
                        info_print()
                
                # 显示相关性分数序列
                relevance_scores = details['relevance_scores']
                info_print(f"  🎯 相关性分数序列: {[f'{score:.0f}' for score in relevance_scores]}")
            else:
                info_print(f"  ❌ 无相关分块")
                info_print(f"  📊 NDCG得分: 0.0000")
        
        # 计算平均NDCG
        if results['ndcg_scores']:
            results['avg_ndcg'] = np.mean(results['ndcg_scores'])
        else:
            results['avg_ndcg'] = 0.0
        
        info_print(f"\n✅ NDCG评估完成")
        info_print(f"📊 平均NDCG: {results['avg_ndcg']:.4f}")
        info_print(f"📊 总查询数: {results['total_queries']}")
        info_print(f"📊 有相关分块的查询数: {results['queries_with_relevant_chunks']}")
        info_print(f"📊 无相关分块的查询数: {results['queries_without_relevant_chunks']}")
        
        return results
    
    def print_detailed_analysis(self, results: Dict[str, Any]):
        """
        打印详细的NDCG分析结果
        
        Args:
            results: NDCG评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📊 NDCG详细分析")
        info_print("=" * 80)
        
        info_print("📋 NDCG指标说明:")
        info_print("  • NDCG (Normalized Discounted Cumulative Gain) = 归一化折损累积增益")
        info_print("  • DCG = Σ(2^relevance - 1) / log2(position + 1)")
        info_print("  • IDCG = 理想排序下的DCG值")
        info_print("  • NDCG = DCG / IDCG")
        info_print("  • 如果没有相关分块，NDCG为0")
        info_print(f"  • 相关性阈值: {self.relevance_threshold}")
        info_print()
        
        info_print("📊 评估结果:")
        info_print(f"1. 平均NDCG: {results['avg_ndcg']:.4f} ({results['avg_ndcg']*100:.1f}%)")
        info_print(f"2. 总查询数: {results['total_queries']}")
        info_print(f"3. 有相关分块的查询数: {results['queries_with_relevant_chunks']}")
        info_print(f"4. 无相关分块的查询数: {results['queries_without_relevant_chunks']}")
        
        if results['total_queries'] > 0:
            coverage = results['queries_with_relevant_chunks'] / results['total_queries']
            info_print(f"5. 相关分块覆盖率: {coverage:.4f} ({coverage*100:.1f}%)")
        
        # NDCG分布统计
        ndcg_scores = results['ndcg_scores']
        if ndcg_scores:
            info_print(f"\n📊 NDCG分布:")
            info_print(f"  • 平均NDCG: {np.mean(ndcg_scores):.4f}")
            info_print(f"  • 最高NDCG: {np.max(ndcg_scores):.4f}")
            info_print(f"  • 最低NDCG: {np.min(ndcg_scores):.4f}")
            info_print(f"  • 标准差: {np.std(ndcg_scores):.4f}")
    
    def print_sample_analysis(self, results: Dict[str, Any]):
        """
        按样本打印NDCG分析结果，显示每个样本的分块计算过程
        
        Args:
            results: NDCG评估结果
        """
        info_print("\n" + "=" * 80)
        info_print("📊 样本级别NDCG分析")
        info_print("=" * 80)
        
        # 显示所有样本的详细计算过程
        for i, result in enumerate(results['detailed_results'], 1):
            info_print(f"\n📋 样本 {i} (行 {result['row_index'] + 1}):")
            info_print(f"  查询: {result['user_input']}")
            info_print(f"  检索分块数: {result['retrieved_count']}个, 参考分块数: {result['reference_count']}个")
            info_print(f"  相关分块数: {result['relevant_chunks_count']}个")
            info_print(f"  DCG: {result['dcg']:.4f}, IDCG: {result['idcg']:.4f}, NDCG: {result['ndcg']:.4f}")
            
            # 显示分块计算过程
            if 'calculation_details' in result and 'calculation_steps' in result['calculation_details']:
                info_print(f"\n  📊 分块计算过程:")
                calculation_steps = result['calculation_details']['calculation_steps']
                for step in calculation_steps:
                    status = "✅ 相关" if step['relevance'] > 0 else "❌ 不相关"
                    info_print(f"    位置{step['position']}: {status}")
                    info_print(f"      分块内容: {step['chunk'][:80]}...")
                    info_print(f"      相关性分数: {step['relevance']:.4f}")
                    info_print(f"      Gain: {step['gain']:.4f}")
                    info_print(f"      Discount: {step['discount']:.4f}")
                    info_print(f"      DCG贡献: {step['dcg_contribution']:.4f}")
                    info_print()
            else:
                info_print(f"  📊 无分块计算过程")
            
            info_print(f"  {'='*60}")
        
        # 按NDCG排序显示统计信息
        sorted_results = sorted(
            results['detailed_results'], 
            key=lambda x: x['ndcg'], 
            reverse=True
        )
        
        info_print(f"\n🔝 表现最好的样本 (前3个):")
        for i, result in enumerate(sorted_results[:3], 1):
            info_print(f"  {i}. 行 {result['row_index'] + 1}: NDCG {result['ndcg']:.4f}")
            info_print(f"     查询: {result['user_input'][:100]}...")
            info_print(f"     相关分块数: {result['relevant_chunks_count']}个")
        
        info_print(f"\n🔻 表现最差的样本 (后3个):")
        for i, result in enumerate(sorted_results[-3:], 1):
            info_print(f"  {i}. 行 {result['row_index'] + 1}: NDCG {result['ndcg']:.4f}")
            info_print(f"     查询: {result['user_input'][:100]}...")
            info_print(f"     相关分块数: {result['relevant_chunks_count']}个")
    
    def run_evaluation(self) -> Dict[str, Any]:
        """
        运行完整的NDCG评估
        
        Returns:
            Dict[str, Any]: NDCG评估结果
        """
        info_print("🚀 开始NDCG RAG评估")
        info_print("=" * 60)
        
        try:
            # 1. 加载数据
            df = self.load_and_process_data()
            if df is None:
                return {"error": "数据加载失败"}
            
            # 2. 运行NDCG评估
            results = self.evaluate_ndcg(df)
            
            # 3. 打印结果
            self.print_detailed_analysis(results)
            self.print_sample_analysis(results)
            
            return results
            
        except Exception as e:
            error_print(f"❌ NDCG评估失败: {e}")
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
    
    # 创建NDCG评估器并运行评估
    evaluator = NDCGEvaluator(config)
    results = evaluator.run_evaluation()
    
    if "error" in results:
        error_print(f"❌ NDCG评估失败: {results['error']}")
    else:
        info_print(f"\n🎉 NDCG评估成功完成！")
        info_print(f"📊 最终NDCG分数: {results['avg_ndcg']:.4f}")


if __name__ == "__main__":
    main()
