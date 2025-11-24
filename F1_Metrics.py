"""
F1-score计算模块
基于BM25评估的Precision和Recall计算F1-score（调和平均数）

功能：
1. 调用BM25_evaluate.py中的precision和recall计算函数
2. 计算F1-score = 2 * (precision * recall) / (precision + recall)
3. 提供F1-score计算接口
"""

import os
import numpy as np
from typing import Dict, Any, List, Optional
from config import debug_print, verbose_print, info_print, error_print, QUIET_MODE
from BM25_evaluate import BM25Evaluator
from read_chuck import EvaluationConfig


class F1ScoreCalculator:
    """F1-score计算器"""
    
    def __init__(self, config: EvaluationConfig):
        """
        初始化F1-score计算器
        
        Args:
            config: 评估配置
        """
        self.config = config
        self.bm25_evaluator = BM25Evaluator(config)
    
    def calculate_f1_score(self, precision: float, recall: float) -> float:
        """
        计算F1-score（Precision和Recall的调和平均数）
        
        Args:
            precision: 精确率
            recall: 召回率
            
        Returns:
            float: F1-score值
        """
        if precision is None or recall is None:
            return 0.0
        
        if precision + recall == 0:
            return 0.0
        
        f1_score = 2 * (precision * recall) / (precision + recall)
        return f1_score
    
    def calculate_f1_scores_from_bm25_results(self, bm25_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        从BM25评估结果中计算F1-score
        
        Args:
            bm25_results: BM25评估结果
            
        Returns:
            Dict[str, Any]: 包含F1-score的结果
        """
        info_print("🔍 开始计算F1-score...")
        
        # 获取平均Precision和Recall
        avg_precision = bm25_results.get('avg_precision', 0)
        avg_recall = bm25_results.get('avg_recall', 0)
        
        # 计算平均F1-score
        avg_f1 = self.calculate_f1_score(avg_precision, avg_recall)
        
        # 计算每个样本的F1-score
        precision_scores = bm25_results.get('precision_scores', [])
        recall_scores = bm25_results.get('recall_scores', [])
        
        f1_scores = []
        for i in range(len(precision_scores)):
            precision = precision_scores[i] if i < len(precision_scores) else 0
            recall = recall_scores[i] if i < len(recall_scores) else 0
            f1_score = self.calculate_f1_score(precision, recall)
            f1_scores.append(f1_score)
        
        # 构建结果
        results = {
            'avg_f1': avg_f1,
            'f1_scores': f1_scores,
            'avg_precision': avg_precision,
            'avg_recall': avg_recall,
            'total_samples': len(f1_scores),
            'bm25_results': bm25_results  # 保留原始BM25结果
        }
        
        info_print(f"✅ F1-score计算完成")
        info_print(f"📊 平均F1-score: {avg_f1:.4f}")
        info_print(f"📊 平均Precision: {avg_precision:.4f}")
        info_print(f"📊 平均Recall: {avg_recall:.4f}")
        info_print(f"📊 样本数: {len(f1_scores)}")
        
        return results
    
    def run_f1_evaluation(self) -> Dict[str, Any]:
        """
        运行完整的F1-score评估
        
        Returns:
            Dict[str, Any]: F1-score评估结果
        """
        info_print("🚀 开始F1-score评估")
        info_print("=" * 60)
        
        try:
            # 1. 运行BM25评估获取Precision和Recall
            bm25_results = self.bm25_evaluator.run_evaluation()
            
            if "error" in bm25_results:
                return {"error": f"BM25评估失败: {bm25_results['error']}"}
            
            # 2. 基于BM25结果计算F1-score
            f1_results = self.calculate_f1_scores_from_bm25_results(bm25_results)
            
            return f1_results
            
        except Exception as e:
            error_msg = f"F1-score评估失败: {str(e)}"
            info_print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return {"error": error_msg}


def calculate_f1_score(precision: float, recall: float) -> float:
    """
    计算F1-score的静态函数
    
    Args:
        precision: 精确率
        recall: 召回率
        
    Returns:
        float: F1-score值
    """
    if precision is None or recall is None:
        return 0.0
    
    if precision + recall == 0:
        return 0.0
    
    f1_score = 2 * (precision * recall) / (precision + recall)
    return f1_score


def main():
    """主函数"""
    # 创建配置
    config = EvaluationConfig(
        api_key=os.getenv("QWEN_API_KEY", "dummy_key"),
        api_base=os.getenv("QWEN_API_BASE", "dummy_base"),
        excel_file_path=os.getenv("EXCEL_FILE_PATH", "standardDataset/standardDataset.xlsx")
    )
    
    # 创建F1-score计算器并运行评估
    calculator = F1ScoreCalculator(config)
    results = calculator.run_f1_evaluation()
    
    if "error" in results:
        info_print(f"❌ F1-score评估失败: {results['error']}")
    else:
        info_print(f"\n🎉 F1-score评估成功完成！")
        info_print(f"📊 最终F1-score: {results['avg_f1']:.4f}")


if __name__ == "__main__":
    main()
