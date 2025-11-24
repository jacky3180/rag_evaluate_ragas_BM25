"""
全局配置管理
控制debug输出、日志级别等
"""
import os

# 从环境变量读取配置
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "false").lower() == "true"
QUIET_MODE = os.getenv("QUIET_MODE", "false").lower() == "true"

def debug_print(*args, **kwargs):
    """调试输出，仅在DEBUG_MODE为True时输出"""
    if DEBUG_MODE and not QUIET_MODE:
        print(*args, **kwargs)

def verbose_print(*args, **kwargs):
    """详细输出，仅在VERBOSE_LOGGING为True时输出"""
    if VERBOSE_LOGGING and not QUIET_MODE:
        print(*args, **kwargs)

def info_print(*args, **kwargs):
    """信息输出，仅在非QUIET_MODE时输出"""
    if not QUIET_MODE:
        print(*args, **kwargs)

def error_print(*args, **kwargs):
    """错误输出，始终输出"""
    print(*args, **kwargs)

def verbose_info_print(*args, **kwargs):
    """详细信息输出，在VERBOSE_LOGGING或非QUIET_MODE时输出"""
    if VERBOSE_LOGGING or not QUIET_MODE:
        print(*args, **kwargs)

def debug_info_print(*args, **kwargs):
    """调试信息输出，在DEBUG_MODE或VERBOSE_LOGGING时输出"""
    if DEBUG_MODE or VERBOSE_LOGGING:
        print(*args, **kwargs)

# 性能优化配置
DISABLE_PROGRESS_BARS = os.getenv("DISABLE_PROGRESS_BARS", "true").lower() == "true"
DISABLE_DETAILED_LOGS = os.getenv("DISABLE_DETAILED_LOGS", "true").lower() == "true"
