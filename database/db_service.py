"""
数据库操作服务
兼容MySQL和SQLite两种数据库
"""
from typing import List, Optional, Dict, Any
import os
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from database.db_config import get_db_session
# 移除对EvaluationResult模型的依赖，因为我们现在使用独立的表

class DatabaseService:
    """数据库操作服务类"""
    
    @staticmethod
    def save_bm25_result(results: Dict[str, Any], description: str = "") -> Optional[int]:
        """保存BM25评估结果到独立的bm25_evaluations表"""
        try:
            with get_db_session() as session:
                # 提取统计数据
                total_samples = results.get('total_samples', 0)
                irrelevant_chunks_count = len(results.get('irrelevant_chunks', []))
                missed_chunks_count = len(results.get('missed_chunks', []))
                
                # 提取指标数据
                context_precision = results.get('avg_precision', 0)
                context_recall = results.get('avg_recall', 0)
                f1_score = results.get('avg_f1', 0)
                mrr = results.get('mrr', 0)
                map_score = results.get('map', 0)
                ndcg = results.get('ndcg', 0)
                
                # 构建SQL查询，兼容MySQL和SQLite
                sql = """
                INSERT INTO bm25_evaluations 
                (evaluation_time, description, context_precision, context_recall, 
                 f1_score, mrr, map, ndcg, total_samples, irrelevant_chunks_count, missed_chunks_count)
                VALUES (CURRENT_TIMESTAMP, :description, :context_precision, :context_recall, 
                 :f1_score, :mrr, :map_score, :ndcg, :total_samples, :irrelevant_chunks_count, :missed_chunks_count)
                """
                
                result = session.execute(text(sql), {
                    'description': description,
                    'context_precision': context_precision,
                    'context_recall': context_recall,
                    'f1_score': f1_score,
                    'mrr': mrr,
                    'map_score': map_score,
                    'ndcg': ndcg,
                    'total_samples': total_samples,
                    'irrelevant_chunks_count': irrelevant_chunks_count,
                    'missed_chunks_count': missed_chunks_count
                })
                session.commit()
                
                # 获取插入的ID
                # 对于SQLAlchemy，我们需要重新查询获取ID
                try:
                    # MySQL
                    id_result = session.execute(text("SELECT LAST_INSERT_ID()"))
                except:
                    # SQLite
                    id_result = session.execute(text("SELECT last_insert_rowid()"))
                row = id_result.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"保存BM25结果失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def extract_ragas_statistics(results: Dict[str, Any]) -> Dict[str, int]:
        """
        从Ragas评估结果中提取统计数据
        
        Args:
            results: Ragas评估结果
            
        Returns:
            Dict[str, int]: 包含total_samples, irrelevant_chunks_count, missed_chunks_count的字典
        """
        try:
            # 尝试从raw_results中获取详情数据
            raw_results = results.get('raw_results', {})
            total_samples = 0
            irrelevant_chunks_count = 0
            missed_chunks_count = 0
            
            # 方法1: 从raw_results的details中提取
            if raw_results and isinstance(raw_results, dict):
                if 'details' in raw_results:
                    details_list = raw_results['details']
                    total_samples = len(details_list)
                    irrelevant_chunks_count = sum(len(sample.get('irrelevant_chunks', [])) for sample in details_list)
                    missed_chunks_count = sum(len(sample.get('missed_chunks', [])) for sample in details_list)
                else:
                    # 如果没有details，尝试从其他字段获取
                    total_samples = raw_results.get('total_samples', 0)
                    irrelevant_chunks_count = raw_results.get('irrelevant_chunks_count', 0)
                    missed_chunks_count = raw_results.get('missed_chunks_count', 0)
            
            # 方法2: 如果raw_results中没有数据，尝试从原始数据重新计算
            if total_samples == 0:
                print("📊 从原始数据重新计算Ragas统计数据...")
                try:
                    # 重新加载数据进行分析
                    from read_chuck import EvaluationConfig, DataLoader, TextProcessor
                    
                    config = EvaluationConfig(
                        api_key=os.getenv("QWEN_API_KEY", ""),
                        api_base=os.getenv("QWEN_API_BASE", ""),
                        model_name=os.getenv("QWEN_MODEL_NAME", "qwen-plus"),
                        embedding_model=os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1"),
                        excel_file_path=os.getenv("EXCEL_FILE_PATH", "standardDataset/standardDataset.xlsx")
                    )
                    
                    data_loader = DataLoader(config)
                    text_processor = TextProcessor(config)
                    
                    df = data_loader.load_excel_data()
                    if df is not None:
                        df = text_processor.parse_context_columns(df)
                        
                        # 过滤空行数据
                        filtered_rows = []
                        for i in range(len(df)):
                            retrieved_contexts = df['retrieved_contexts'].iloc[i]
                            reference_contexts = df['reference_contexts'].iloc[i]
                            user_input = df['user_input'].iloc[i] if 'user_input' in df.columns else ""
                            response = df['response'].iloc[i] if 'response' in df.columns else ""
                            
                            if not text_processor.is_empty_row_data(retrieved_contexts, reference_contexts, user_input, response):
                                filtered_rows.append(i)
                        
                        # 使用过滤后的数据
                        df = df.iloc[filtered_rows].copy()
                        total_samples = len(df)
                        
                        # 分析每个样本的分块情况
                        for idx, row in df.iterrows():
                            retrieved_contexts = row['retrieved_contexts']
                            reference_contexts = row['reference_contexts']
                            
                            if not retrieved_contexts or not reference_contexts:
                                continue
                            
                            # 分析不相关分块（简化版本）
                            for retrieved_chunk in retrieved_contexts:
                                is_relevant = False
                                for ref_chunk in reference_contexts:
                                    # 简单的关键词匹配
                                    retrieved_words = set(str(retrieved_chunk).lower().split())
                                    ref_words = set(str(ref_chunk).lower().split())
                                    overlap = len(retrieved_words.intersection(ref_words))
                                    if overlap > 3:  # 至少3个词重叠
                                        is_relevant = True
                                        break
                                
                                if not is_relevant:
                                    irrelevant_chunks_count += 1
                            
                            # 分析未召回分块（简化版本）
                            for ref_chunk in reference_contexts:
                                is_retrieved = False
                                for retrieved_chunk in retrieved_contexts:
                                    retrieved_words = set(str(retrieved_chunk).lower().split())
                                    ref_words = set(str(ref_chunk).lower().split())
                                    overlap = len(retrieved_words.intersection(ref_words))
                                    if overlap > 3:
                                        is_retrieved = True
                                        break
                                
                                if not is_retrieved:
                                    missed_chunks_count += 1
                        
                        print(f"✅ 重新计算完成: total_samples={total_samples}, irrelevant_chunks={irrelevant_chunks_count}, missed_chunks={missed_chunks_count}")
                        
                except Exception as e:
                    print(f"⚠️ 重新计算统计数据失败: {e}")
                    # 使用默认值
                    total_samples = 1
                    irrelevant_chunks_count = 0
                    missed_chunks_count = 0
            
            # 确保至少有一个样本
            if total_samples == 0:
                total_samples = 1
            
            return {
                'total_samples': total_samples,
                'irrelevant_chunks_count': irrelevant_chunks_count,
                'missed_chunks_count': missed_chunks_count
            }
            
        except Exception as e:
            print(f"❌ 提取Ragas统计数据失败: {e}")
            return {
                'total_samples': 1,
                'irrelevant_chunks_count': 0,
                'missed_chunks_count': 0
            }
    
    @staticmethod
    def save_ragas_result(results: Dict[str, Any], description: str = "") -> Optional[int]:
        """保存Ragas评估结果到独立的ragas_evaluations表"""
        try:
            with get_db_session() as session:
                # 提取统计数据
                stats = DatabaseService.extract_ragas_statistics(results)
                total_samples = stats['total_samples']
                irrelevant_chunks_count = stats['irrelevant_chunks_count']
                missed_chunks_count = stats['missed_chunks_count']
                
                # 提取指标数据
                context_precision = results.get('context_precision', 0)
                context_recall = results.get('context_recall', 0)
                faithfulness = results.get('faithfulness', 0)
                answer_relevancy = results.get('answer_relevancy', 0)
                context_entity_recall = results.get('context_entity_recall', 0)
                context_relevance = results.get('context_relevance', 0)
                answer_correctness = results.get('answer_correctness', 0)
                answer_similarity = results.get('answer_similarity', 0)
                
                # 构建SQL查询，兼容MySQL和SQLite
                sql = """
                INSERT INTO ragas_evaluations 
                (evaluation_time, description, context_precision, context_recall, 
                 faithfulness, answer_relevancy, context_entity_recall, context_relevance,
                 answer_correctness, answer_similarity, total_samples, 
                 irrelevant_chunks_count, missed_chunks_count)
                VALUES (CURRENT_TIMESTAMP, :description, :context_precision, :context_recall, 
                 :faithfulness, :answer_relevancy, :context_entity_recall, :context_relevance,
                 :answer_correctness, :answer_similarity, :total_samples, 
                 :irrelevant_chunks_count, :missed_chunks_count)
                """
                
                result = session.execute(text(sql), {
                    'description': description,
                    'context_precision': context_precision,
                    'context_recall': context_recall,
                    'faithfulness': faithfulness,
                    'answer_relevancy': answer_relevancy,
                    'context_entity_recall': context_entity_recall,
                    'context_relevance': context_relevance,
                    'answer_correctness': answer_correctness,
                    'answer_similarity': answer_similarity,
                    'total_samples': total_samples,
                    'irrelevant_chunks_count': irrelevant_chunks_count,
                    'missed_chunks_count': missed_chunks_count
                })
                session.commit()
                
                # 获取插入的ID
                # 对于SQLAlchemy，我们需要重新查询获取ID
                try:
                    # MySQL
                    id_result = session.execute(text("SELECT LAST_INSERT_ID()"))
                except:
                    # SQLite
                    id_result = session.execute(text("SELECT last_insert_rowid()"))
                row = id_result.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"保存Ragas结果失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_evaluation_history(limit: int = 50) -> List[Dict[str, Any]]:
        """获取评估历史记录（从独立的表中获取）"""
        try:
            with get_db_session() as session:
                # 获取BM25评估历史
                bm25_sql = """
                SELECT id, evaluation_time, description, context_precision, context_recall,
                       f1_score, mrr, map, ndcg, total_samples, irrelevant_chunks_count, missed_chunks_count,
                       'BM25' as evaluation_type
                FROM bm25_evaluations 
                ORDER BY evaluation_time DESC 
                LIMIT :limit
                """
                
                # 获取Ragas评估历史
                ragas_sql = """
                SELECT id, evaluation_time, description, context_precision, context_recall,
                       faithfulness, answer_relevancy, context_entity_recall, context_relevance,
                       answer_correctness, answer_similarity, total_samples, 
                       irrelevant_chunks_count, missed_chunks_count,
                       'RAGAS' as evaluation_type
                FROM ragas_evaluations 
                ORDER BY evaluation_time DESC 
                LIMIT :limit
                """
                
                bm25_result = session.execute(text(bm25_sql), {'limit': limit})
                ragas_result = session.execute(text(ragas_sql), {'limit': limit})
                
                bm25_results = bm25_result.fetchall()
                ragas_results = ragas_result.fetchall()
                
                # 合并结果并按时间排序
                all_results = []
                for row in bm25_results:
                    # 将Row对象转换为字典
                    if hasattr(row, '_asdict'):
                        all_results.append(row._asdict())
                    else:
                        all_results.append(dict(row))
                for row in ragas_results:
                    # 将Row对象转换为字典
                    if hasattr(row, '_asdict'):
                        all_results.append(row._asdict())
                    else:
                        all_results.append(dict(row))
                
                # 按时间排序
                all_results.sort(key=lambda x: x['evaluation_time'], reverse=True)
                return all_results[:limit]
        except Exception as e:
            print(f"获取评估历史失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def get_evaluation_by_id(evaluation_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取评估结果（从独立的表中获取）"""
        try:
            with get_db_session() as session:
                # 先尝试在bm25_evaluations表中查找
                bm25_sql = """
                SELECT id, evaluation_time, description, context_precision, context_recall,
                       f1_score, mrr, map, ndcg, total_samples, irrelevant_chunks_count, missed_chunks_count,
                       'BM25' as evaluation_type
                FROM bm25_evaluations 
                WHERE id = :id
                """
                
                # 再尝试在ragas_evaluations表中查找
                ragas_sql = """
                SELECT id, evaluation_time, description, context_precision, context_recall,
                       faithfulness, answer_relevancy, context_entity_recall, context_relevance,
                       answer_correctness, answer_similarity, total_samples, 
                       irrelevant_chunks_count, missed_chunks_count,
                       'RAGAS' as evaluation_type
                FROM ragas_evaluations 
                WHERE id = :id
                """
                
                bm25_result = session.execute(text(bm25_sql), {'id': evaluation_id})
                bm25_row = bm25_result.fetchone()
                if bm25_row:
                    return dict(bm25_row)
                
                ragas_result = session.execute(text(ragas_sql), {'id': evaluation_id})
                ragas_row = ragas_result.fetchone()
                if ragas_row:
                    return dict(ragas_row)
                
                return None
        except Exception as e:
            print(f"获取评估结果失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """获取评估统计信息（从独立的表中获取）"""
        try:
            with get_db_session() as session:
                # 统计BM25评估数量
                bm25_sql = "SELECT COUNT(*) FROM bm25_evaluations"
                ragas_sql = "SELECT COUNT(*) FROM ragas_evaluations"
                
                bm25_result = session.execute(text(bm25_sql))
                ragas_result = session.execute(text(ragas_sql))
                
                bm25_count = bm25_result.scalar() or 0
                ragas_count = ragas_result.scalar() or 0
                
                # 获取最新评估时间
                latest_sql = """
                SELECT MAX(evaluation_time) FROM (
                    SELECT evaluation_time FROM bm25_evaluations
                    UNION ALL
                    SELECT evaluation_time FROM ragas_evaluations
                ) as all_evaluations
                """
                latest_result = session.execute(text(latest_sql))
                latest_evaluation = latest_result.scalar()
                
                # 处理日期格式（SQLite返回字符串，MySQL返回datetime对象）
                latest_evaluation_time = None
                if latest_evaluation:
                    if hasattr(latest_evaluation, 'isoformat'):
                        # MySQL datetime对象
                        latest_evaluation_time = latest_evaluation.isoformat()
                    else:
                        # SQLite字符串
                        latest_evaluation_time = str(latest_evaluation)
                
                return {
                    'total_evaluations': bm25_count + ragas_count,
                    'bm25_evaluations': bm25_count,
                    'ragas_evaluations': ragas_count,
                    'latest_evaluation_time': latest_evaluation_time
                }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_evaluations': 0,
                'bm25_evaluations': 0,
                'ragas_evaluations': 0,
                'latest_evaluation_time': None
            }

# 历史数据分析相关函数（修改为使用独立的表）
def get_evaluation_history(evaluation_type: str, metric: str) -> List[Dict[str, Any]]:
    """获取指定评估类型和指标的历史数据（从独立的表中获取）"""
    try:
        with get_db_session() as session:
            if evaluation_type.upper() == 'BM25':
                # 特殊处理map指标的列名
                actual_metric = 'map' if metric == 'map_score' else metric
                # 构建SQL查询，兼容MySQL和SQLite
                sql = f"""
                    SELECT id, evaluation_time, {actual_metric}
                    FROM bm25_evaluations
                    WHERE {actual_metric} IS NOT NULL 
                    AND {actual_metric} > 0
                    ORDER BY evaluation_time ASC
                """
            else:  # RAGAS
                # 构建SQL查询，兼容MySQL和SQLite
                sql = f"""
                    SELECT id, evaluation_time, {metric}
                    FROM ragas_evaluations
                    WHERE {metric} IS NOT NULL 
                    AND {metric} > 0
                    ORDER BY evaluation_time ASC
                """
            
            result = session.execute(text(sql))
            rows = result.fetchall()
            
            # 格式化数据
            data = []
            for row in rows:
                # 处理日期格式（SQLite返回字符串，MySQL返回datetime对象）
                evaluation_time = row[1]
                if evaluation_time:
                    if hasattr(evaluation_time, 'isoformat'):
                        # MySQL datetime对象
                        evaluation_time_str = evaluation_time.isoformat()
                    else:
                        # SQLite字符串
                        evaluation_time_str = str(evaluation_time)
                else:
                    evaluation_time_str = None
                
                data.append({
                    'created_at': evaluation_time_str,
                    'value': float(row[2]) if row[2] else None,
                    'id': row[0]
                })
            
            return data
    except Exception as e:
        print(f"获取{evaluation_type} {metric}历史数据失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_evaluation_stats() -> Dict[str, Any]:
    """获取评估统计概览（从独立的表中获取）"""
    try:
        with get_db_session() as session:
            # 获取BM25和RAGAS的总评估次数
            bm25_count_sql = "SELECT COUNT(*) FROM bm25_evaluations"
            ragas_count_sql = "SELECT COUNT(*) FROM ragas_evaluations"
            
            bm25_count = session.execute(text(bm25_count_sql)).scalar() or 0
            ragas_count = session.execute(text(ragas_count_sql)).scalar() or 0
            total_evaluations = bm25_count + ragas_count
            
            # 计算平均准确率
            bm25_precision_sql = """
                SELECT AVG(context_precision) 
                FROM bm25_evaluations 
                WHERE context_precision IS NOT NULL
            """
            ragas_precision_sql = """
                SELECT AVG(context_precision) 
                FROM ragas_evaluations 
                WHERE context_precision IS NOT NULL
            """
            
            bm25_avg_precision = session.execute(text(bm25_precision_sql)).scalar() or 0
            ragas_avg_precision = session.execute(text(ragas_precision_sql)).scalar() or 0
            
            # 计算加权平均准确率
            if bm25_count > 0 and ragas_count > 0:
                avg_precision = (bm25_avg_precision * bm25_count + ragas_avg_precision * ragas_count) / total_evaluations
            elif bm25_count > 0:
                avg_precision = bm25_avg_precision
            elif ragas_count > 0:
                avg_precision = ragas_avg_precision
            else:
                avg_precision = 0
            
            # 计算平均召回率
            bm25_recall_sql = """
                SELECT AVG(context_recall) 
                FROM bm25_evaluations 
                WHERE context_recall IS NOT NULL
            """
            ragas_recall_sql = """
                SELECT AVG(context_recall) 
                FROM ragas_evaluations 
                WHERE context_recall IS NOT NULL
            """
            
            bm25_avg_recall = session.execute(text(bm25_recall_sql)).scalar() or 0
            ragas_avg_recall = session.execute(text(ragas_recall_sql)).scalar() or 0
            
            # 计算加权平均召回率
            if bm25_count > 0 and ragas_count > 0:
                avg_recall = (bm25_avg_recall * bm25_count + ragas_avg_recall * ragas_count) / total_evaluations
            elif bm25_count > 0:
                avg_recall = bm25_avg_recall
            elif ragas_count > 0:
                avg_recall = ragas_avg_recall
            else:
                avg_recall = 0
            
            # 获取最新更新时间（兼容MySQL和SQLite）
            latest_sql = """
                SELECT MAX(evaluation_time) as latest_time 
                FROM (
                    SELECT evaluation_time FROM bm25_evaluations
                    UNION ALL
                    SELECT evaluation_time FROM ragas_evaluations
                ) as all_evaluations
            """
            latest_time = session.execute(text(latest_sql)).scalar()
            
            # 处理日期格式
            latest_update = None
            if latest_time:
                if hasattr(latest_time, 'isoformat'):
                    # MySQL datetime对象
                    latest_update = latest_time.isoformat()
                else:
                    # SQLite字符串
                    latest_update = str(latest_time)
            
            return {
                'total_evaluations': total_evaluations,
                'avg_precision': float(avg_precision) if avg_precision else 0,
                'avg_recall': float(avg_recall) if avg_recall else 0,
                'latest_update': latest_update
            }
    except Exception as e:
        print(f"获取评估统计失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_evaluations': 0,
            'avg_precision': 0,
            'avg_recall': 0,
            'latest_update': None
        }