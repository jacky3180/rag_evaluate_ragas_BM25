"""
文本相似度计算模块
"""

import re

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度
    使用Jaccard相似度和字符重叠度
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        
    Returns:
        float: 相似度分数 (0-1)
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
            containment_similarity = 0.8  # 固定给予0.8的相似度
            final_similarity = max(final_similarity, containment_similarity)
    
    return final_similarity
