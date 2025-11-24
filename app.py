"""
RAG评估系统Web应用
基于FastAPI + HTML/CSS/JS实现
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import os
import json
import pandas as pd
import re
from typing import Dict, Any, List, Optional
from config import debug_print, verbose_print, info_print, error_print, QUIET_MODE
import traceback
import tempfile
from pathlib import Path
from uploadFile import upload_document, get_upload_info, delete_uploaded_file, upload_knowledge_document, get_knowledge_documents, delete_knowledge_document, get_dataset_files
from standardDatasetBuild import build_standard_dataset
from env_manager import update_env_file, get_env_value

# 导入缓存模块
from api_cache import (
    get_history_cache, get_stats_cache, get_eval_cache,
    clear_all_caches, get_all_cache_stats, cache_response
)

# 导入评估模块
from BM25_evaluate import BM25Evaluator
from rag_evaluator import MainController, RagasMetricsConfig
from read_chuck import EvaluationConfig
from MRR_Metrics import MRREvaluator
from MAP_Metrics import MAPEvaluator
from NDCG_Metrics import NDCGEvaluator
from F1_Metrics import F1ScoreCalculator

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度
    使用Jaccard相似度和字符重叠度
    """
    if not text1 or not text2:
        return 0.0
    
    # 清理文本：移除标点符号，转换为小写
    def clean_text(text):
        # 移除标点符号和特殊字符，保留中文、英文、数字
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        # 移除多余空格
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned.lower()
    
    clean_text1 = clean_text(text1)
    clean_text2 = clean_text(text2)
    
    # 1. Jaccard相似度（基于词）
    words1 = set(clean_text1.split())
    words2 = set(clean_text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    jaccard_similarity = intersection / union if union > 0 else 0.0
    
    # 2. 字符重叠度（基于字符）
    chars1 = set(clean_text1)
    chars2 = set(clean_text2)
    char_intersection = len(chars1.intersection(chars2))
    char_union = len(chars1.union(chars2))
    char_similarity = char_intersection / char_union if char_union > 0 else 0.0
    
    # 3. 子字符串匹配度
    substring_similarity = 0.0
    if len(clean_text1) > 10 and len(clean_text2) > 10:
        # 检查较短的文本是否包含在较长的文本中
        shorter, longer = (clean_text1, clean_text2) if len(clean_text1) < len(clean_text2) else (clean_text2, clean_text1)
        if shorter in longer:
            substring_similarity = len(shorter) / len(longer)
        else:
            # 检查部分匹配
            max_match = 0
            for i in range(len(shorter) - 5):  # 至少5个字符的匹配
                for j in range(i + 5, len(shorter) + 1):
                    substring = shorter[i:j]
                    if substring in longer:
                        max_match = max(max_match, len(substring))
            substring_similarity = max_match / len(longer) if longer else 0.0
    
    # 综合相似度：加权平均
    final_similarity = (
        jaccard_similarity * 0.4 +      # 词级别相似度权重40%
        char_similarity * 0.3 +         # 字符级别相似度权重30%
        substring_similarity * 0.3      # 子字符串匹配度权重30%
    )
    
    # 优化：如果短文本完全包含在长文本中，给予更高的相似度
    # 这是为了处理"检索分块包含标准答案分块"的场景
    if len(clean_text1) > len(clean_text2):
        # text1是长文本，text2是短文本
        if clean_text2 in clean_text1:
            # 短文本完全包含在长文本中，给予包含度奖励
            # 使用更高的相似度分数，确保能通过阈值
            containment_similarity = 0.8  # 固定给予0.8的相似度
            final_similarity = max(final_similarity, containment_similarity)
    elif len(clean_text2) > len(clean_text1):
        # text2是长文本，text1是短文本
        if clean_text1 in clean_text2:
            # 短文本完全包含在长文本中，给予包含度奖励
            # 使用更高的相似度分数，确保能通过阈值
            containment_similarity = 0.8  # 固定给予0.8的相似度
            final_similarity = max(final_similarity, containment_similarity)
    
    # 新增：检查语义包含度是否超过阈值（完整包含检测）
    semantic_containment_threshold = float(os.getenv("SEMANTIC_CONTAINMENT_THRESHOLD", "0.9"))
    
    # 计算语义包含度（基于词级别的重叠）
    if len(words1) > 0 and len(words2) > 0:
        # 计算较短文本的词在较长文本中的包含度
        if len(words1) <= len(words2):
            # words1是较短的，计算words1在words2中的包含度
            contained_words = words1.intersection(words2)
            semantic_containment = len(contained_words) / len(words1)
        else:
            # words2是较短的，计算words2在words1中的包含度
            contained_words = words2.intersection(words1)
            semantic_containment = len(contained_words) / len(words2)
        
        # 如果语义包含度超过阈值，给予高相似度分数
        if semantic_containment >= semantic_containment_threshold:
            # 使用包含度作为相似度分数，确保能通过阈值
            containment_similarity = min(semantic_containment, 0.95)  # 最高0.95，避免完全匹配
            final_similarity = max(final_similarity, containment_similarity)
    
    return min(final_similarity, 1.0)

# 导入数据库模块
from database.db_service import DatabaseService
from database.db_config import create_tables, test_connection
db = DatabaseService()
init_database = create_tables

app = FastAPI(title="RAG评估系统", description="BM25和Ragas评估系统Web界面")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 添加构建数据集页面的直接路由
@app.get("/standardDataset_build.html")
async def build_dataset_page():
    """构建数据集页面"""
    with open("static/standardDataset_build.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

# 全局变量存储评估结果
bm25_results = None
ragas_results = {}

class EvaluationRequest(BaseModel):
    """评估请求模型"""
    dataset_file: Optional[str] = "standardDataset.xlsx"

class EvaluationResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = {}

class SaveEvaluationRequest(BaseModel):
    """保存评估结果请求模型"""
    evaluation_type: str  # "BM25" 或 "RAGAS"
    description: str = ""

class BM25CombinedResults(BaseModel):
    """BM25合并结果模型"""
    context_precision: float
    context_recall: float
    f1_score: float
    mrr: float
    map: float
    ndcg: float
    total_samples: int
    irrelevant_chunks: int
    missed_chunks: int
    relevant_chunks: int
    description: str = ""

class SaveEvaluationResponse(BaseModel):
    """保存评估结果响应模型"""
    success: bool
    message: str
    evaluation_id: Optional[int] = None


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """主页面"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        try:
            with open("static/index.html", "r", encoding="gbk") as f:
                return HTMLResponse(content=f.read())
        except:
            # 如果都失败，返回简单的HTML页面
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>RAG评估系统</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>RAG评估系统</h1>
                <p>系统正在启动中，请稍后刷新页面...</p>
                <script>setTimeout(() => location.reload(), 2000);</script>
            </body>
            </html>
            """)

@app.post("/api/mrr/evaluate", response_model=EvaluationResponse)
async def run_mrr_evaluation(request: Optional[EvaluationRequest] = None):
    """运行MRR评估"""
    try:
        # 获取数据集文件路径
        dataset_file = "standardDataset.xlsx" if request is None else request.dataset_file
        excel_file_path = f"standardDataset/{dataset_file}"
        
        # 设置环境变量
        os.environ["EXCEL_FILE_PATH"] = excel_file_path
        os.environ.setdefault("SIMILARITY_THRESHOLD", "0.5")
        
        # 创建最小化配置
        from read_chuck import EvaluationConfig
        config = EvaluationConfig(
            api_key="dummy",
            api_base="dummy",
            excel_file_path=os.getenv("EXCEL_FILE_PATH", "standardDataset/standardDataset.xlsx")
        )
        
        # 创建MRR评估器并运行评估
        evaluator = MRREvaluator(config)
        results = evaluator.run_evaluation()
        
        if "error" in results:
            return EvaluationResponse(
                success=False,
                message=f"MRR评估失败: {results['error']}"
            )
        
        # 格式化结果
        formatted_results = {
            "mrr": results.get("mrr", 0),
            "total_queries": results.get("total_queries", 0),
            "queries_with_relevant_chunks": results.get("queries_with_relevant_chunks", 0),
            "queries_without_relevant_chunks": results.get("queries_without_relevant_chunks", 0),
            "detailed_results": results.get("detailed_results", [])
        }
        
        return EvaluationResponse(
            success=True,
            message="MRR评估完成",
            data=formatted_results
        )
        
    except Exception as e:
        error_msg = f"MRR评估异常: {str(e)}"
        info_print(error_msg)
        traceback.print_exc()
        return EvaluationResponse(
            success=False,
            message=error_msg
        )

@app.post("/api/map/evaluate", response_model=EvaluationResponse)
async def run_map_evaluation(request: Optional[EvaluationRequest] = None):
    """运行MAP评估"""
    try:
        # 获取数据集文件路径
        dataset_file = "standardDataset.xlsx" if request is None else request.dataset_file
        excel_file_path = f"standardDataset/{dataset_file}"
        
        # 设置环境变量
        os.environ["EXCEL_FILE_PATH"] = excel_file_path
        os.environ.setdefault("SIMILARITY_THRESHOLD", "0.5")
        
        # 创建最小化配置
        from read_chuck import EvaluationConfig
        config = EvaluationConfig(
            api_key="dummy",
            api_base="dummy",
            excel_file_path=os.getenv("EXCEL_FILE_PATH", "standardDataset/standardDataset.xlsx")
        )
        
        # 创建MAP评估器并运行评估
        evaluator = MAPEvaluator(config)
        results = evaluator.run_evaluation()
        
        if "error" in results:
            return EvaluationResponse(
                success=False,
                message=f"MAP评估失败: {results['error']}"
            )
        
        # 格式化结果
        formatted_results = {
            "map": results.get("map", 0),
            "total_queries": results.get("total_queries", 0),
            "queries_with_relevant_chunks": results.get("queries_with_relevant_chunks", 0),
            "queries_without_relevant_chunks": results.get("queries_without_relevant_chunks", 0),
            "detailed_results": results.get("detailed_results", [])
        }
        
        return EvaluationResponse(
            success=True,
            message="MAP评估完成",
            data=formatted_results
        )
        
    except Exception as e:
        error_msg = f"MAP评估异常: {str(e)}"
        info_print(error_msg)
        traceback.print_exc()
        return EvaluationResponse(
            success=False,
            message=error_msg
        )

@app.post("/api/ndcg/evaluate", response_model=EvaluationResponse)
async def run_ndcg_evaluation(request: Optional[EvaluationRequest] = None):
    """运行NDCG评估"""
    try:
        # 获取数据集文件路径
        dataset_file = "standardDataset.xlsx" if request is None else request.dataset_file
        excel_file_path = f"standardDataset/{dataset_file}"
        
        # 设置环境变量
        os.environ["EXCEL_FILE_PATH"] = excel_file_path
        os.environ.setdefault("SIMILARITY_THRESHOLD", "0.5")
        
        # 创建最小化配置
        from read_chuck import EvaluationConfig
        config = EvaluationConfig(
            api_key="dummy",
            api_base="dummy",
            excel_file_path=os.getenv("EXCEL_FILE_PATH", "standardDataset/standardDataset.xlsx")
        )
        
        # 创建NDCG评估器并运行评估
        evaluator = NDCGEvaluator(config)
        results = evaluator.run_evaluation()
        
        if "error" in results:
            return EvaluationResponse(
                success=False,
                message=f"NDCG评估失败: {results['error']}"
            )
        
        # 格式化结果
        formatted_results = {
            "ndcg": results.get("avg_ndcg", 0),
            "total_queries": results.get("total_queries", 0),
            "queries_with_relevant_chunks": results.get("queries_with_relevant_chunks", 0),
            "queries_without_relevant_chunks": results.get("queries_without_relevant_chunks", 0),
            "detailed_results": results.get("detailed_results", [])
        }
        
        return EvaluationResponse(
            success=True,
            message="NDCG评估完成",
            data=formatted_results
        )
        
    except Exception as e:
        error_msg = f"NDCG评估异常: {str(e)}"
        info_print(error_msg)
        traceback.print_exc()
        return EvaluationResponse(
            success=False,
            message=error_msg
        )

@app.post("/api/bm25/evaluate", response_model=EvaluationResponse)
async def run_bm25_evaluation(request: Optional[EvaluationRequest] = None):
    """运行BM25评估"""
    global bm25_results
    
    try:
        # 获取数据集文件路径
        dataset_file = "standardDataset.xlsx" if request is None else request.dataset_file
        excel_file_path = f"standardDataset/{dataset_file}"
        
        # 创建配置
        config = EvaluationConfig(
            api_key=os.getenv("QWEN_API_KEY", "dummy_key"),
            api_base=os.getenv("QWEN_API_BASE", "dummy_base"),
            excel_file_path=excel_file_path
        )
        
        # 创建评估器并运行评估
        evaluator = BM25Evaluator(config)
        results = evaluator.run_evaluation()
        
        if "error" in results:
            return EvaluationResponse(
                success=False,
                message=f"BM25评估失败: {results['error']}"
            )
        
        # 计算F1-score
        f1_calculator = F1ScoreCalculator(config)
        f1_results = f1_calculator.calculate_f1_scores_from_bm25_results(results)
        
        # 格式化结果（包含BM25相关指标和F1-score）
        formatted_results = {
            "context_recall": results.get("avg_recall", 0),
            "context_precision": results.get("avg_precision", 0),
            "f1_score": f1_results.get("avg_f1", 0),
            "mrr": 0,  # 将在JavaScript中从MRR API获取
            "map": 0,  # 将在JavaScript中从MAP API获取
            "ndcg": 0,  # 将在JavaScript中从NDCG API获取
            "irrelevant_chunks": len(results.get("irrelevant_chunks", [])),
            "missed_chunks": len(results.get("missed_chunks", [])),
            "relevant_chunks": len(results.get("relevant_chunks", [])),
            "detailed_results": results.get("detailed_results", []),
            "total_samples": len(results.get("precision_scores", [])),
            "precision_scores": results.get("precision_scores", []),
            "recall_scores": results.get("recall_scores", []),
            "f1_scores": f1_results.get("f1_scores", [])
        }
        
        bm25_results = results
        info_print(f"🔍 调试: 设置bm25_results全局变量，包含{len(results.get('detailed_results', []))}个详细结果")
        
        return EvaluationResponse(
            success=True,
            message="BM25评估完成",
            data=formatted_results
        )
        
    except Exception as e:
        error_msg = f"BM25评估异常: {str(e)}"
        info_print(error_msg)
        traceback.print_exc()
        return EvaluationResponse(
            success=False,
            message=error_msg
        )

@app.get("/api/ragas/config", response_model=EvaluationResponse)
async def get_ragas_config():
    """获取Ragas评估指标配置"""
    try:
        config = RagasMetricsConfig.load()
        return EvaluationResponse(
            success=True,
            message="获取配置成功",
            data={
                "enabled_metrics": config.enabled_metrics
            }
        )
    except Exception as e:
        error_msg = f"获取Ragas配置失败: {str(e)}"
        info_print(error_msg)
        return EvaluationResponse(
            success=False,
            message=error_msg
        )

@app.post("/api/ragas/config", response_model=EvaluationResponse)
async def save_ragas_config(request: dict):
    """保存Ragas评估指标配置"""
    try:
        enabled_metrics = request.get("enabled_metrics", [])
        
        # 验证必选指标
        required = ['context_recall', 'context_precision']
        for metric in required:
            if metric not in enabled_metrics:
                return EvaluationResponse(
                    success=False,
                    message=f"必选指标 {metric} 不能取消"
                )
        
        # 保存配置
        config = RagasMetricsConfig(enabled_metrics=enabled_metrics)
        config.save()
        
        info_print(f"✅ Ragas配置已保存: {len(enabled_metrics)} 个指标")
        
        return EvaluationResponse(
            success=True,
            message=f"配置已保存，已选择 {len(enabled_metrics)} 个指标",
            data={
                "enabled_metrics": enabled_metrics
            }
        )
    except Exception as e:
        error_msg = f"保存Ragas配置失败: {str(e)}"
        info_print(error_msg)
        traceback.print_exc()
        return EvaluationResponse(
            success=False,
            message=error_msg
        )

@app.post("/api/ragas/evaluate", response_model=EvaluationResponse)
async def run_ragas_evaluation(request: Optional[EvaluationRequest] = None):
    """运行Ragas评估"""
    global ragas_results
    
    try:
        # 获取数据集文件路径
        dataset_file = "standardDataset.xlsx" if request is None else request.dataset_file
        excel_file_path = f"standardDataset/{dataset_file}"
        
        # 创建配置
        config = EvaluationConfig(
            api_key=os.getenv("QWEN_API_KEY"),
            api_base=os.getenv("QWEN_API_BASE"),
            model_name=os.getenv("QWEN_MODEL_NAME", "qwen-plus"),
            embedding_model=os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1"),
            use_ollama=os.getenv("USE_OLLAMA", "false").lower() == "true",
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            ollama_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma:300m"),
            ollama_llm_model=os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b"),
            excel_file_path=excel_file_path
        )
        
        # 验证配置
        if not config.api_key or not config.api_base:
            return EvaluationResponse(
                success=False,
                message="请设置QWEN_API_KEY和QWEN_API_BASE环境变量"
            )
        
        # 创建主控制器并运行评估
        controller = MainController(config)
        results = await controller.run_evaluation()
        
        if "error" in results:
            return EvaluationResponse(
                success=False,
                message=f"Ragas评估失败: {results['error']}"
            )
        
        # 格式化结果（不包含raw_results，避免序列化问题）
        formatted_results = {
            "context_recall": results.get("context_recall", 0),
            "context_precision": results.get("context_precision", 0),
            "faithfulness": results.get("faithfulness", 0),
            "answer_relevancy": results.get("answer_relevancy", 0),
            "context_entity_recall": results.get("context_entity_recall", 0),
            "context_relevance": results.get("context_relevance", 0),
            "answer_correctness": results.get("answer_correctness", 0),
            "answer_similarity": results.get("answer_similarity", 0),
            "fallback_mode": results.get("fallback_mode", False),
            "error_message": results.get("error_message", "")
        }
        
        # 保存完整的评估结果到全局变量
        global ragas_results
        ragas_results = {
            "context_recall": results.get("context_recall", 0),
            "context_precision": results.get("context_precision", 0),
            "faithfulness": results.get("faithfulness", 0),
            "answer_relevancy": results.get("answer_relevancy", 0),
            "context_entity_recall": results.get("context_entity_recall", 0),
            "context_relevance": results.get("context_relevance", 0),
            "answer_correctness": results.get("answer_correctness", 0),
            "answer_similarity": results.get("answer_similarity", 0),
            "raw_results": results.get("raw_results"),
            "fallback_mode": results.get("fallback_mode", False),
            "error_message": results.get("error_message", ""),
            "evaluation_completed": True,  # 标记评估已完成
            "evaluation_time": results.get("evaluation_time", None),
            "dataset_file": dataset_file  # 保存使用的数据集文件
        }
        
        info_print(f"✅ Ragas评估结果已保存到全局变量，fallback_mode: {ragas_results.get('fallback_mode', False)}")
        
        return EvaluationResponse(
            success=True,
            message="Ragas评估完成",
            data=formatted_results
        )
        
    except Exception as e:
        error_msg = f"Ragas评估异常: {str(e)}"
        info_print(error_msg)
        traceback.print_exc()
        return EvaluationResponse(
            success=False,
            message=error_msg
        )

@app.get("/api/bm25/details", response_model=EvaluationResponse)
async def get_bm25_details():
    """获取BM25评估详情"""
    global bm25_results
    
    info_print(f"🔍 调试: BM25详情API调用，bm25_results状态: {bm25_results is not None}")
    if bm25_results:
        info_print(f"🔍 调试: bm25_results包含{len(bm25_results.get('detailed_results', []))}个详细结果")
    
    if not bm25_results:
        return EvaluationResponse(
            success=False,
            message="请先运行BM25评估"
        )
    
    # 格式化详细结果
    details = []
    sample_analysis = {}
    
    # 组织不相关分块
    for chunk_info in bm25_results.get('irrelevant_chunks', []):
        row_idx = chunk_info['row_index']
        if row_idx not in sample_analysis:
            sample_analysis[row_idx] = {
                'user_input': chunk_info['user_input'],
                'irrelevant_chunks': [],
                'missed_chunks': [],
                'relevant_chunks': []
            }
        sample_analysis[row_idx]['irrelevant_chunks'].append(chunk_info)
    
    # 组织未召回分块
    for chunk_info in bm25_results.get('missed_chunks', []):
        row_idx = chunk_info['row_index']
        if row_idx not in sample_analysis:
            sample_analysis[row_idx] = {
                'user_input': chunk_info['user_input'],
                'irrelevant_chunks': [],
                'missed_chunks': [],
                'relevant_chunks': []
            }
        sample_analysis[row_idx]['missed_chunks'].append(chunk_info)
    
    # 组织相关分块（与不相关分块、未召回分块保持一致）
    for chunk_info in bm25_results.get('relevant_chunks', []):
        row_idx = chunk_info['row_index']
        if row_idx not in sample_analysis:
            sample_analysis[row_idx] = {
                'user_input': chunk_info['user_input'],
                'irrelevant_chunks': [],
                'missed_chunks': [],
                'relevant_chunks': []
            }
        sample_analysis[row_idx]['relevant_chunks'].append(chunk_info)
    
    # 转换为列表格式
    for sample_idx, (row_idx, data) in enumerate(sample_analysis.items(), 1):
        details.append({
            'sample_id': sample_idx,
            'row_index': row_idx + 1,
            'user_input': data['user_input'],
            'relevant_chunks': data['relevant_chunks'],
            'irrelevant_chunks': data['irrelevant_chunks'],
            'missed_chunks': data['missed_chunks']
        })
    
    return EvaluationResponse(
        success=True,
        message="获取BM25详情成功",
        data={'details': details}
    )

def get_chunk_ragas_scores(ragas_results, sample_id):
    """
    从RAGAS原始结果中获取指定样本每个分块的详细分数
    
    Args:
        ragas_results: RAGAS评估结果
        sample_id: 样本ID (1-based)
        
    Returns:
        dict: 包含每个分块评分的字典
    """
    try:
        raw_results = ragas_results.get('raw_results')
        if not raw_results:
            return {}
        
        chunk_scores = {}
        
        # 从traces中获取chunk-level评分
        if isinstance(raw_results, dict) and 'traces' in raw_results:
            traces = raw_results['traces']
            
            # sample_id是1-based，需要转换为0-based索引
            sample_index = sample_id - 1
            
            if isinstance(traces, list) and 0 <= sample_index < len(traces):
                trace = traces[sample_index]
                
                if isinstance(trace, dict) and 'scores' in trace:
                    scores = trace['scores']
                    
                    # 提取所有指标的分数
                    if isinstance(scores, dict):
                        chunk_scores = {
                            'faithfulness': scores.get('faithfulness'),
                            'answer_relevancy': scores.get('answer_relevancy'),
                            'context_precision': scores.get('context_precision'),
                            'context_recall': scores.get('context_recall'),
                            'context_entity_recall': scores.get('context_entity_recall'),
                            'context_relevance': scores.get('nv_context_relevance'),
                            'answer_correctness': scores.get('answer_correctness'),
                            'answer_similarity': scores.get('answer_similarity')
                        }
        
        return chunk_scores
        
    except Exception as e:
        info_print(f"获取样本{sample_id}的分块RAGAS分数时出错: {e}")
        return {}

def get_sample_ragas_scores(ragas_results, sample_id):
    """
    从RAGAS原始结果中获取指定样本的详细分数
    
    Args:
        ragas_results: RAGAS评估结果
        sample_id: 样本ID (1-based)
        
    Returns:
        tuple: (precision, recall) 或 (None, None) 如果无法获取
    """
    try:
        raw_results = ragas_results.get('raw_results')
        if not raw_results:
            return None, None
        
        # 处理不同的raw_results格式
        precision = None
        recall = None
        
        # 方式1: 如果是EvaluationResult对象，使用_scores_dict属性
        if hasattr(raw_results, '_scores_dict') and raw_results._scores_dict:
            # sample_id是1-based，需要转换为0-based索引
            sample_index = sample_id - 1
            
            # 获取context_precision和context_recall的所有样本分数
            precision_scores = raw_results._scores_dict.get('context_precision', [])
            recall_scores = raw_results._scores_dict.get('context_recall', [])
            
            if (0 <= sample_index < len(precision_scores) and 
                0 <= sample_index < len(recall_scores)):
                
                precision = precision_scores[sample_index]
                recall = recall_scores[sample_index]
        
        # 方式2: 如果是字典格式，从scores字段中获取
        elif isinstance(raw_results, dict) and 'scores' in raw_results:
            scores = raw_results['scores']
            
            # 如果scores是DataFrame
            if hasattr(scores, 'iloc'):
                # sample_id是1-based，需要转换为0-based索引
                sample_index = sample_id - 1
                
                if (0 <= sample_index < len(scores) and 
                    'context_precision' in scores.columns and 
                    'context_recall' in scores.columns):
                    
                    precision = scores.iloc[sample_index]['context_precision']
                    recall = scores.iloc[sample_index]['context_recall']
            
            # 如果scores是列表格式（每个元素是一个字典）
            elif isinstance(scores, list):
                # sample_id是1-based，需要转换为0-based索引
                sample_index = sample_id - 1
                
                if (0 <= sample_index < len(scores) and 
                    isinstance(scores[sample_index], dict)):
                    
                    sample_scores = scores[sample_index]
                    precision = sample_scores.get('context_precision')
                    recall = sample_scores.get('context_recall')
        
        # 检查分数是否有效（不是NaN或None）
        if (precision is not None and not (isinstance(precision, float) and str(precision) == 'nan') and
            recall is not None and not (isinstance(recall, float) and str(recall) == 'nan')):
            return float(precision), float(recall)
        
        return None, None
        
    except Exception as e:
        info_print(f"获取样本{sample_id}的RAGAS分数时出错: {e}")
        return None, None

def generate_sample_summary(details, ragas_results):
    """生成样本汇总分析"""
    summary = {
        'overall_metrics': {},
        'sample_analysis': []
    }
    
    # 获取整体评估指标
    if ragas_results and ragas_results.get('evaluation_completed'):
        summary['overall_metrics'] = {
            'context_precision': ragas_results.get('context_precision', 0),
            'context_recall': ragas_results.get('context_recall', 0),
            'faithfulness': ragas_results.get('faithfulness', 0),
            'answer_relevancy': ragas_results.get('answer_relevancy', 0)
        }
    
    # 分析每个样本
    for detail in details:
        sample_id = detail['sample_id']
        user_input = detail['user_input']
        relevant_chunks = detail['relevant_chunks']
        irrelevant_chunks = detail['irrelevant_chunks']
        missed_chunks = detail['missed_chunks']
        
        # 计算样本统计
        total_retrieved = len(relevant_chunks) + len(irrelevant_chunks)
        total_reference = len(relevant_chunks) + len(missed_chunks)
        
        # 尝试从RAGAS原始结果中获取每个样本的真实分数
        sample_precision, sample_recall = get_sample_ragas_scores(ragas_results, sample_id)
        
        # 获取该样本的所有RAGAS评分
        chunk_ragas_scores = get_chunk_ragas_scores(ragas_results, sample_id)
        
        # 如果无法获取RAGAS分数，回退到分块匹配计算
        if sample_precision is None or sample_recall is None:
            sample_precision = len(relevant_chunks) / total_retrieved if total_retrieved > 0 else 0
            sample_recall = len(relevant_chunks) / total_reference if total_reference > 0 else 0
        
        # 为每个分块添加RAGAS评分
        enhanced_relevant_chunks = []
        for chunk in relevant_chunks:
            enhanced_chunk = chunk.copy()
            enhanced_chunk['ragas_scores'] = chunk_ragas_scores
            enhanced_relevant_chunks.append(enhanced_chunk)
        
        enhanced_irrelevant_chunks = []
        for chunk in irrelevant_chunks:
            enhanced_chunk = chunk.copy()
            enhanced_chunk['ragas_scores'] = chunk_ragas_scores
            enhanced_irrelevant_chunks.append(enhanced_chunk)
        
        enhanced_missed_chunks = []
        for chunk in missed_chunks:
            enhanced_chunk = chunk.copy()
            enhanced_chunk['ragas_scores'] = chunk_ragas_scores
            enhanced_missed_chunks.append(enhanced_chunk)
        
        # 生成样本分析描述
        analysis_desc = generate_sample_description(
            user_input, sample_precision, sample_recall, 
            len(relevant_chunks), len(irrelevant_chunks), len(missed_chunks), sample_id
        )
        
        summary['sample_analysis'].append({
            'sample_id': sample_id,
            'user_input': user_input,
            'precision': sample_precision,
            'recall': sample_recall,
            'relevant_chunks': len(relevant_chunks),
            'irrelevant_chunks': len(irrelevant_chunks),
            'missed_chunks': len(missed_chunks),
            'analysis': analysis_desc,
            'ragas_scores': chunk_ragas_scores,
            'enhanced_relevant_chunks': enhanced_relevant_chunks,
            'enhanced_irrelevant_chunks': enhanced_irrelevant_chunks,
            'enhanced_missed_chunks': enhanced_missed_chunks
        })
    
    return summary

def generate_sample_description(user_input, precision, recall, relevant_count, irrelevant_count, missed_count, sample_id=None):
    """生成样本分析描述"""
    # 截取查询的前30个字符
    query_short = user_input[:30] + "..." if len(user_input) > 30 else user_input
    
    # 使用样本ID或默认描述
    sample_desc = f"样本{sample_id}" if sample_id else "该样本"
    
    if precision >= 0.9 and recall >= 0.9:
        return f"{sample_desc}: 检索内容完全相关且完整，Precision: {precision*100:.1f}%, Recall: {recall*100:.1f}%"
    elif precision >= 0.7 and recall >= 0.7:
        return f"{sample_desc}: 检索质量良好，但存在少量不相关内容，Precision: {precision*100:.1f}%, Recall: {recall*100:.1f}%"
    elif irrelevant_count > 0 and missed_count > 0:
        return f"{sample_desc}: 检索内容不完整且包含不相关信息，缺少{missed_count}个相关分块，Precision: {precision*100:.1f}%, Recall: {recall*100:.1f}%"
    elif irrelevant_count > 0:
        return f"{sample_desc}: 检索到{irrelevant_count}个不相关分块，但相关分块完整，Precision: {precision*100:.1f}%, Recall: {recall*100:.1f}%"
    elif missed_count > 0:
        return f"{sample_desc}: 检索内容不完整，缺少{missed_count}个相关分块，Precision: {precision*100:.1f}%, Recall: {recall*100:.1f}%"
    else:
        return f"{sample_desc}: 检索质量中等，Precision: {precision*100:.1f}%, Recall: {recall*100:.1f}%"

@app.get("/api/ragas/details", response_model=EvaluationResponse)
async def get_ragas_details():
    """获取Ragas评估详情"""
    global ragas_results
    
    # 检查是否有评估结果
    if not ragas_results or not ragas_results.get('evaluation_completed', False):
        return EvaluationResponse(
            success=False,
            message="请先运行Ragas评估"
        )
    
    # 检查是否是fallback模式
    is_fallback = ragas_results.get('fallback_mode', False)
    if is_fallback:
        return EvaluationResponse(
            success=False,
            message=f"Ragas评估处于fallback模式，无法提供详细分析。错误信息: {ragas_results.get('error_message', '未知错误')}"
        )
    
    try:
        # 获取评估时使用的数据集文件
        dataset_file = ragas_results.get('dataset_file', 'standardDataset.xlsx')
        excel_file_path = f"standardDataset/{dataset_file}"
        
        info_print(f"📊 查看Ragas明细，使用数据集: {dataset_file}")
        
        # 从原始数据中重新加载并分析
        config = EvaluationConfig(
            api_key=os.getenv("QWEN_API_KEY"),
            api_base=os.getenv("QWEN_API_BASE"),
            model_name=os.getenv("QWEN_MODEL_NAME", "qwen-plus"),
            embedding_model=os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1"),
            excel_file_path=excel_file_path  # 使用评估时的数据集
        )
        
        # 重新加载数据进行分析
        from read_chuck import DataLoader, TextProcessor
        data_loader = DataLoader(config)
        text_processor = TextProcessor(config)
        
        df = data_loader.load_excel_data()
        if df is None:
            return EvaluationResponse(
                success=False,
                message="无法加载数据文件"
            )
        
        # 处理数据
        df = text_processor.parse_context_columns(df)
        
        # 分析每个样本的分块情况
        details = []
        for idx, row in df.iterrows():
            user_input = str(row['user_input']) if pd.notna(row['user_input']) else ""
            retrieved_contexts = row['retrieved_contexts']
            reference_contexts = row['reference_contexts']
            
            if not retrieved_contexts or not reference_contexts:
                continue
            
            # 使用Ragas评估结果进行相关性分析
            relevant_chunks = []
            irrelevant_chunks = []
            missed_chunks = []
            
            # 从环境变量读取相似度阈值
            similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
            
            # 分析相关和不相关分块
            for i, retrieved_chunk in enumerate(retrieved_contexts):
                # 使用更智能的文本相似度计算
                is_relevant = False
                max_similarity = 0
                best_ref_idx = -1
                
                for j, ref_chunk in enumerate(reference_contexts):
                    # 计算文本相似度
                    similarity = calculate_text_similarity(retrieved_chunk, ref_chunk)
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_ref_idx = j
                
                # 如果相似度足够高，认为相关
                if max_similarity > similarity_threshold:
                    is_relevant = True
                    relevant_chunks.append({
                        'retrieved_chunk': retrieved_chunk,
                        'reference_chunk': reference_contexts[best_ref_idx] if best_ref_idx >= 0 else "",
                        'retrieved_idx': i,
                        'reference_idx': best_ref_idx,
                        'relevance_score': max_similarity
                    })
                else:
                    irrelevant_chunks.append({
                        'retrieved_chunk': retrieved_chunk,
                        'retrieved_idx': i,
                        'max_relevance': max_similarity
                    })
            
            # 分析未召回分块
            # 未召回分块 = reference_contexts中存在的分块，而retrieved_contexts中不存在的分块
            matched_references = set()
            for chunk in relevant_chunks:
                if 'reference_idx' in chunk:
                    matched_references.add(chunk['reference_idx'])
            
            for j, ref_chunk in enumerate(reference_contexts):
                if j not in matched_references:
                    # 找到该参考分块与所有检索分块的最大相似度
                    max_similarity = 0
                    best_retrieved_idx = -1
                    for i, retrieved_chunk in enumerate(retrieved_contexts):
                        similarity = calculate_text_similarity(retrieved_chunk, ref_chunk)
                        if similarity > max_similarity:
                            max_similarity = similarity
                            best_retrieved_idx = i
                    
                    # 如果相似度低于阈值，认为是未召回的分块
                    if max_similarity < similarity_threshold:
                        missed_chunks.append({
                            'reference_chunk': ref_chunk,
                            'reference_idx': j,
                            'best_retrieved_idx': best_retrieved_idx,
                            'max_relevance': max_similarity
                        })
            
            details.append({
                'sample_id': len(details) + 1,
                'row_index': idx + 1,
                'user_input': user_input,
                'relevant_chunks': relevant_chunks,
                'irrelevant_chunks': irrelevant_chunks,
                'missed_chunks': missed_chunks
            })
        
        # 生成样本汇总分析
        sample_summary = generate_sample_summary(details, ragas_results)
        
        return EvaluationResponse(
            success=True,
            message="获取Ragas详情成功",
            data={
                'details': details,
                'sample_summary': sample_summary,
                'ragas_raw_results': ragas_results.get('raw_results', None)
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return EvaluationResponse(
            success=False,
            message=f"获取Ragas详情失败: {str(e)}"
        )

@app.post("/api/save-bm25-combined", response_model=SaveEvaluationResponse)
async def save_bm25_combined(request: BM25CombinedResults):
    """保存包含所有指标的BM25评估结果"""
    try:
        # 构建BM25结果数据
        bm25_data = {
            'avg_precision': request.context_precision,
            'avg_recall': request.context_recall,
            'avg_f1': request.f1_score,
            'mrr': request.mrr,
            'map': request.map,
            'ndcg': request.ndcg,
            'total_samples': request.total_samples,
            'irrelevant_chunks': [{}] * request.irrelevant_chunks,  # 创建空数组
            'missed_chunks': [{}] * request.missed_chunks,  # 创建空数组
            'relevant_chunks': [{}] * request.relevant_chunks  # 创建空数组
        }
        
        # 保存到数据库
        evaluation_id = db.save_bm25_result(bm25_data, request.description)
        
        if evaluation_id:
            return SaveEvaluationResponse(
                success=True,
                message="BM25评估结果保存成功",
                evaluation_id=evaluation_id
            )
        else:
            return SaveEvaluationResponse(
                success=False,
                message="保存BM25评估结果失败"
            )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return SaveEvaluationResponse(
            success=False,
            message=f"保存BM25评估结果失败: {str(e)}"
        )

@app.post("/api/save-evaluation", response_model=SaveEvaluationResponse)
async def save_evaluation(request: SaveEvaluationRequest):
    """保存评估结果到数据库"""
    try:
        # 检查评估类型
        if request.evaluation_type not in ["BM25", "RAGAS"]:
            return SaveEvaluationResponse(
                success=False,
                message="无效的评估类型，必须是BM25或RAGAS"
            )
        
        # 获取对应的评估结果
        if request.evaluation_type == "BM25":
            if not bm25_results:
                return SaveEvaluationResponse(
                    success=False,
                    message="没有BM25评估结果可保存，请先运行评估"
                )
            # 使用原始的BM25结果，但需要确保包含所有指标
            results = bm25_results.copy()
            
            # 如果结果中没有新指标，尝试从全局变量获取
            if 'mrr' not in results or 'map' not in results or 'ndcg' not in results:
                info_print("⚠️ BM25结果中缺少MRR/MAP/NDCG指标，使用默认值0")
                results.setdefault('mrr', 0)
                results.setdefault('map', 0)
                results.setdefault('ndcg', 0)
        else:  # RAGAS
            if not ragas_results:
                return SaveEvaluationResponse(
                    success=False,
                    message="没有Ragas评估结果可保存，请先运行评估"
                )
            results = ragas_results
        
        # 保存到数据库
        if request.evaluation_type == "BM25":
            evaluation_id = db.save_bm25_result(results, request.description)
        else:
            # 对于Ragas评估，先提取统计数据，然后保存
            info_print("📊 提取Ragas评估统计数据...")
            stats = db.extract_ragas_statistics(results)
            info_print(f"✅ 统计数据提取完成: {stats}")
            evaluation_id = db.save_ragas_result(results, request.description)
        
        if evaluation_id:
            return SaveEvaluationResponse(
                success=True,
                message=f"{request.evaluation_type}评估结果保存成功",
                evaluation_id=evaluation_id
            )
        else:
            return SaveEvaluationResponse(
                success=False,
                message="保存评估结果失败"
            )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return SaveEvaluationResponse(
            success=False,
            message=f"保存评估结果失败: {str(e)}"
        )

@app.get("/api/evaluation-history")
async def get_evaluation_history():
    """获取评估历史记录"""
    try:
        history = db.get_evaluation_history()
        return EvaluationResponse(
            success=True,
            message="获取评估历史成功",
            data={'history': history}
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取评估历史失败: {str(e)}"
        )

@app.get("/api/ragas-status")
async def get_ragas_status():
    """获取Ragas评估状态"""
    global ragas_results
    
    try:
        if not ragas_results:
            return EvaluationResponse(
                success=False,
                message="没有Ragas评估结果",
                data={'has_results': False}
            )
        
        return EvaluationResponse(
            success=True,
            message="Ragas评估状态正常",
            data={
                'has_results': True,
                'evaluation_completed': ragas_results.get('evaluation_completed', False),
                'fallback_mode': ragas_results.get('fallback_mode', False),
                'error_message': ragas_results.get('error_message', ''),
                'has_metrics': any(ragas_results.get(metric) is not None for metric in 
                                 ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall'])
            }
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"检查Ragas状态失败: {str(e)}",
            data={'has_results': False}
        )

@app.get("/api/database-status")
async def get_database_status():
    """获取数据库连接状态"""
    try:
        is_connected = test_connection()
        if is_connected:
            stats = db.get_database_statistics()
            return EvaluationResponse(
                success=True,
                message="数据库连接正常",
                data={'connected': True, 'statistics': stats}
            )
        else:
            return EvaluationResponse(
                success=False,
                message="数据库连接失败",
                data={'connected': False}
            )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"检查数据库状态失败: {str(e)}",
            data={'connected': False}
        )

@app.post("/api/init-database")
async def init_database_endpoint():
    """初始化数据库表"""
    try:
        success = init_database()
        if success:
            return EvaluationResponse(
                success=True,
                message="数据库表初始化成功"
            )
        else:
            return EvaluationResponse(
                success=False,
                message="数据库表初始化失败"
            )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"数据库表初始化失败: {str(e)}"
        )

# 历史数据分析API接口
@app.get("/api/history/bm25/precision")
@cache_response(cache_instance=get_history_cache())
async def get_bm25_precision_history():
    """获取BM25准确率历史数据（带缓存）"""
    try:
        from database.db_service import get_evaluation_history
        
        # 获取BM25评估历史数据
        data = get_evaluation_history('BM25', 'context_precision')
        
        return EvaluationResponse(
            success=True,
            message="获取BM25准确率历史数据成功",
            data={"history": data}
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取BM25准确率历史数据失败: {str(e)}"
        )

@app.get("/api/history/bm25/recall")
@cache_response(cache_instance=get_history_cache())
async def get_bm25_recall_history():
    """获取BM25召回率历史数据（带缓存）"""
    try:
        from database.db_service import get_evaluation_history
        
        # 获取BM25评估历史数据
        data = get_evaluation_history('BM25', 'context_recall')
        
        return EvaluationResponse(
            success=True,
            message="获取BM25召回率历史数据成功",
            data={"history": data}
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取BM25召回率历史数据失败: {str(e)}"
        )

@app.get("/api/history/bm25/f1")
@cache_response(cache_instance=get_history_cache())
async def get_bm25_f1_history():
    """获取BM25 F1-Score历史数据（带缓存）"""
    try:
        from database.db_service import get_evaluation_history
        
        # 获取BM25评估历史数据
        data = get_evaluation_history('BM25', 'f1_score')
        
        return EvaluationResponse(
            success=True,
            message="获取BM25 F1-Score历史数据成功",
            data={"history": data}
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取BM25 F1-Score历史数据失败: {str(e)}"
        )

@app.get("/api/history/bm25/ndcg")
@cache_response(cache_instance=get_history_cache())
async def get_bm25_ndcg_history():
    """获取BM25 NDCG历史数据（带缓存）"""
    try:
        from database.db_service import get_evaluation_history
        
        # 获取BM25评估历史数据
        data = get_evaluation_history('BM25', 'ndcg')
        
        return EvaluationResponse(
            success=True,
            message="获取BM25 NDCG历史数据成功",
            data={"history": data}
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取BM25 NDCG历史数据失败: {str(e)}"
        )

@app.get("/api/history/ragas/precision")
@cache_response(cache_instance=get_history_cache())
async def get_ragas_precision_history():
    """获取Ragas准确率历史数据（带缓存）"""
    try:
        from database.db_service import get_evaluation_history
        
        # 获取Ragas评估历史数据
        data = get_evaluation_history('RAGAS', 'context_precision')
        
        return EvaluationResponse(
            success=True,
            message="获取Ragas准确率历史数据成功",
            data={"history": data}
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取Ragas准确率历史数据失败: {str(e)}"
        )

@app.get("/api/history/ragas/recall")
@cache_response(cache_instance=get_history_cache())
async def get_ragas_recall_history():
    """获取Ragas召回率历史数据（带缓存）"""
    try:
        from database.db_service import get_evaluation_history
        
        # 获取Ragas评估历史数据
        data = get_evaluation_history('RAGAS', 'context_recall')
        
        return EvaluationResponse(
            success=True,
            message="获取Ragas召回率历史数据成功",
            data={"history": data}
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取Ragas召回率历史数据失败: {str(e)}"
        )

@app.get("/api/history/stats")
@cache_response(cache_instance=get_stats_cache())
async def get_history_stats():
    """获取历史数据统计概览（带缓存）"""
    try:
        from database.db_service import get_evaluation_stats
        
        # 获取统计概览数据
        stats = get_evaluation_stats()
        
        return EvaluationResponse(
            success=True,
            message="获取历史数据统计成功",
            data=stats
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取历史数据统计失败: {str(e)}"
        )

@app.get("/api/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        stats = get_all_cache_stats()
        return EvaluationResponse(
            success=True,
            message="获取缓存统计成功",
            data=stats
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取缓存统计失败: {str(e)}"
        )

@app.post("/api/cache/clear")
async def clear_cache():
    """清空所有缓存"""
    try:
        cleared_counts = clear_all_caches()
        return EvaluationResponse(
            success=True,
            message=f"缓存已清空，共清除 {cleared_counts['total']} 项",
            data=cleared_counts
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"清空缓存失败: {str(e)}"
        )

@app.get("/api/history/all")
@cache_response(cache_instance=get_history_cache())
async def get_all_history_data():
    """
    批量获取所有历史数据（优化版）
    一次性返回所有图表需要的数据，减少API调用次数
    """
    try:
        from database.db_service import get_evaluation_history
        
        # 批量查询所有数据
        result = {
            "bm25": {
                "precision": get_evaluation_history('BM25', 'context_precision'),
                "recall": get_evaluation_history('BM25', 'context_recall'),
                "f1": get_evaluation_history('BM25', 'f1_score'),
                "ndcg": get_evaluation_history('BM25', 'ndcg')
            },
            "ragas": {
                "precision": get_evaluation_history('RAGAS', 'context_precision'),
                "recall": get_evaluation_history('RAGAS', 'context_recall')
            }
        }
        
        return EvaluationResponse(
            success=True,
            message="批量获取历史数据成功",
            data=result
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"批量获取历史数据失败: {str(e)}"
        )

@app.get("/api/embedding-config")
async def get_embedding_config():
    """获取当前embedding模型配置"""
    try:
        # 优先从.env文件读取，然后从环境变量读取
        config = {
            "use_ollama": get_env_value("USE_OLLAMA", os.getenv("USE_OLLAMA", "false")).lower() == "true",
            "ollama_url": get_env_value("OLLAMA_URL", os.getenv("OLLAMA_URL", "http://localhost:11434")),
            "ollama_model": get_env_value("OLLAMA_EMBEDDING_MODEL", os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma:300m")),
            "ollama_llm_model": get_env_value("OLLAMA_LLM_MODEL", os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b")),
            "qwen_embedding_model": get_env_value("QWEN_EMBEDDING_MODEL", os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1")),
            "qwen_api_key": get_env_value("QWEN_API_KEY", os.getenv("QWEN_API_KEY", "")),
            "openai_api_key": get_env_value("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        }
        
        return EvaluationResponse(
            success=True,
            message="获取embedding配置成功",
            data=config
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取embedding配置失败: {str(e)}"
        )

class EmbeddingConfigRequest(BaseModel):
    """模型配置请求模型"""
    use_ollama: bool
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "embeddinggemma:300m"
    ollama_llm_model: str = "qwen2.5:7b"
    qwen_api_key: str = ""

@app.post("/api/embedding-config")
async def update_embedding_config(request: EmbeddingConfigRequest):
    """更新embedding模型配置"""
    try:
        # 更新环境变量（仅在当前会话中有效）
        os.environ["USE_OLLAMA"] = str(request.use_ollama).lower()
        os.environ["OLLAMA_URL"] = request.ollama_url
        os.environ["OLLAMA_EMBEDDING_MODEL"] = request.ollama_model
        os.environ["OLLAMA_LLM_MODEL"] = request.ollama_llm_model
        os.environ["QWEN_API_KEY"] = request.qwen_api_key
        
        # 如果提供了Qwen API Key，也更新OPENAI_API_KEY（用于兼容性）
        if request.qwen_api_key:
            os.environ["OPENAI_API_KEY"] = request.qwen_api_key
        
        # 同时更新.env文件
        env_updates = {
            "USE_OLLAMA": str(request.use_ollama).lower(),
            "OLLAMA_URL": request.ollama_url,
            "OLLAMA_EMBEDDING_MODEL": request.ollama_model,
            "OLLAMA_LLM_MODEL": request.ollama_llm_model,
            "QWEN_API_KEY": request.qwen_api_key
        }
        
        if request.qwen_api_key:
            env_updates["OPENAI_API_KEY"] = request.qwen_api_key
        
        update_env_file(env_updates)
        
        return EvaluationResponse(
            success=True,
            message="Embedding配置更新成功"
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"更新embedding配置失败: {str(e)}"
        )

@app.get("/api/dataset-files")
async def get_dataset_files_api():
    """获取standardDataset目录下的所有数据集文件"""
    try:
        result = get_dataset_files()
        return result
    except Exception as e:
        return {"success": False, "data": [], "message": f"获取数据集文件列表失败: {str(e)}"}

@app.post("/api/upload-document")
async def upload_document_api(file: UploadFile = File(...)):
    """上传待评测的文档"""
    try:
        # 检查文件类型
        if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return EvaluationResponse(
                success=False,
                message="只支持Excel文档格式(.xlsx, .xls)"
            )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            # 读取上传的文件内容
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 调用上传处理函数，传入原始文件名用于生成时间戳文件名
            result = upload_document(temp_file_path, original_filename=file.filename)
            
            if result["success"]:
                return EvaluationResponse(
                    success=True,
                    message=result["message"],
                    data={
                        "file_path": result.get("file_path"),
                        "file_size": result.get("file_size"),
                        "validation": result.get("validation")
                    }
                )
            else:
                return EvaluationResponse(
                    success=False,
                    message=result["message"]
                )
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        info_print(f"上传文档异常: {error_details}")
        return EvaluationResponse(
            success=False,
            message=f"上传文档失败: {str(e)}"
        )

@app.get("/api/upload-info")
async def get_upload_info_api():
    """获取上传文档信息"""
    try:
        info = get_upload_info()
        return EvaluationResponse(
            success=True,
            message="获取上传信息成功",
            data=info
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"获取上传信息失败: {str(e)}"
        )

@app.delete("/api/uploaded-document")
async def delete_uploaded_document_api():
    """删除已上传的文档"""
    try:
        result = delete_uploaded_file()
        return EvaluationResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        return EvaluationResponse(
            success=False,
            message=f"删除文档失败: {str(e)}"
        )

@app.get("/api/dataset/download-template")
async def download_template():
    """下载标准数据集模版文件"""
    try:
        # 标准数据集模版文件路径
        template_path = "standardDataset/standardDataset.xlsx"
        
        # 检查文件是否存在
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="模版文件不存在")
        
        info_print(f"📥 下载模版文件: {template_path}")
        
        # 返回文件响应
        return FileResponse(
            path=template_path,
            filename="standardDataset.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=standardDataset.xlsx"
            }
        )
    except Exception as e:
        error_msg = f"下载模版失败: {str(e)}"
        info_print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# 知识库文档上传相关API端点

@app.post("/api/upload-knowledge-document")
async def upload_knowledge_document_api(file: UploadFile = File(...)):
    """上传知识库文档"""
    try:
        # 验证文件类型
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md']
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            return {
                "success": False,
                "message": f"不支持的文件格式: {file_extension}。支持的格式: {', '.join(allowed_extensions)}"
            }
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 调用上传函数
            result = upload_knowledge_document(temp_file_path, file.filename)
            return result
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        return {
            "success": False,
            "message": f"上传失败: {str(e)}"
        }

@app.get("/api/knowledge-documents")
async def get_knowledge_documents_api():
    """获取知识库文档列表"""
    try:
        result = get_knowledge_documents()
        return result
    except Exception as e:
        return {"success": False, "message": f"获取文档列表失败: {str(e)}"}

@app.delete("/api/knowledge-documents/{filename}")
async def delete_knowledge_document_api(filename: str):
    """删除指定的知识库文档"""
    try:
        result = delete_knowledge_document(filename)
        return result
    except Exception as e:
        return {"success": False, "message": f"删除文档失败: {str(e)}"}

# 构建数据集API端点

@app.post("/api/build-dataset")
async def build_dataset_api():
    """构建标准数据集"""
    try:
        # 调用构建数据集函数
        result = await build_standard_dataset()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"构建数据集失败: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
