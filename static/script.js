// 全局变量
let isEvaluating = false;
let currentSaveType = null;
let selectedFile = null;
let currentDatasetFile = "standardDataset.xlsx"; // 当前选中的数据集文件

const RAGAS_METRIC_DEFINITIONS = [
    { key: 'context_precision', id: 'ragas-precision', percentId: 'ragas-precision-percent' },
    { key: 'context_recall', id: 'ragas-recall', percentId: 'ragas-recall-percent' },
    { key: 'context_entity_recall', id: 'ragas-entity-recall', percentId: 'ragas-entity-recall-percent' },
    { key: 'context_relevance', id: 'ragas-context-relevance', percentId: 'ragas-context-relevance-percent' },
    { key: 'faithfulness', id: 'ragas-faithfulness', percentId: 'ragas-faithfulness-percent' },
    { key: 'answer_relevancy', id: 'ragas-relevancy', percentId: 'ragas-relevancy-percent' },
    { key: 'answer_correctness', id: 'ragas-correctness', percentId: 'ragas-correctness-percent' },
    { key: 'answer_similarity', id: 'ragas-similarity', percentId: 'ragas-similarity-percent' }
];

const DEFAULT_SELECTED_RAGAS_METRICS = Array.isArray(window.DEFAULT_SELECTED_RAGAS_METRICS)
    ? [...window.DEFAULT_SELECTED_RAGAS_METRICS]
    : ['context_recall', 'context_precision', 'context_entity_recall', 'context_relevance'];

function getEnabledRagasMetrics() {
    if (Array.isArray(window.currentRagasMetrics) && window.currentRagasMetrics.length > 0) {
        return [...window.currentRagasMetrics];
    }
    return [...DEFAULT_SELECTED_RAGAS_METRICS];
}

function applyMetricValue(valueElement, percentElement, value) {
    if (!valueElement || !percentElement) return;
    valueElement.textContent = formatScore(value);
    percentElement.textContent = formatPercentage(value);
    valueElement.classList.remove('metric-not-evaluated');
    percentElement.classList.remove('metric-not-evaluated');
    valueElement.classList.remove('metric-deselected');
    percentElement.classList.remove('metric-deselected');
}

function applyMetricNotEvaluated(valueElement, percentElement) {
    if (!valueElement || !percentElement) return;
    valueElement.textContent = '-';
    valueElement.classList.remove('metric-deselected');
    valueElement.classList.add('metric-not-evaluated');
    percentElement.classList.remove('metric-deselected');
    percentElement.classList.remove('metric-not-evaluated');
    percentElement.innerHTML = '<span class="metric-tag metric-tag--pending">未评测</span>';
}

function applyMetricDeselected(valueElement, percentElement) {
    if (!valueElement || !percentElement) return;
    valueElement.textContent = '-';
    valueElement.classList.remove('metric-not-evaluated');
    percentElement.classList.remove('metric-not-evaluated');
    percentElement.classList.add('metric-deselected');
    percentElement.innerHTML = '<span class="metric-tag metric-tag--deselected">选中未评测</span>';
}

function refreshRagasMetricPlaceholders() {
    const enabledMetrics = getEnabledRagasMetrics();
    const ragasCache = (typeof metricsCache !== 'undefined' && metricsCache && metricsCache.ragas)
        ? metricsCache.ragas
        : null;
    
    RAGAS_METRIC_DEFINITIONS.forEach(metric => {
        const valueElement = document.getElementById(metric.id);
        const percentElement = document.getElementById(metric.percentId);
        if (!valueElement || !percentElement) return;
        
        const cachedValue = ragasCache ? ragasCache[metric.key] : null;
        const hasCachedValue = typeof cachedValue === 'number' && !Number.isNaN(cachedValue);
        const isEnabled = enabledMetrics.includes(metric.key);
        
        if (!isEnabled) {
            applyMetricDeselected(valueElement, percentElement);
        } else if (hasCachedValue) {
            applyMetricValue(valueElement, percentElement, cachedValue);
        } else {
            applyMetricNotEvaluated(valueElement, percentElement);
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 加载数据集文件列表
    loadDatasetFiles();
    
    // 初始化上传功能
    initializeUpload();
    
    // 初始化指标显示
    initializeMetricsDisplay();
    
    // 加载缓存的指标数据
    loadMetricsFromLocalStorage();
    
    // 添加全局错误处理
    window.addEventListener('error', function(e) {
        console.error('全局错误:', e.error);
        showToast('系统错误，请检查控制台', 'error');
    });
    
    window.addEventListener('unhandledrejection', function(e) {
        console.error('未处理的Promise拒绝:', e.reason);
        showToast('网络请求失败，请重试', 'error');
    });
    
    // 添加键盘快捷键
    document.addEventListener('keydown', function(e) {
        // Ctrl+B 或 Cmd+B - 运行 BM25 评估
        if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
            e.preventDefault();
            runBM25Evaluation();
        }
        
        // Ctrl+R 或 Cmd+R - 运行 Ragas 评估（但要阻止默认的刷新行为）
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            runRagasEvaluation();
        }
    });
});

// 加载数据集文件列表
async function loadDatasetFiles() {
    try {
        const response = await fetch('/api/dataset-files');
        const result = await response.json();
        
        if (result.success) {
            updateDatasetSelector(result.data);
        } else {
            console.error('加载数据集文件失败:', result.message);
        }
    } catch (error) {
        console.error('加载数据集文件列表错误:', error);
    }
}

// 更新数据集选择器
function updateDatasetSelector(files) {
    const selector = document.getElementById('datasetType');
    if (!selector) return;
    
    // 保存当前选中的值
    const currentSelectedValue = selector.value;
    
    // 清空现有选项
    selector.innerHTML = '';
    
    // 重新添加标准数据集选项
    const standardOption = document.createElement('option');
    standardOption.value = 'standard';
    standardOption.textContent = '✨ 标准数据集';
    selector.appendChild(standardOption);
    
    // 添加上传的文件选项
    files.forEach(file => {
        if (!file.is_standard) { // 不是标准数据集文件
            const option = document.createElement('option');
            option.value = file.name;
            option.textContent = `📄 ${file.name}`;
            selector.appendChild(option);
        }
    });
    
    // 恢复之前选中的值（如果存在的话）
    if (currentSelectedValue && selector.querySelector(`option[value="${currentSelectedValue}"]`)) {
        selector.value = currentSelectedValue;
    } else {
        // 如果之前选中的值不存在了，重置为标准数据集
        selector.value = 'standard';
        currentDatasetFile = 'standardDataset.xlsx';
        console.log('选中项已重置为标准数据集');
    }
}

// 处理数据集类型变更
function handleDatasetTypeChange() {
    const selector = document.getElementById('datasetType');
    if (!selector) return;
    
    const selectedValue = selector.value;
    
    if (selectedValue === 'standard') {
        currentDatasetFile = 'standardDataset.xlsx';
        console.log('📄 选中数据集: 标准数据集 (standardDataset.xlsx)');
    } else {
        currentDatasetFile = selectedValue;
        console.log('📄 选中数据集: 上传文件 (' + selectedValue + ')');
    }
    
    // 显示当前选中的数据集
    showToast(`已选择数据集: ${currentDatasetFile}`, 'info');
    
    // 显示选中的具体数据集信息（调试用）
    const option = selector.options[selector.selectedIndex];
    console.log('📊 当前选中的选项:', {
        value: option.value,
        text: option.text,
        currentDatasetFile: currentDatasetFile
    });
    
    // 清空之前的评估结果（因为数据集变了）
    clearEvaluationResults();
}

// 清空评估结果
function clearEvaluationResults() {
    // 清空 BM25 指标
    ['precision', 'recall', 'f1', 'mrr', 'map', 'ndcg'].forEach(metric => {
        const element = document.getElementById(`bm25-${metric}`);
        const percentElement = document.getElementById(`bm25-${metric}-percent`);
        if (element) element.textContent = '-';
        if (percentElement) percentElement.textContent = '-';
    });
    
    // 清空 Ragas 指标
    ['recall', 'precision', 'entity-recall', 'context-relevance', 'faithfulness', 'relevancy', 'similarity', 'correctness'].forEach(metric => {
        const element = document.getElementById(`ragas-${metric}`);
        const percentElement = document.getElementById(`ragas-${metric}-percent`);
        if (element) element.textContent = '-';
        if (percentElement) percentElement.textContent = '-';
    });
    
    // 隐藏保存按钮
    const bm25SaveBtn = document.getElementById('bm25-save-btn');
    const ragasSaveBtn = document.getElementById('ragas-save-btn');
    if (bm25SaveBtn) bm25SaveBtn.style.display = 'none';
    if (ragasSaveBtn) ragasSaveBtn.style.display = 'none';
    
    // 清空缓存
    metricsCache.bm25 = {
        context_precision: null,
        context_recall: null,
        f1_score: null,
        mrr: null,
        map: null,
        ndcg: null,
        lastUpdated: null
    };
    metricsCache.ragas = {
        context_precision: null,
        context_recall: null,
        faithfulness: null,
        answer_relevancy: null,
        context_entity_recall: null,
        context_relevance: null,
        answer_correctness: null,
        answer_similarity: null,
        enabled_metrics: getEnabledRagasMetrics(),
        lastUpdated: null
    };
    window.bm25CombinedResults = null;
    window.ragasResults = null;
    
    refreshRagasMetricPlaceholders();
}

// 初始化上传功能
function initializeUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files && e.target.files[0]) {
                handleFileSelect(e.target.files[0]);
            }
        });
    }
    
    // 拖拽上传功能
    if (uploadArea) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });
    }
}

// 初始化指标显示
function initializeMetricsDisplay() {
    // 初始化所有指标为默认值
    const metrics = [
        'bm25-precision', 'bm25-recall', 'bm25-f1', 'bm25-mrr', 'bm25-map', 'bm25-ndcg',
        'ragas-recall', 'ragas-precision', 'ragas-entity-recall', 'ragas-context-relevance',
        'ragas-faithfulness', 'ragas-relevancy', 'ragas-similarity', 'ragas-correctness'
    ];
    
    metrics.forEach(metricId => {
        const element = document.getElementById(metricId);
        const percentElement = document.getElementById(metricId + '-percent');
        if (element && element.textContent === '') {
            element.textContent = '-';
        }
        if (percentElement && percentElement.textContent === '') {
            percentElement.textContent = '-';
        }
    });
    
    // 初始化Ragas指标占位显示
    refreshRagasMetricPlaceholders();
}

// 指标缓存对象
let metricsCache = {
    bm25: {
        context_precision: null,
        context_recall: null,
        f1_score: null,
        mrr: null,
        map: null,
        ndcg: null,
        lastUpdated: null
    },
    ragas: {
        context_precision: null,
        context_recall: null,
        faithfulness: null,
        answer_relevancy: null,
        context_entity_recall: null,
        context_relevance: null,
        answer_correctness: null,
        answer_similarity: null,
        enabled_metrics: getEnabledRagasMetrics(),
        lastUpdated: null
    }
};

// 工具函数
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastIcon = toast.querySelector('.toast-icon');
    const toastMessage = toast.querySelector('.toast-message');
    
    // 设置消息内容
    toastMessage.textContent = message;
    
    // 设置图标
    if (type === 'success') {
        toastIcon.className = 'toast-icon fas fa-check-circle';
        toast.className = 'toast success';
    } else if (type === 'info') {
        toastIcon.className = 'toast-icon fas fa-info-circle';
        toast.className = 'toast info';
    } else {
        toastIcon.className = 'toast-icon fas fa-exclamation-circle';
        toast.className = 'toast error';
    }
    
    // 显示提示
    toast.classList.add('show');
    
    // 3秒后自动隐藏
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function showLoading(text = '正在评估中...') {
    const overlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    loadingText.textContent = text;
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = 'none';
}

function formatPercentage(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return '-';
    }
    return (value * 100).toFixed(1) + '%';
}

function formatScore(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return '-';
    }
    return value.toFixed(4);
}

// BM25评估功能
async function runBM25Evaluation() {
    if (isEvaluating) {
        showToast('评估正在进行中，请稍候...', 'error');
        return;
    }
    
    isEvaluating = true;
    const btn = document.getElementById('bm25-evaluate-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 评估中...';
    
    showLoading('正在进行BM25评估...');
    
    try {
        console.log('🚀 开始BM25评估，使用数据集:', currentDatasetFile);
        console.log('🚀 开始并行调用四个评估接口...');
        
        // 并行调用所有评估接口并直接解析JSON
        const [bm25Result, mrrResult, mapResult, ndcgResult] = await Promise.all([
            fetch('/api/bm25/evaluate', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset_file: currentDatasetFile })
            }).then(res => {
                console.log('BM25 API响应状态:', res.status);
                return res.json();
            }).catch(err => {
                console.error('BM25 API请求失败:', err);
                return { success: false, message: 'BM25 API请求失败: ' + err.message };
            }),
            fetch('/api/mrr/evaluate', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset_file: currentDatasetFile })
            }).then(res => {
                console.log('MRR API响应状态:', res.status);
                return res.json();
            }).catch(err => {
                console.error('MRR API请求失败:', err);
                return { success: false, message: 'MRR API请求失败: ' + err.message };
            }),
            fetch('/api/map/evaluate', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset_file: currentDatasetFile })
            }).then(res => {
                console.log('MAP API响应状态:', res.status);
                return res.json();
            }).catch(err => {
                console.error('MAP API请求失败:', err);
                return { success: false, message: 'MAP API请求失败: ' + err.message };
            }),
            fetch('/api/ndcg/evaluate', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset_file: currentDatasetFile })
            }).then(res => {
                console.log('NDCG API响应状态:', res.status);
                return res.json();
            }).catch(err => {
                console.error('NDCG API请求失败:', err);
                return { success: false, message: 'NDCG API请求失败: ' + err.message };
            })
        ]);
        
        console.log('📊 所有接口调用完成:', {
            bm25: bm25Result,
            mrr: mrrResult,
            map: mapResult,
            ndcg: ndcgResult
        });
        
        // 检查所有评估是否成功
        const allSuccessful = bm25Result.success && mrrResult.success && mapResult.success && ndcgResult.success;
        
        if (allSuccessful) {
            // 合并所有评估结果
            const combinedData = {
                ...bm25Result.data,
                mrr: mrrResult.data.mrr,
                map: mapResult.data.map,
                ndcg: ndcgResult.data.ndcg
            };
            
            // 将合并后的数据存储到全局变量，用于保存到数据库
            window.bm25CombinedResults = {
                ...bm25Result.data,
                mrr: mrrResult.data.mrr,
                map: mapResult.data.map,
                ndcg: ndcgResult.data.ndcg,
                // 添加原始BM25结果用于数据库保存
                avg_precision: bm25Result.data.context_precision,
                avg_recall: bm25Result.data.context_recall,
                avg_f1: bm25Result.data.f1_score
            };
            
            // 更新指标显示
            updateBM25Metrics(combinedData);
            showToast('BM25评估完成！', 'success');
            
            // 显示保存按钮
            showSaveButton('BM25');
            
            // 评估完成后自动显示BM25评估明细
            setTimeout(() => {
                showBM25Details();
            }, 1000);
            
        } else {
            // 显示具体的错误信息
            const errors = [];
            if (!bm25Result.success) errors.push(`BM25: ${bm25Result.message}`);
            if (!mrrResult.success) errors.push(`MRR: ${mrrResult.message}`);
            if (!mapResult.success) errors.push(`MAP: ${mapResult.message}`);
            if (!ndcgResult.success) errors.push(`NDCG: ${ndcgResult.message}`);
            
            console.error('❌ 评估失败详情:', {
                bm25: bm25Result,
                mrr: mrrResult,
                map: mapResult,
                ndcg: ndcgResult
            });
            
            showToast(`评估失败: ${errors.join(', ')}`, 'error');
        }
    } catch (error) {
        console.error('BM25评估错误:', error);
        showToast('BM25评估请求失败', 'error');
    } finally {
        isEvaluating = false;
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play"></i> 开始评估';
        hideLoading();
    }
}

function updateBM25Metrics(data) {
    // 缓存BM25指标数据
    metricsCache.bm25 = {
        context_precision: data.context_precision,
        context_recall: data.context_recall,
        f1_score: data.f1_score,
        mrr: data.mrr,
        map: data.map,
        ndcg: data.ndcg,
        lastUpdated: new Date().toISOString()
    };
    
    // 更新Context Precision
    const precisionElement = document.getElementById('bm25-precision');
    const precisionPercentElement = document.getElementById('bm25-precision-percent');
    precisionElement.textContent = formatScore(data.context_precision);
    precisionPercentElement.textContent = formatPercentage(data.context_precision);
    
    // 更新Context Recall
    const recallElement = document.getElementById('bm25-recall');
    const recallPercentElement = document.getElementById('bm25-recall-percent');
    recallElement.textContent = formatScore(data.context_recall);
    recallPercentElement.textContent = formatPercentage(data.context_recall);
    
    // 更新F1-Score
    const f1Element = document.getElementById('bm25-f1');
    const f1PercentElement = document.getElementById('bm25-f1-percent');
    f1Element.textContent = formatScore(data.f1_score);
    f1PercentElement.textContent = formatPercentage(data.f1_score);
    
    // 更新MRR
    const mrrElement = document.getElementById('bm25-mrr');
    const mrrPercentElement = document.getElementById('bm25-mrr-percent');
    mrrElement.textContent = formatScore(data.mrr);
    mrrPercentElement.textContent = formatPercentage(data.mrr);
    
    // 更新MAP
    const mapElement = document.getElementById('bm25-map');
    const mapPercentElement = document.getElementById('bm25-map-percent');
    mapElement.textContent = formatScore(data.map);
    mapPercentElement.textContent = formatPercentage(data.map);
    
    // 更新NDCG
    const ndcgElement = document.getElementById('bm25-ndcg');
    const ndcgPercentElement = document.getElementById('bm25-ndcg-percent');
    ndcgElement.textContent = formatScore(data.ndcg);
    ndcgPercentElement.textContent = formatPercentage(data.ndcg);
    
    // 添加动画效果
    animateMetricUpdate(precisionPercentElement);
    animateMetricUpdate(recallPercentElement);
    animateMetricUpdate(f1PercentElement);
    animateMetricUpdate(mrrPercentElement);
    animateMetricUpdate(mapPercentElement);
    animateMetricUpdate(ndcgPercentElement);
    
    // 保存到本地存储
    saveMetricsToLocalStorage();
}

// Ragas评估功能
async function runRagasEvaluation() {
    if (isEvaluating) {
        showToast('评估正在进行中，请稍候...', 'error');
        return;
    }
    
    isEvaluating = true;
    const btn = document.getElementById('ragas-evaluate-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 评估中...';
    
    showLoading('正在进行Ragas评估...');
    
    try {
        console.log('🚀 开始Ragas评估，使用数据集:', currentDatasetFile);
        
        const response = await fetch('/api/ragas/evaluate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ dataset_file: currentDatasetFile })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 更新指标显示
            updateRagasMetrics(result.data);
            showToast('Ragas评估完成！', 'success');
            
            // 显示保存按钮
            showSaveButton('RAGAS');
            
        } else {
            showToast(`Ragas评估失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('Ragas评估错误:', error);
        showToast('Ragas评估请求失败', 'error');
    } finally {
        isEvaluating = false;
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play"></i> 开始评估';
        hideLoading();
    }
}

function updateRagasMetrics(data) {
    // 缓存Ragas指标数据
    metricsCache.ragas = {
        context_precision: data.context_precision,
        context_recall: data.context_recall,
        faithfulness: data.faithfulness,
        answer_relevancy: data.answer_relevancy,
        context_entity_recall: data.context_entity_recall,
        context_relevance: data.context_relevance,
        answer_correctness: data.answer_correctness,
        answer_similarity: data.answer_similarity,
        enabled_metrics: getEnabledRagasMetrics(),
        lastUpdated: new Date().toISOString()
    };
    
    // 更新所有Ragas指标
    const enabledMetrics = metricsCache.ragas.enabled_metrics;
    
    RAGAS_METRIC_DEFINITIONS.forEach(metric => {
        const valueElement = document.getElementById(metric.id);
        const percentElement = document.getElementById(metric.percentId);
        const value = data[metric.key];
        const hasValue = typeof value === 'number' && !Number.isNaN(value);
        const isEnabled = enabledMetrics.includes(metric.key);
        
        if (!isEnabled) {
            applyMetricDeselected(valueElement, percentElement);
        } else if (hasValue) {
            applyMetricValue(valueElement, percentElement, value);
            animateMetricUpdate(percentElement);
        } else {
            applyMetricNotEvaluated(valueElement, percentElement);
        }
    });
    
    // 保存到本地存储
    saveMetricsToLocalStorage();
}

// 显示BM25评估明细
async function showBM25Details() {
    showLoading('正在加载BM25评估明细...');
    
    try {
        const response = await fetch('/api/bm25/details');
        const result = await response.json();
        
        if (result.success) {
            displayBM25Details(result.data.details);
            document.getElementById('bm25-details-section').style.display = 'block';
            
            // 滚动到明细区域
            document.getElementById('bm25-details-section').scrollIntoView({ 
                behavior: 'smooth' 
            });
            
            showToast('BM25评估明细加载完成', 'success');
        } else {
            showToast(`加载BM25明细失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('加载BM25明细错误:', error);
        showToast('加载BM25明细请求失败', 'error');
    } finally {
        hideLoading();
    }
}

function displayBM25Details(details) {
    const content = document.getElementById('bm25-details-content');
    const statsElement = document.getElementById('bm25-details-stats');
    
    if (!details || details.length === 0) {
        content.innerHTML = '<p style="text-align: center; color: #7f8c8d; padding: 40px;">暂无评估明细数据</p>';
        statsElement.innerHTML = '';
        return;
    }
    
    // 计算统计信息
    const totalSamples = details.length;
    const totalRelevantChunks = details.reduce((sum, sample) => sum + (sample.relevant_chunks ? sample.relevant_chunks.length : 0), 0);
    const totalIrrelevantChunks = details.reduce((sum, sample) => sum + sample.irrelevant_chunks.length, 0);
    const totalMissedChunks = details.reduce((sum, sample) => sum + sample.missed_chunks.length, 0);
    
    // 显示统计信息
    statsElement.innerHTML = `
        <div class="stats-container">
            <div class="stat-item">
                <div class="stat-number">${totalSamples}</div>
                <div class="stat-label">总样本数</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${totalRelevantChunks}</div>
                <div class="stat-label">完整含有相关信息的分块</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${totalIrrelevantChunks}</div>
                <div class="stat-label">不含有相关信息的分块</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${totalMissedChunks}</div>
                <div class="stat-label">未召回分块</div>
            </div>
        </div>
    `;
    
    let html = '';
    
    details.forEach(sample => {
        html += `
            <div class="sample-item">
                <div class="sample-header">
                    <div class="sample-title">样本${sample.sample_id}</div>
                    <div class="sample-score">行 ${sample.row_index}</div>
                </div>
                
                <div class="user-query">
                    <strong>用户查询:</strong>
                    ${sample.user_input || '无查询内容'}
                </div>
                
                <div class="chunk-section relevant-chunk-section">
                    <h4><i class="fas fa-check-circle"></i> BM25判定完整含有相关信息的分块 (${sample.relevant_chunks ? sample.relevant_chunks.length : 0}个)</h4>
                    ${sample.relevant_chunks && sample.relevant_chunks.length > 0 ? sample.relevant_chunks.map(chunk => `
                        <div class="chunk-item relevant-chunk-item">
                            <strong>检索分块:</strong> ${chunk.retrieved_chunk ? chunk.retrieved_chunk.substring(0, 200) + '...' : '无内容'}
                            ${chunk.reference_chunk ? `<br><strong>匹配的参考分块:</strong> ${chunk.reference_chunk.substring(0, 150) + '...'}` : ''}
                            ${chunk.relevance_score ? `<br><small style="color: #27ae60; font-weight: bold;">BM25相关分数: ${chunk.relevance_score.toFixed(4)}</small>` : ''}
                            ${chunk.is_semantic_containment ? `<br><small style="color: #e67e22; font-weight: bold;">📝 该分块完整含有reference_contexts中的某一分块语义信息，相似度达到${(chunk.semantic_containment_threshold * 100).toFixed(0)}%</small>` : ''}
                        </div>
                    `).join('') : '<div class="chunk-item" style="color: #7f8c8d; font-style: italic;">BM25未判定出完整含有相关信息的分块</div>'}
                </div>
                
                <div class="chunk-section">
                    <h4><i class="fas fa-times-circle"></i> BM25判定不含有相关信息的分块 (${sample.irrelevant_chunks.length}个)</h4>
                    ${sample.irrelevant_chunks.map(chunk => `
                        <div class="chunk-item">
                            ${chunk.retrieved_chunk ? chunk.retrieved_chunk.substring(0, 200) + '...' : '无内容'}
                            <br><small style="color: #e74c3c; font-weight: bold;">相关性分数: ${chunk.max_relevance ? chunk.max_relevance.toFixed(4) : 'N/A'}</small>
                        </div>
                    `).join('')}
                </div>
                
                <div class="chunk-section missed-chunk-section">
                    <h4><i class="fas fa-exclamation-triangle"></i> 未召回的分块 (${sample.missed_chunks.length}个)</h4>
                    ${sample.missed_chunks.map(chunk => `
                        <div class="chunk-item">
                            ${chunk.reference_chunk ? chunk.reference_chunk.substring(0, 200) + '...' : '无内容'}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });
    
    content.innerHTML = html;
}


// 显示Ragas评估明细
async function showRagasDetails() {
    showLoading('正在加载Ragas评估明细...');
    
    try {
        const response = await fetch('/api/ragas/details');
        const result = await response.json();
        
        if (result.success) {
            console.log('API Response:', result); // 调试信息
            console.log('Details:', result.data.details); // 调试信息
            console.log('Sample Summary:', result.data.sample_summary); // 调试信息
            displayRagasDetails(result.data.details, result.data.sample_summary);
            document.getElementById('ragas-details-section').style.display = 'block';
            
            // 滚动到明细区域
            document.getElementById('ragas-details-section').scrollIntoView({ 
                behavior: 'smooth' 
            });
            
            showToast('Ragas评估明细加载完成', 'success');
        } else {
            showToast(`加载Ragas明细失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('加载Ragas明细错误:', error);
        showToast('加载Ragas明细请求失败', 'error');
    } finally {
        hideLoading();
    }
}

function displayRagasDetails(details, sampleSummary) {
    console.log('displayRagasDetails called with:', { details, sampleSummary });
    
    const content = document.getElementById('ragas-details-content');
    const statsElement = document.getElementById('ragas-details-stats');
    const summaryElement = document.getElementById('ragas-details-summary');
    
    console.log('DOM elements:', { content, statsElement, summaryElement });
    
    if (!details || details.length === 0) {
        console.log('No details data, clearing all elements');
        content.innerHTML = '<p style="text-align: center; color: #7f8c8d; padding: 40px;">暂无评估明细数据</p>';
        statsElement.innerHTML = '';
        summaryElement.innerHTML = '';
        return;
    }
    
    // 显示汇总信息 - 使用真实数据
    let summaryHtml = `
        <div class="sample-summary-section" style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <div class="summary-header">
                <h3><i class="fas fa-chart-line"></i> 📊 您的评估结果解释</h3>
            </div>
            <div class="summary-content">
                <div class="overall-metrics">
                    <p><strong>整体评估结果分析：</strong></p>
                    ${sampleSummary && sampleSummary.overall_metrics ? `
                        <p>RAGAS评估结果：Precision: ${(sampleSummary.overall_metrics.context_precision * 100).toFixed(1)}%, Recall: ${(sampleSummary.overall_metrics.context_recall * 100).toFixed(1)}%</p>
                        <p><small>注：RAGAS使用LLM语义评估，比简单的文本匹配更准确</small></p>
                    ` : ''}
                </div>
                <div class="sample-analysis-list">
    `;
    
    // 动态生成每个样本的分析
    details.forEach((sample, index) => {
        const queryShort = sample.user_input.length > 30 ? 
            sample.user_input.substring(0, 30) + "..." : 
            sample.user_input;
        
        // 使用sample_analysis中的真实分数（来自后端计算）
        let samplePrecision, sampleRecall;
        
        if (sampleSummary && sampleSummary.sample_analysis && sampleSummary.sample_analysis[index]) {
            // 使用后端sample_analysis中的分数
            const sampleAnalysis = sampleSummary.sample_analysis[index];
            samplePrecision = sampleAnalysis.precision || 0;
            sampleRecall = sampleAnalysis.recall || 0;
        } else {
            // 回退到分块匹配的简单计算
            const totalRetrieved = sample.relevant_chunks.length + sample.irrelevant_chunks.length;
            const totalReference = sample.relevant_chunks.length + sample.missed_chunks.length;
            samplePrecision = totalRetrieved > 0 ? (sample.relevant_chunks.length / totalRetrieved) : 0;
            sampleRecall = totalReference > 0 ? (sample.relevant_chunks.length / totalReference) : 0;
        }
        
        // 动态生成样本描述
        let sampleDescription = '';
        if (samplePrecision >= 0.9 && sampleRecall >= 0.9) {
            sampleDescription = `样本${index + 1}: 检索内容完全相关且完整，Precision: ${(samplePrecision * 100).toFixed(1)}%, Recall: ${(sampleRecall * 100).toFixed(1)}%`;
        } else if (samplePrecision >= 0.7 && sampleRecall >= 0.7) {
            sampleDescription = `样本${index + 1}: 检索质量良好，但存在少量不相关内容，Precision: ${(samplePrecision * 100).toFixed(1)}%, Recall: ${(sampleRecall * 100).toFixed(1)}%`;
        } else if (sample.irrelevant_chunks.length > 0 && sample.missed_chunks.length > 0) {
            sampleDescription = `样本${index + 1}: 检索内容不完整且包含不相关信息，缺少${sample.missed_chunks.length}个相关分块，Precision: ${(samplePrecision * 100).toFixed(1)}%, Recall: ${(sampleRecall * 100).toFixed(1)}%`;
        } else if (sample.irrelevant_chunks.length > 0) {
            sampleDescription = `样本${index + 1}: 检索到${sample.irrelevant_chunks.length}个不相关分块，但相关分块完整，Precision: ${(samplePrecision * 100).toFixed(1)}%, Recall: ${(sampleRecall * 100).toFixed(1)}%`;
        } else if (sample.missed_chunks.length > 0) {
            sampleDescription = `样本${index + 1}: 检索内容不完整，缺少${sample.missed_chunks.length}个相关分块，Precision: ${(samplePrecision * 100).toFixed(1)}%, Recall: ${(sampleRecall * 100).toFixed(1)}%`;
        } else {
            sampleDescription = `样本${index + 1}: 检索质量中等，Precision: ${(samplePrecision * 100).toFixed(1)}%, Recall: ${(sampleRecall * 100).toFixed(1)}%`;
        }
        
        summaryHtml += `
                    <div class="sample-analysis-item">
                        <div class="sample-query">
                            <strong>样本${index + 1}:</strong> ${queryShort}
                        </div>
                        <div class="sample-metrics">
                            <span class="metric precision">Precision: ${(samplePrecision * 100).toFixed(1)}%</span>
                            <span class="metric recall">Recall: ${(sampleRecall * 100).toFixed(1)}%</span>
                        </div>
                        <div class="sample-description">
                            ${sampleDescription}
                        </div>
                    </div>
        `;
    });
    
    summaryHtml += `
                </div>
            </div>
        </div>
    `;
    
    console.log('Setting summary HTML:', summaryHtml);
    summaryElement.innerHTML = summaryHtml;
    console.log('Summary element after setting:', summaryElement.innerHTML);
    
    // 计算统计信息
    const totalSamples = details.length;
    const totalRelevantChunks = details.reduce((sum, sample) => sum + (sample.relevant_chunks ? sample.relevant_chunks.length : 0), 0);
    const totalIrrelevantChunks = details.reduce((sum, sample) => sum + sample.irrelevant_chunks.length, 0);
    const totalMissedChunks = details.reduce((sum, sample) => sum + sample.missed_chunks.length, 0);
    
    // 显示统计信息
    statsElement.innerHTML = `
        <div class="stats-container">
            <div class="stat-item">
                <div class="stat-number">${totalSamples}</div>
                <div class="stat-label">总样本数</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${totalRelevantChunks}</div>
                <div class="stat-label">完整含有相关信息的分块</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${totalIrrelevantChunks}</div>
                <div class="stat-label">不含有相关信息的分块</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${totalMissedChunks}</div>
                <div class="stat-label">未召回分块</div>
            </div>
        </div>
    `;
    
    let html = ''; // 只生成样本详情
    
    details.forEach((sample, index) => {
        // 获取RAGAS真实分数
        let samplePrecision, sampleRecall;
        if (sampleSummary && sampleSummary.sample_analysis && sampleSummary.sample_analysis[index]) {
            const sampleAnalysis = sampleSummary.sample_analysis[index];
            samplePrecision = sampleAnalysis.precision || 0;
            sampleRecall = sampleAnalysis.recall || 0;
        } else {
            // 回退到分块匹配计算
            const totalRetrieved = sample.relevant_chunks.length + sample.irrelevant_chunks.length;
            const totalReference = sample.relevant_chunks.length + sample.missed_chunks.length;
            samplePrecision = totalRetrieved > 0 ? (sample.relevant_chunks.length / totalRetrieved) : 0;
            sampleRecall = totalReference > 0 ? (sample.relevant_chunks.length / totalReference) : 0;
        }
        
        html += `
            <div class="sample-item">
                <div class="sample-header">
                    <div class="sample-title">样本${sample.sample_id}</div>
                    <div class="sample-score">行 ${sample.row_index}</div>
                </div>
                
                <div class="user-query">
                    <strong>用户查询:</strong>
                    ${sample.user_input || '无查询内容'}
                </div>
                
                <div class="sample-ragas-scores" style="background: #e8f4fd; border: 1px solid #b3d9ff; border-radius: 6px; padding: 12px; margin: 10px 0;">
                    <h4 style="margin: 0 0 8px 0; color: #1976d2;"><i class="fas fa-chart-bar"></i> RAGAS评估分数</h4>
                    <div style="display: flex; gap: 20px;">
                        <span style="color: #1976d2; font-weight: bold;">Precision: ${(samplePrecision * 100).toFixed(1)}%</span>
                        <span style="color: #7b1fa2; font-weight: bold;">Recall: ${(sampleRecall * 100).toFixed(1)}%</span>
                    </div>
                </div>
                
                <div class="chunk-section relevant-chunk-section">
                    <h4><i class="fas fa-check-circle"></i> Ragas判定为相关的分块 (${sample.relevant_chunks ? sample.relevant_chunks.length : 0}个)</h4>
                    ${sample.relevant_chunks && sample.relevant_chunks.length > 0 ? sample.relevant_chunks.map(chunk => {
                        // 获取RAGAS评分
                        let ragasScoresHtml = '';
                        if (chunk.ragas_scores) {
                            const scores = chunk.ragas_scores;
                            ragasScoresHtml = `
                                <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 8px; margin: 8px 0; font-size: 12px;">
                                    <strong style="color: #495057;">RAGAS真实评分:</strong><br>
                                    <span style="color: #28a745;">Context Precision: ${(scores.context_precision * 100).toFixed(1)}%</span> |
                                    <span style="color: #6f42c1;">Context Recall: ${(scores.context_recall * 100).toFixed(1)}%</span> |
                                    <span style="color: #fd7e14;">Faithfulness: ${(scores.faithfulness * 100).toFixed(1)}%</span> |
                                    <span style="color: #20c997;">Answer Relevancy: ${(scores.answer_relevancy * 100).toFixed(1)}%</span>
                                </div>
                            `;
                        }
                        
                        return `
                            <div class="chunk-item relevant-chunk-item">
                                <strong>检索分块:</strong> ${chunk.retrieved_chunk ? chunk.retrieved_chunk.substring(0, 200) + '...' : '无内容'}
                                ${chunk.reference_chunk ? `<br><strong>匹配的参考分块:</strong> ${chunk.reference_chunk.substring(0, 150) + '...'}` : ''}
                                ${chunk.relevance_score ? `<br><small style="color: #27ae60; font-weight: bold;">Ragas相关分数: ${chunk.relevance_score.toFixed(4)}</small>` : ''}
                                ${ragasScoresHtml}
                            </div>
                        `;
                    }).join('') : '<div class="chunk-item" style="color: #7f8c8d; font-style: italic;">Ragas未判定出相关分块</div>'}
                </div>
                
                <div class="chunk-section">
                    <h4><i class="fas fa-times-circle"></i> Ragas判定不相关的分块 (${sample.irrelevant_chunks.length}个)</h4>
                    ${sample.irrelevant_chunks.map(chunk => {
                        // 获取RAGAS评分
                        let ragasScoresHtml = '';
                        if (chunk.ragas_scores) {
                            const scores = chunk.ragas_scores;
                            ragasScoresHtml = `
                                <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 8px; margin: 8px 0; font-size: 12px;">
                                    <strong style="color: #495057;">RAGAS真实评分:</strong><br>
                                    <span style="color: #28a745;">Context Precision: ${(scores.context_precision * 100).toFixed(1)}%</span> |
                                    <span style="color: #6f42c1;">Context Recall: ${(scores.context_recall * 100).toFixed(1)}%</span> |
                                    <span style="color: #fd7e14;">Faithfulness: ${(scores.faithfulness * 100).toFixed(1)}%</span> |
                                    <span style="color: #20c997;">Answer Relevancy: ${(scores.answer_relevancy * 100).toFixed(1)}%</span>
                                </div>
                            `;
                        }
                        
                        return `
                            <div class="chunk-item">
                                ${chunk.retrieved_chunk ? chunk.retrieved_chunk.substring(0, 200) + '...' : '无内容'}
                                <br><small style="color: #e74c3c; font-weight: bold;">相关性分数: ${chunk.max_relevance ? chunk.max_relevance.toFixed(4) : 'N/A'}</small>
                                ${ragasScoresHtml}
                            </div>
                        `;
                    }).join('')}
                </div>
                
                <div class="chunk-section missed-chunk-section">
                    <h4><i class="fas fa-exclamation-triangle"></i> 未召回的分块 (${sample.missed_chunks.length}个)</h4>
                    ${sample.missed_chunks.map(chunk => {
                        // 获取RAGAS评分
                        let ragasScoresHtml = '';
                        if (chunk.ragas_scores) {
                            const scores = chunk.ragas_scores;
                            ragasScoresHtml = `
                                <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 8px; margin: 8px 0; font-size: 12px;">
                                    <strong style="color: #495057;">RAGAS真实评分:</strong><br>
                                    <span style="color: #28a745;">Context Precision: ${(scores.context_precision * 100).toFixed(1)}%</span> |
                                    <span style="color: #6f42c1;">Context Recall: ${(scores.context_recall * 100).toFixed(1)}%</span> |
                                    <span style="color: #fd7e14;">Faithfulness: ${(scores.faithfulness * 100).toFixed(1)}%</span> |
                                    <span style="color: #20c997;">Answer Relevancy: ${(scores.answer_relevancy * 100).toFixed(1)}%</span>
                                </div>
                            `;
                        }
                        
                        return `
                            <div class="chunk-item">
                                ${chunk.reference_chunk ? chunk.reference_chunk.substring(0, 200) + '...' : '无内容'}
                                ${ragasScoresHtml}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    });
    
    content.innerHTML = html;
}

function generateSampleSummaryHtml(sampleSummary) {
    // 创建样本汇总HTML
    let summaryHtml = `
        <div class="sample-summary-section">
            <div class="summary-header">
                <h3><i class="fas fa-chart-line"></i> 📊 您的评估结果解释</h3>
            </div>
            <div class="summary-content">
    `;
    
    // 显示整体指标
    if (sampleSummary.overall_metrics) {
        const metrics = sampleSummary.overall_metrics;
        summaryHtml += `
            <div class="overall-metrics">
                <p><strong>Precision: ${(metrics.context_precision * 100).toFixed(1)}%, Recall: ${(metrics.context_recall * 100).toFixed(1)}%</strong> 是正确的评估结果，因为：</p>
            </div>
        `;
    }
    
    // 显示每个样本的分析
    summaryHtml += '<div class="sample-analysis-list">';
    sampleSummary.sample_analysis.forEach((sample, index) => {
        const queryShort = sample.user_input.length > 30 ? 
            sample.user_input.substring(0, 30) + "..." : 
            sample.user_input;
        
        summaryHtml += `
            <div class="sample-analysis-item">
                <div class="sample-query">
                    <strong>样本${index + 1}:</strong> ${queryShort}
                </div>
                <div class="sample-metrics">
                    <span class="metric precision">Precision: ${(sample.precision * 100).toFixed(1)}%</span>
                    <span class="metric recall">Recall: ${(sample.recall * 100).toFixed(1)}%</span>
                </div>
                <div class="sample-description">
                    ${sample.analysis}
                </div>
            </div>
        `;
    });
    summaryHtml += '</div></div></div>';
    
    return summaryHtml;
}

function hideRagasDetails() {
    document.getElementById('ragas-details-section').style.display = 'none';
}

// 动画效果
function animateMetricUpdate(element) {
    element.style.transform = 'scale(1.1)';
    element.style.color = '#27ae60';
    
    setTimeout(() => {
        element.style.transform = 'scale(1)';
        element.style.color = '';
    }, 300);
}

// 更新当前模型显示
function updateCurrentModelDisplay(selectedModel, ollamaModel) {
    const modelDisplay = document.getElementById('currentModelDisplay');
    if (modelDisplay) {
        if (selectedModel === 'ollama') {
            modelDisplay.innerHTML = `
                <i class="fas fa-server model-icon"></i> 
                <span class="model-title">本地Ollama</span>
                <span class="model-subtitle">${ollamaModel}</span>
            `;
            modelDisplay.className = 'model-info-card ollama-model';
        } else {
            modelDisplay.innerHTML = `
                <i class="fas fa-cloud model-icon"></i> 
                <span class="model-title">云端Qwen</span>
                <span class="model-subtitle">text-embedding-v1</span>
            `;
            modelDisplay.className = 'model-info-card qwen-model';
        }
        
        // 添加设置按钮点击监听器
        addSettingsClickListener(modelDisplay);
    }
}

// 为模型显示元素添加设置按钮点击监听器
function addSettingsClickListener(element) {
    // 移除之前的监听器（如果存在）
    element.removeEventListener('click', handleModelDisplayClick);
    
    // 添加新的点击监听器
    element.addEventListener('click', handleModelDisplayClick);
    
    // 添加鼠标悬停效果提示
    element.style.cursor = 'pointer';
    element.title = '点击打开设置';
}

// 处理模型显示元素的点击事件
function handleModelDisplayClick(event) {
    event.preventDefault();
    event.stopPropagation();
    
    // 调用设置函数
    openSettings();
}

// 初始化数据集类型选择器
function initializeDatasetSelector() {
    const datasetType = localStorage.getItem('datasetType') || 'standard';
    const select = document.getElementById('datasetType');
    if (select) {
        select.value = datasetType;
        updateDatasetDisplay(datasetType);
        
        // 突出显示标准数据集选项
        if (datasetType === 'standard') {
            highlightStandardOption();
        }
    }
}

// 突出显示标准数据集选项
function highlightStandardOption() {
    const select = document.getElementById('datasetType');
    if (select) {
        select.style.background = 'linear-gradient(135deg, rgba(40, 167, 69, 0.2), rgba(32, 201, 151, 0.15))';
        select.style.color = '#28a745';
        select.style.fontWeight = '700';
        select.style.textShadow = '0 1px 3px rgba(40, 167, 69, 0.3)';
        select.style.border = '2px solid rgba(40, 167, 69, 0.4)';
        select.style.borderRadius = '6px';
        select.style.fontSize = '1rem';
        select.style.padding = '12px 16px';
        select.style.boxShadow = '0 2px 8px rgba(40, 167, 69, 0.2)';
        select.style.transform = 'scale(1.02)';
    }
}



// 重置选择器样式
function resetSelectStyle() {
    const select = document.getElementById('datasetType');
    if (select) {
        select.style.background = 'rgba(255, 255, 255, 0.9)';
        select.style.color = '#2c3e50';
        select.style.fontWeight = '500';
        select.style.textShadow = 'none';
        select.style.border = '1px solid rgba(44, 104, 255, 0.3)';
        select.style.borderRadius = '8px';
        select.style.fontSize = '0.9rem';
        select.style.padding = '8px 12px';
        select.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
        select.style.transform = 'scale(1)';
    }
}

// 更新数据集显示
function updateDatasetDisplay(datasetType) {
    // 这里可以根据数据集类型显示不同的内容或样式
    // 目前只是更新选择器的视觉状态
    const selector = document.querySelector('.dataset-selector');
    if (selector) {
        if (datasetType === 'standard') {
            selector.classList.remove('upload-mode');
            selector.classList.add('standard-mode');
        } else {
            selector.classList.remove('standard-mode');
            selector.classList.add('upload-mode');
        }
    }
}

// 获取当前配置并更新显示
async function loadCurrentConfig() {
    try {
        const response = await fetch('/api/embedding-config');
        const result = await response.json();
        
        if (result.success) {
            const config = result.data;
            const selectedModel = config.use_ollama ? 'ollama' : 'qwen';
            const ollamaModel = config.ollama_model;
            
            // 更新localStorage
            localStorage.setItem('embeddingModel', selectedModel);
            localStorage.setItem('ollamaUrl', config.ollama_url);
            localStorage.setItem('ollamaModel', ollamaModel);
            
            // 更新显示
            updateCurrentModelDisplay(selectedModel, ollamaModel);
            
            console.log('当前配置已加载:', config);
        }
    } catch (error) {
        console.error('加载当前配置失败:', error);
        // 使用localStorage中的默认值
        const selectedModel = localStorage.getItem('embeddingModel') || 'qwen';
        const ollamaModel = localStorage.getItem('ollamaModel') || 'embeddinggemma:300m';
        updateCurrentModelDisplay(selectedModel, ollamaModel);
    }
}



// 保存评估结果相关函数
function showSaveDialog(evaluationType) {
    currentSaveType = evaluationType;
    const modal = document.getElementById('saveModal');
    const typeBadge = document.getElementById('saveEvaluationType');
    const description = document.getElementById('evaluationDescription');
    
    // 设置评估类型
    typeBadge.textContent = evaluationType;
    
    // 清空描述
    description.value = '';
    
    // 显示弹框
    modal.style.display = 'block';
    
    // 聚焦到描述输入框
    setTimeout(() => {
        description.focus();
    }, 100);
}

function closeSaveDialog() {
    const modal = document.getElementById('saveModal');
    modal.style.display = 'none';
    currentSaveType = null;
}

async function saveEvaluation() {
    console.log('🔍 开始保存评估，currentSaveType:', currentSaveType);
    
    if (!currentSaveType) {
        console.error('❌ currentSaveType 为空');
        showToast('请选择评估类型', 'error');
        return;
    }
    
    const description = document.getElementById('evaluationDescription').value.trim();
    console.log('📝 评估描述:', description);
    
    try {
        // 显示加载状态
        const saveBtn = document.querySelector('#saveModal .btn-primary');
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
        saveBtn.disabled = true;
        
        let response;
        
        // 根据评估类型选择不同的API端点
        if (currentSaveType === 'BM25' && window.bm25CombinedResults) {
            // 使用新的BM25合并结果API
            console.log('📊 使用BM25合并结果保存:', window.bm25CombinedResults);
            
            response = await fetch('/api/save-bm25-combined', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    context_precision: window.bm25CombinedResults.context_precision,
                    context_recall: window.bm25CombinedResults.context_recall,
                    f1_score: window.bm25CombinedResults.f1_score,
                    mrr: window.bm25CombinedResults.mrr,
                    map: window.bm25CombinedResults.map,
                    ndcg: window.bm25CombinedResults.ndcg,
                    total_samples: window.bm25CombinedResults.total_samples,
                    irrelevant_chunks: window.bm25CombinedResults.irrelevant_chunks,
                    missed_chunks: window.bm25CombinedResults.missed_chunks,
                    relevant_chunks: window.bm25CombinedResults.relevant_chunks,
                    description: description
                })
            });
        } else {
            // 使用原有的保存API
            response = await fetch('/api/save-evaluation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    evaluation_type: currentSaveType,
                    description: description
                })
            });
        }
        
        console.log('📡 响应状态码:', response.status);
        
        const result = await response.json();
        console.log('📊 解析结果:', result);
        
        if (result.success) {
            showToast(result.message, 'success');
            
            // 隐藏保存按钮（可选）
            const saveBtn = document.getElementById(`${currentSaveType.toLowerCase()}-save-btn`);
            if (saveBtn) {
                saveBtn.style.display = 'none';
            }
            
            closeSaveDialog();
        } else {
            showToast(result.message, 'error');
        }
        
    } catch (error) {
        console.error('保存评估结果失败:', error);
        console.error('错误详情:', error.message);
        showToast(`保存失败: ${error.message}`, 'error');
    } finally {
        // 恢复按钮状态
        const saveBtn = document.querySelector('#saveModal .btn-primary');
        saveBtn.innerHTML = '<i class="fas fa-save"></i> 保存';
        saveBtn.disabled = false;
    }
}

// 更新评估结果显示保存按钮
function showSaveButton(evaluationType) {
    const saveBtn = document.getElementById(`${evaluationType.toLowerCase()}-save-btn`);
    if (saveBtn) {
        saveBtn.style.display = 'inline-flex';
    }
}

// 公用弹框处理函数
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'block';
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'none';
}

// 点击弹框外部关闭
window.onclick = function(event) {
    // 检查所有可能的弹框
    const modals = ['saveModal', 'settingsModal', 'uploadModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
    if (event.target === modal) {
            if (modalId === 'saveModal') {
        closeSaveDialog();
            } else if (modalId === 'settingsModal') {
                closeSettings();
            } else if (modalId === 'uploadModal') {
                closeUploadDialog();
            }
    }
    });
}

// ESC键关闭弹框
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = ['saveModal', 'settingsModal', 'uploadModal'];
        modals.forEach(modalId => {
            const modal = document.getElementById(modalId);
        if (modal.style.display === 'block') {
                if (modalId === 'saveModal') {
            closeSaveDialog();
                } else if (modalId === 'settingsModal') {
                    closeSettings();
                } else if (modalId === 'uploadModal') {
                    closeUploadDialog();
                }
        }
        });
    }
});

// 跳转到历史数据分析页面
function goToHistory() {
    window.open('/static/history.html', '_blank');
}

// 跳转到构建数据集页面
function openBuildDataset() {
    window.location.href = 'standardDataset_build.html';
}

// 设置窗口功能
function openSettings() {
    openModal('settingsModal');
    
    // 加载当前设置
    loadCurrentSettings();
    
    // 监听模型选择变化
    const modelRadios = document.querySelectorAll('input[name="embeddingModel"]');
    modelRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const ollamaSettings = document.getElementById('ollamaSettings');
            const qwenSettings = document.getElementById('qwenSettings');
            if (this.value === 'ollama') {
                ollamaSettings.style.display = 'block';
                qwenSettings.style.display = 'none';
            } else {
                ollamaSettings.style.display = 'none';
                qwenSettings.style.display = 'block';
            }
        });
    });
}

function closeSettings() {
    closeModal('settingsModal');
}

async function loadCurrentSettings() {
    try {
        // 首先尝试从服务器获取当前配置
        const response = await fetch('/api/embedding-config');
        const result = await response.json();
        
        let currentModel, ollamaUrl, ollamaModel;
        
        if (result.success) {
            const config = result.data;
            currentModel = config.use_ollama ? 'ollama' : 'qwen';
            ollamaUrl = config.ollama_url;
            ollamaModel = config.ollama_model;
            
            // 同步到localStorage
            localStorage.setItem('embeddingModel', currentModel);
            localStorage.setItem('ollamaUrl', ollamaUrl);
            localStorage.setItem('ollamaModel', ollamaModel);
        } else {
            // 如果服务器获取失败，使用localStorage中的值
            currentModel = localStorage.getItem('embeddingModel') || 'qwen';
            ollamaUrl = localStorage.getItem('ollamaUrl') || 'http://localhost:11434';
            ollamaModel = localStorage.getItem('ollamaModel') || 'embeddinggemma:300m';
        }
    
    // 设置单选按钮
        const modelRadio = document.querySelector(`input[name="embeddingModel"][value="${currentModel}"]`);
        if (modelRadio) {
            modelRadio.checked = true;
        }
    
    // 安全地设置Ollama配置
    const ollamaUrlInput = document.getElementById('ollamaUrl');
    if (ollamaUrlInput) {
        ollamaUrlInput.value = ollamaUrl;
    }
    
    const ollamaModelInput = document.getElementById('ollamaModel');
    if (ollamaModelInput) {
        ollamaModelInput.value = ollamaModel;
    }
    
        // 显示/隐藏设置区域
        const ollamaSettings = document.getElementById('ollamaSettings');
        const qwenSettings = document.getElementById('qwenSettings');
        if (currentModel === 'ollama') {
            ollamaSettings.style.display = 'block';
            qwenSettings.style.display = 'none';
        } else {
            ollamaSettings.style.display = 'none';
            qwenSettings.style.display = 'block';
        }
        
        // 设置Qwen API Key（优先从服务器获取，然后从localStorage获取）
        let qwenApiKey = '';
        if (result.success && result.data.qwen_api_key) {
            qwenApiKey = result.data.qwen_api_key;
        } else {
            qwenApiKey = localStorage.getItem('qwenApiKey') || '';
        }
        document.getElementById('qwenApiKey').value = qwenApiKey;
        
        console.log('设置已加载:', { currentModel, ollamaUrl, ollamaModel });
        
    } catch (error) {
        console.error('加载设置失败:', error);
        // 使用默认值
        const currentModel = localStorage.getItem('embeddingModel') || 'qwen';
        const ollamaUrl = localStorage.getItem('ollamaUrl') || 'http://localhost:11434';
        const ollamaModel = localStorage.getItem('ollamaModel') || 'embeddinggemma:300m';
        
        // 安全地设置embedding模型选择
        const embeddingModelInput = document.querySelector(`input[name="embeddingModel"][value="${currentModel}"]`);
        if (embeddingModelInput) {
            embeddingModelInput.checked = true;
        }
        
        // 安全地设置Ollama配置
        const ollamaUrlInput = document.getElementById('ollamaUrl');
        if (ollamaUrlInput) {
            ollamaUrlInput.value = ollamaUrl;
        }
        
        const ollamaModelInput = document.getElementById('ollamaModel');
        if (ollamaModelInput) {
            ollamaModelInput.value = ollamaModel;
        }
        
    const ollamaSettings = document.getElementById('ollamaSettings');
    if (currentModel === 'ollama') {
        ollamaSettings.style.display = 'block';
    } else {
        ollamaSettings.style.display = 'none';
        }
    }
}

async function saveSettings() {
    const selectedModelRadio = document.querySelector('input[name="embeddingModel"]:checked');
    if (!selectedModelRadio) {
        console.error('未选择embedding模型');
        return;
    }
    const selectedModel = selectedModelRadio.value;
    
    const ollamaUrlInput = document.getElementById('ollamaUrl');
    const ollamaModelInput = document.getElementById('ollamaModel');
    const qwenApiKeyInput = document.getElementById('qwenApiKey');
    
    if (!ollamaUrlInput || !ollamaModelInput || !qwenApiKeyInput) {
        console.error('设置表单元素未找到');
        return;
    }
    
    const ollamaUrl = ollamaUrlInput.value;
    const ollamaModel = ollamaModelInput.value;
    const qwenApiKey = qwenApiKeyInput.value;
    
    try {
    // 保存到localStorage
    localStorage.setItem('embeddingModel', selectedModel);
    localStorage.setItem('ollamaUrl', ollamaUrl);
    localStorage.setItem('ollamaModel', ollamaModel);
    localStorage.setItem('qwenApiKey', qwenApiKey);
        
        // 更新服务器端配置
        const response = await fetch('/api/embedding-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                use_ollama: selectedModel === 'ollama',
                ollama_url: ollamaUrl,
                ollama_model: ollamaModel,
                qwen_api_key: qwenApiKey
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('设置已保存并生效！', 'success');
            
            // 更新首页显示的当前模型信息
            updateCurrentModelDisplay(selectedModel, ollamaModel);
        } else {
            showToast(`设置保存失败: ${result.message}`, 'error');
        }
    
    // 关闭设置窗口
    closeSettings();
    
    console.log('设置已更新:', {
        model: selectedModel,
        ollamaUrl: ollamaUrl,
        ollamaModel: ollamaModel
    });
        
    } catch (error) {
        console.error('保存设置失败:', error);
        showToast('保存设置失败，请重试', 'error');
    }
}

// 文档上传相关函数
function openUploadDialog() {
    openModal('uploadModal');
    
    // 重置状态
    selectedFile = null;
    resetUploadArea();
    
    // 添加拖拽事件监听
    setupDragAndDrop();
}

function closeUploadDialog() {
    closeModal('uploadModal');
    
    // 清理状态
    selectedFile = null;
    resetUploadArea();
}

function resetUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const uploadBtn = document.getElementById('uploadBtn');
    
    uploadArea.classList.remove('file-selected', 'dragover');
    uploadBtn.disabled = true;
    
    // 重置文件输入
    const fileInput = document.getElementById('fileInput');
    fileInput.value = '';
}

function setupDragAndDrop() {
    const uploadArea = document.getElementById('uploadArea');
    
    // 拖拽进入
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    // 拖拽离开
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    // 拖拽放下
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
    
    // 点击上传区域
    uploadArea.addEventListener('click', function(e) {
        if (e.target === uploadArea || e.target.closest('.upload-text')) {
            document.getElementById('fileInput').click();
        }
    });
    
    // 文件输入变化
    document.getElementById('fileInput').addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
}

function handleFileSelect(file) {
    // 验证文件类型
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
        showToast('只支持 .xlsx 格式的Excel文档', 'error');
        return;
    }
    
    selectedFile = file;
    
    // 更新UI
    const uploadArea = document.getElementById('uploadArea');
    const uploadBtn = document.getElementById('uploadBtn');
    
    uploadArea.classList.add('file-selected');
    uploadBtn.disabled = false;
    
    // 更新显示文本
    const uploadText = uploadArea.querySelector('.upload-text h3');
    uploadText.textContent = `已选择文件: ${file.name}`;
    
    const uploadSubtext = uploadArea.querySelector('.upload-text p');
    uploadSubtext.textContent = `文件大小: ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    
    showToast('文件选择成功，可以开始上传', 'success');
}

async function uploadFile() {
    if (!selectedFile) {
        showToast('请先选择要上传的文件', 'error');
        return;
    }
    
    const uploadBtn = document.getElementById('uploadBtn');
    const originalText = uploadBtn.innerHTML;
    
    try {
        // 显示上传状态
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 上传中...';
        uploadBtn.disabled = true;
        
        // 创建FormData
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        // 发送上传请求
        const response = await fetch('/api/upload-document', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(result.message, 'success');
            
            // 显示上传结果详情
            if (result.data && result.data.validation) {
                const validation = result.data.validation;
                console.log('上传验证结果:', validation);
                
                if (validation.row_count) {
                    showToast(`文档包含 ${validation.row_count} 行数据`, 'success');
                }
            }
            
            // 关闭弹框
            closeUploadDialog();
            
            // 重新加载数据集文件列表
            loadDatasetFiles();
        } else {
            showToast(result.message, 'error');
        }
        
    } catch (error) {
        console.error('上传失败:', error);
        showToast('上传失败，请重试', 'error');
    } finally {
        // 恢复按钮状态
        uploadBtn.innerHTML = originalText;
        uploadBtn.disabled = false;
    }
}

// 点击弹框外部关闭
window.addEventListener('click', function(event) {
    const uploadModal = document.getElementById('uploadModal');
    if (event.target === uploadModal) {
        closeUploadDialog();
    }
});

// ESC键关闭弹框
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const uploadModal = document.getElementById('uploadModal');
        if (uploadModal.style.display === 'block') {
            closeUploadDialog();
        }
    }
});

/**
 * 下载数据集模版
 */
async function downloadTemplate() {
    console.log('📥 下载模版按钮被点击');
    
    try {
        showLoading('正在准备下载模版...');
        
        console.log('发送下载请求到: /api/dataset/download-template');
        
        // 调用后端API下载模版文件
        const response = await fetch('/api/dataset/download-template');
        
        console.log('API响应状态:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API错误响应:', errorText);
            throw new Error(`下载失败: ${response.status} - ${errorText}`);
        }
        
        // 获取文件blob
        const blob = await response.blob();
        console.log('Blob创建成功，大小:', blob.size, 'bytes, 类型:', blob.type);
        
        // 创建下载链接
        const url = window.URL.createObjectURL(blob);
        console.log('创建下载URL:', url);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'standardDataset.xlsx';  // 下载的文件名
        a.style.display = 'none';  // 隐藏链接
        document.body.appendChild(a);
        
        console.log('触发点击下载');
        a.click();
        
        // 延迟清理，确保下载开始
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            console.log('清理完成');
        }, 100);
        
        showToast('模版下载成功！', 'success');
        console.log('✅ 下载流程完成');
        
    } catch (error) {
        console.error('❌ 下载模版失败:', error);
        showToast('下载模版失败，请重试: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// 保存指标到本地存储
function saveMetricsToLocalStorage() {
    try {
        localStorage.setItem('metricsCache', JSON.stringify(metricsCache));
        console.log('指标缓存已保存到本地存储');
    } catch (error) {
        console.error('保存指标缓存失败:', error);
    }
}

// 从本地存储加载指标缓存
function loadCachedMetrics() {
    try {
        const cached = localStorage.getItem('metricsCache');
        if (cached) {
            const parsedCache = JSON.parse(cached);
            
            // 恢复BM25指标
            if (parsedCache.bm25 && parsedCache.bm25.lastUpdated) {
                metricsCache.bm25 = parsedCache.bm25;
                displayCachedBM25Metrics();
            }
            
            // 恢复Ragas指标
            if (parsedCache.ragas && parsedCache.ragas.lastUpdated) {
                metricsCache.ragas = parsedCache.ragas;
                if (!Array.isArray(metricsCache.ragas.enabled_metrics) || metricsCache.ragas.enabled_metrics.length === 0) {
                    metricsCache.ragas.enabled_metrics = getEnabledRagasMetrics();
                }
                displayCachedRagasMetrics();
            }
            
            console.log('指标缓存已从本地存储加载');
        }
    } catch (error) {
        console.error('加载指标缓存失败:', error);
    }
}

// 显示缓存的BM25指标
function displayCachedBM25Metrics() {
    const data = metricsCache.bm25;
    if (!data || !data.lastUpdated) return;
    
    // 更新Context Precision
    const precisionElement = document.getElementById('bm25-precision');
    const precisionPercentElement = document.getElementById('bm25-precision-percent');
    if (precisionElement && precisionPercentElement) {
        precisionElement.textContent = formatScore(data.context_precision);
        precisionPercentElement.textContent = formatPercentage(data.context_precision);
    }
    
    // 更新Context Recall
    const recallElement = document.getElementById('bm25-recall');
    const recallPercentElement = document.getElementById('bm25-recall-percent');
    if (recallElement && recallPercentElement) {
        recallElement.textContent = formatScore(data.context_recall);
        recallPercentElement.textContent = formatPercentage(data.context_recall);
    }
    
    // 更新F1-Score
    const f1Element = document.getElementById('bm25-f1');
    const f1PercentElement = document.getElementById('bm25-f1-percent');
    if (f1Element && f1PercentElement) {
        f1Element.textContent = formatScore(data.f1_score);
        f1PercentElement.textContent = formatPercentage(data.f1_score);
    }
    
    // 更新MRR
    const mrrElement = document.getElementById('bm25-mrr');
    const mrrPercentElement = document.getElementById('bm25-mrr-percent');
    if (mrrElement && mrrPercentElement) {
        mrrElement.textContent = formatScore(data.mrr);
        mrrPercentElement.textContent = formatPercentage(data.mrr);
    }
    
    // 更新MAP
    const mapElement = document.getElementById('bm25-map');
    const mapPercentElement = document.getElementById('bm25-map-percent');
    if (mapElement && mapPercentElement) {
        mapElement.textContent = formatScore(data.map);
        mapPercentElement.textContent = formatPercentage(data.map);
    }
    
    // 更新NDCG
    const ndcgElement = document.getElementById('bm25-ndcg');
    const ndcgPercentElement = document.getElementById('bm25-ndcg-percent');
    if (ndcgElement && ndcgPercentElement) {
        ndcgElement.textContent = formatScore(data.ndcg);
        ndcgPercentElement.textContent = formatPercentage(data.ndcg);
    }
    
    // 显示保存按钮
    showSaveButton('BM25');
    
    console.log('BM25指标已从缓存恢复');
}

// 显示缓存的Ragas指标
function displayCachedRagasMetrics() {
    const data = metricsCache.ragas;
    if (!data || !data.lastUpdated) return;
    
    const enabledMetrics = Array.isArray(data.enabled_metrics) ? data.enabled_metrics : getEnabledRagasMetrics();
    
    RAGAS_METRIC_DEFINITIONS.forEach(metric => {
        const valueElement = document.getElementById(metric.id);
        const percentElement = document.getElementById(metric.percentId);
        const value = data[metric.key];
        const hasValue = typeof value === 'number' && !Number.isNaN(value);
        const isEnabled = enabledMetrics.includes(metric.key);
        
        if (!isEnabled) {
            applyMetricDeselected(valueElement, percentElement);
        } else if (hasValue) {
            applyMetricValue(valueElement, percentElement, value);
        } else {
            applyMetricNotEvaluated(valueElement, percentElement);
        }
    });
    
    // 显示保存按钮
    showSaveButton('RAGAS');
    
    console.log('Ragas指标已从缓存恢复');
    refreshRagasMetricPlaceholders();
}

// 清除指标缓存
function clearMetricsCache() {
    // 确认对话框
    if (!confirm('确定要清除所有指标缓存吗？此操作将删除所有已缓存的BM25和Ragas评估结果。')) {
        return;
    }
    
    // 重置内存中的缓存
    metricsCache = {
        bm25: {
            context_precision: null,
            context_recall: null,
            f1_score: null,
            mrr: null,
            map: null,
            ndcg: null,
            lastUpdated: null
        },
        ragas: {
            context_precision: null,
            context_recall: null,
            faithfulness: null,
            answer_relevancy: null,
            context_entity_recall: null,
            context_relevance: null,
            answer_correctness: null,
            answer_similarity: null,
            lastUpdated: null
        }
    };
    
    // 清除本地存储
    localStorage.removeItem('metricsCache');
    
    // 重置页面显示
    resetMetricsDisplay();
    
    showToast('指标缓存已清除', 'success');
    console.log('指标缓存已清除');
}

// 重置指标显示
function resetMetricsDisplay() {
    // 重置BM25指标显示
    const bm25Metrics = [
        { id: 'bm25-precision', percentId: 'bm25-precision-percent' },
        { id: 'bm25-recall', percentId: 'bm25-recall-percent' },
        { id: 'bm25-f1', percentId: 'bm25-f1-percent' },
        { id: 'bm25-mrr', percentId: 'bm25-mrr-percent' },
        { id: 'bm25-map', percentId: 'bm25-map-percent' },
        { id: 'bm25-ndcg', percentId: 'bm25-ndcg-percent' }
    ];
    
    bm25Metrics.forEach(metric => {
        const valueElement = document.getElementById(metric.id);
        const percentElement = document.getElementById(metric.percentId);
        if (valueElement) valueElement.textContent = '--';
        if (percentElement) percentElement.textContent = '--';
    });
    
    // 重置Ragas指标显示
    const ragasMetrics = [
        { id: 'ragas-precision', percentId: 'ragas-precision-percent' },
        { id: 'ragas-recall', percentId: 'ragas-recall-percent' },
        { id: 'ragas-faithfulness', percentId: 'ragas-faithfulness-percent' },
        { id: 'ragas-relevancy', percentId: 'ragas-relevancy-percent' },
        { id: 'ragas-entity-recall', percentId: 'ragas-entity-recall-percent' },
        { id: 'ragas-context-relevance', percentId: 'ragas-context-relevance-percent' },
        { id: 'ragas-correctness', percentId: 'ragas-correctness-percent' },
        { id: 'ragas-similarity', percentId: 'ragas-similarity-percent' }
    ];
    
    ragasMetrics.forEach(metric => {
        const valueElement = document.getElementById(metric.id);
        const percentElement = document.getElementById(metric.percentId);
        if (valueElement) valueElement.textContent = '--';
        if (percentElement) percentElement.textContent = '--';
    });
    
    // 隐藏保存按钮
    const bm25SaveBtn = document.getElementById('bm25-save-btn');
    const ragasSaveBtn = document.getElementById('ragas-save-btn');
    if (bm25SaveBtn) bm25SaveBtn.style.display = 'none';
    if (ragasSaveBtn) ragasSaveBtn.style.display = 'none';
}

