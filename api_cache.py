"""
API响应缓存模块
用于缓存历史数据查询结果，减少数据库查询次数
提升响应速度
"""
import time
import hashlib
import json
from typing import Dict, Any, Optional, Callable
from functools import wraps
from config import info_print, debug_print

class APICache:
    """API响应缓存类"""
    
    def __init__(self, ttl: int = 300):
        """
        初始化缓存
        
        Args:
            ttl: 缓存过期时间（秒），默认5分钟
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        self.hit_count = 0
        self.miss_count = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            str: 缓存键
        """
        # 将参数序列化为字符串
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        # 使用MD5生成短键
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取数据
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[Any]: 缓存的数据，如果不存在或已过期则返回None
        """
        if key not in self.cache:
            self.miss_count += 1
            debug_print(f"🔍 缓存未命中: {key}")
            return None
        
        cache_entry = self.cache[key]
        
        # 检查是否过期
        if time.time() - cache_entry['timestamp'] > self.ttl:
            # 缓存已过期，删除
            del self.cache[key]
            self.miss_count += 1
            debug_print(f"⏰ 缓存已过期: {key}")
            return None
        
        self.hit_count += 1
        debug_print(f"✅ 缓存命中: {key}")
        return cache_entry['data']
    
    def set(self, key: str, data: Any) -> None:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
        debug_print(f"💾 缓存已保存: {key}")
    
    def clear(self) -> None:
        """清空所有缓存"""
        count = len(self.cache)
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        info_print(f"🗑️  已清空 {count} 个缓存项")
    
    def clear_expired(self) -> int:
        """
        清除过期的缓存项
        
        Returns:
            int: 清除的缓存项数量
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] > self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            info_print(f"🗑️  已清除 {len(expired_keys)} 个过期缓存项")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 缓存统计信息
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.2f}%",
            'ttl': self.ttl
        }

# 全局缓存实例
_history_cache = APICache(ttl=300)  # 历史数据缓存5分钟
_stats_cache = APICache(ttl=60)     # 统计数据缓存1分钟
_eval_cache = APICache(ttl=600)     # 评估结果缓存10分钟

def cache_response(cache_instance: APICache = None, ttl: Optional[int] = None):
    """
    缓存装饰器
    
    Args:
        cache_instance: 使用的缓存实例，默认使用历史数据缓存
        ttl: 自定义TTL（秒）
        
    Returns:
        Callable: 装饰器函数
    """
    if cache_instance is None:
        cache_instance = _history_cache
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_instance._generate_key(func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_data = cache_instance.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache_instance.set(cache_key, result)
            
            return result
        
        return wrapper
    
    return decorator

def get_history_cache() -> APICache:
    """获取历史数据缓存实例"""
    return _history_cache

def get_stats_cache() -> APICache:
    """获取统计数据缓存实例"""
    return _stats_cache

def get_eval_cache() -> APICache:
    """获取评估结果缓存实例"""
    return _eval_cache

def clear_all_caches() -> Dict[str, int]:
    """
    清空所有缓存
    
    Returns:
        Dict: 各缓存清除的项数
    """
    history_count = len(_history_cache.cache)
    stats_count = len(_stats_cache.cache)
    eval_count = len(_eval_cache.cache)
    
    _history_cache.clear()
    _stats_cache.clear()
    _eval_cache.clear()
    
    return {
        'history_cache': history_count,
        'stats_cache': stats_count,
        'eval_cache': eval_count,
        'total': history_count + stats_count + eval_count
    }

def get_all_cache_stats() -> Dict[str, Any]:
    """
    获取所有缓存的统计信息
    
    Returns:
        Dict: 所有缓存的统计信息
    """
    return {
        'history_cache': _history_cache.get_stats(),
        'stats_cache': _stats_cache.get_stats(),
        'eval_cache': _eval_cache.get_stats()
    }

