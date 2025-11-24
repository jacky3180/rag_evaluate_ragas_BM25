"""
环境变量管理模块
处理.env文件的读取和更新
"""

import os
from pathlib import Path
from typing import Dict, Optional

def load_env_file(env_path: str = ".env") -> Dict[str, str]:
    """
    加载.env文件中的环境变量
    
    Args:
        env_path: .env文件路径
        
    Returns:
        dict: 环境变量字典
    """
    env_vars = {}
    env_file = Path(env_path)
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

def update_env_file(updates: Dict[str, str], env_path: str = ".env") -> bool:
    """
    更新.env文件中的环境变量，完全保持原有格式、注释和换行符
    
    Args:
        updates: 要更新的环境变量字典
        env_path: .env文件路径
        
    Returns:
        bool: 更新是否成功
    """
    try:
        env_file = Path(env_path)
        
        # 如果文件不存在，创建新文件
        if not env_file.exists():
            with open(env_file, 'w', encoding='utf-8') as f:
                for key, value in updates.items():
                    f.write(f"{key}={value}\n")
            return True
        
        # 读取现有文件的所有行（保持原始格式）
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 创建更新后的行列表
        updated_lines = []
        updated_keys = set()
        
        for line in lines:
            line_stripped = line.strip()
            
            # 检查是否是环境变量行（不是注释，包含=号）
            if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                key = line_stripped.split('=', 1)[0].strip()
                
                # 如果这个key需要更新
                if key in updates:
                    # 保持原有的缩进和格式，只替换值
                    if line.startswith(' '):
                        # 保持缩进
                        indent = len(line) - len(line.lstrip())
                        updated_lines.append(' ' * indent + f"{key}={updates[key]}\n")
                    else:
                        updated_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                else:
                    # 保持原行不变
                    updated_lines.append(line)
            else:
                # 保持原行不变（注释、空行等）
                updated_lines.append(line)
        
        # 添加新的变量（如果不存在于原文件中）
        for key, value in updates.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}\n")
        
        # 写入更新后的文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        return True
    except Exception as e:
        print(f"更新.env文件失败: {e}")
        return False

def get_env_value(key: str, default: str = "", env_path: str = ".env") -> str:
    """
    获取.env文件中的环境变量值
    
    Args:
        key: 环境变量名
        default: 默认值
        env_path: .env文件路径
        
    Returns:
        str: 环境变量值
    """
    env_vars = load_env_file(env_path)
    return env_vars.get(key, default)

def set_env_value(key: str, value: str, env_path: str = ".env") -> bool:
    """
    设置.env文件中的环境变量值
    
    Args:
        key: 环境变量名
        value: 环境变量值
        env_path: .env文件路径
        
    Returns:
        bool: 设置是否成功
    """
    return update_env_file({key: value}, env_path)

# 测试函数
def test_env_manager():
    """测试环境变量管理功能"""
    print("🔍 测试环境变量管理功能...")
    
    # 测试读取
    env_vars = load_env_file()
    print(f"📋 当前.env文件内容: {env_vars}")
    
    # 测试设置
    test_key = "TEST_KEY"
    test_value = "test_value_123"
    
    success = set_env_value(test_key, test_value)
    print(f"📝 设置测试环境变量: {success}")
    
    # 验证设置
    retrieved_value = get_env_value(test_key)
    print(f"📖 读取测试环境变量: {retrieved_value}")
    
    # 清理测试
    if retrieved_value == test_value:
        print("✅ 环境变量管理功能正常")
    else:
        print("❌ 环境变量管理功能异常")

if __name__ == "__main__":
    test_env_manager()
