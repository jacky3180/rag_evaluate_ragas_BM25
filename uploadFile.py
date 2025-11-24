"""
文档上传处理模块
处理Excel文档上传到standardDataset目录
处理知识库文档上传到knowledgeDoc目录
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
import pandas as pd
import datetime

def upload_document(file_path: str, target_filename: Optional[str] = None, original_filename: Optional[str] = None) -> dict:
    """
    上传文档到standardDataset目录
    
    Args:
        file_path: 上传文件的临时路径
        target_filename: 目标文件名，如果为None则自动生成
        original_filename: 原始文件名，用于生成目标文件名
        
    Returns:
        dict: 上传结果
    """
    try:
        # 确保standardDataset目录存在
        target_dir = Path("standardDataset")
        target_dir.mkdir(exist_ok=True)
        
        # 如果没有指定target_filename，则生成带时间戳的文件名
        if target_filename is None:
            if original_filename:
                # 获取文件名和扩展名
                file_stem = Path(original_filename).stem
                file_suffix = Path(original_filename).suffix
                # 生成时间戳格式：YYYY-MM-DD_HH-MM (使用下划线和短横线，避免空格和冒号)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                target_filename = f"{file_stem}_{timestamp}{file_suffix}"
            else:
                # 如果没有原始文件名，从file_path中读取扩展名
                file_suffix = Path(file_path).suffix
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                target_filename = f"standardDataset_{timestamp}{file_suffix}"
        
        # 目标文件路径
        target_path = target_dir / target_filename
        
        # 验证文件是否为Excel格式
        if not file_path.lower().endswith(('.xlsx', '.xls')):
            return {
                "success": False,
                "message": "只支持Excel文档格式(.xlsx, .xls)"
            }
        
        # 验证Excel文件内容
        validation_result = validate_excel_file(file_path)
        if not validation_result["success"]:
            return validation_result
        
        # 复制文件到目标位置（如果存在同名文件则替换）
        shutil.copy2(file_path, target_path)
        
        # 验证上传后的文件
        if target_path.exists():
            file_size = target_path.stat().st_size
            return {
                "success": True,
                "message": f"文档上传成功！文件已保存为 {target_filename}",
                "file_path": str(target_path),
                "file_size": file_size,
                "validation": validation_result
            }
        else:
            return {
                "success": False,
                "message": "文件上传失败，目标文件不存在"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"上传过程中出现错误: {str(e)}"
        }

def validate_excel_file(file_path: str) -> dict:
    """
    验证Excel文件格式和字段
    
    Args:
        file_path: Excel文件路径
        
    Returns:
        dict: 验证结果
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
        
        # 检查必要的列是否存在
        required_columns = [
            'user_input',
            'retrieved_contexts', 
            'response',
            'reference_contexts',
            'reference'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                "success": False,
                "message": f"Excel文件缺少必要字段: {', '.join(missing_columns)}",
                "required_columns": required_columns,
                "found_columns": list(df.columns)
            }
        
        # 检查数据行数
        row_count = len(df)
        if row_count == 0:
            return {
                "success": False,
                "message": "Excel文件为空，没有数据行"
            }
        
        # 检查是否有空行
        empty_rows = 0
        try:
            # 使用更简单的方式计算空行数
            for i in range(len(df)):
                if df.iloc[i].isnull().all():
                    empty_rows += 1
        except Exception:
            empty_rows = 0
        
        return {
            "success": True,
            "message": "Excel文件格式验证通过",
            "row_count": int(row_count),  # 转换为Python int
            "empty_rows": int(empty_rows),  # 转换为Python int
            "columns": list(df.columns),
            "sample_data": df.head(2).to_dict('records') if row_count > 0 else []
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Excel文件验证失败: {str(e)}"
        }

def get_upload_info() -> dict:
    """
    获取上传相关信息
    
    Returns:
        dict: 上传信息
    """
    target_dir = Path("standardDataset")
    target_file = target_dir / "standardDataset.xlsx"
    
    info = {
        "target_directory": str(target_dir),
        "target_filename": "standardDataset.xlsx",
        "file_exists": target_file.exists(),
        "supported_formats": [".xlsx", ".xls"]
    }
    
    if target_file.exists():
        stat = target_file.stat()
        info.update({
            "file_size": stat.st_size,
            "last_modified": stat.st_mtime,
            "file_path": str(target_file)
        })
        
        # 尝试读取文件信息
        try:
            df = pd.read_excel(target_file)
            info.update({
                "row_count": int(len(df)),  # 转换为Python int
                "columns": list(df.columns)
            })
        except Exception as e:
            info["read_error"] = str(e)
    
    return info

def get_dataset_files() -> dict:
    """
    获取standardDataset目录下的所有数据集文件
    
    Returns:
        dict: 文件列表信息
    """
    try:
        target_dir = Path("standardDataset")
        
        if not target_dir.exists():
            return {
                "success": True,
                "data": [],
                "message": "standardDataset目录不存在"
            }
        
        files = []
        # 只获取Excel文件
        for file_path in target_dir.glob("*.xlsx"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "last_modified": stat.st_mtime,
                    "is_standard": file_path.name == "standardDataset.xlsx"
                })
        
        # 按最后修改时间倒序排列
        files.sort(key=lambda x: x["last_modified"], reverse=True)
        
        return {
            "success": True,
            "data": files,
            "message": f"找到 {len(files)} 个数据集文件"
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取数据集文件列表失败: {str(e)}"
        }

def delete_uploaded_file() -> dict:
    """
    删除已上传的文件
    
    Returns:
        dict: 删除结果
    """
    try:
        target_file = Path("standardDataset") / "standardDataset.xlsx"
        
        if target_file.exists():
            target_file.unlink()
            return {
                "success": True,
                "message": "文件删除成功"
            }
        else:
            return {
                "success": False,
                "message": "文件不存在，无需删除"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"删除文件失败: {str(e)}"
        }

# 测试函数
def test_upload_functionality():
    """测试上传功能"""
    print("🔍 测试文档上传功能...")
    
    # 测试获取上传信息
    info = get_upload_info()
    print(f"📋 上传信息: {info}")
    
    # 测试验证功能（如果有现有文件）
    if info["file_exists"]:
        validation = validate_excel_file(info["file_path"])
        print(f"📋 文件验证结果: {validation}")
    
    print("✅ 上传功能测试完成")

# 知识库文档上传相关函数

def upload_knowledge_document(file_path: str, filename: str) -> dict:
    """
    上传知识库文档到knowledgeDoc目录
    
    Args:
        file_path: 上传文件的临时路径
        filename: 原始文件名
        
    Returns:
        dict: 上传结果
    """
    try:
        # 确保knowledgeDoc目录存在
        target_dir = Path("knowledgeDoc")
        target_dir.mkdir(exist_ok=True)
        
        # 目标文件路径
        target_path = target_dir / filename
        
        # 验证文件格式
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md']
        file_extension = Path(filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            return {
                "success": False,
                "message": f"不支持的文件格式: {file_extension}。支持的格式: {', '.join(allowed_extensions)}"
            }
        
        # 复制文件到目标位置（如果存在同名文件则替换）
        shutil.copy2(file_path, target_path)
        
        # 验证上传后的文件
        if target_path.exists():
            file_size = target_path.stat().st_size
            upload_time = datetime.datetime.now().isoformat()
            
            return {
                "success": True,
                "message": f"知识库文档上传成功！文件已保存为 {filename}",
                "file_path": str(target_path),
                "file_size": file_size,
                "upload_time": upload_time,
                "filename": filename
            }
        else:
            return {
                "success": False,
                "message": "文件上传失败，目标文件不存在"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"上传过程中出现错误: {str(e)}"
        }

def get_knowledge_documents() -> dict:
    """
    获取knowledgeDoc目录中的所有文档信息
    
    Returns:
        dict: 文档列表信息
    """
    try:
        target_dir = Path("knowledgeDoc")
        
        if not target_dir.exists():
            return {
                "success": True,
                "data": []
            }
        
        documents = []
        for file_path in target_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                documents.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "upload_time": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "file_path": str(file_path)
                })
        
        # 按上传时间倒序排列
        documents.sort(key=lambda x: x["upload_time"], reverse=True)
        
        return {
            "success": True,
            "data": documents
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取文档列表失败: {str(e)}"
        }

def delete_knowledge_document(filename: str) -> dict:
    """
    删除knowledgeDoc目录中的指定文档
    
    Args:
        filename: 要删除的文件名
        
    Returns:
        dict: 删除结果
    """
    try:
        target_file = Path("knowledgeDoc") / filename
        
        if target_file.exists():
            target_file.unlink()
            return {
                "success": True,
                "message": f"文档 {filename} 删除成功"
            }
        else:
            return {
                "success": False,
                "message": f"文档 {filename} 不存在"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"删除文档失败: {str(e)}"
        }

# 测试函数
def test_knowledge_upload_functionality():
    """测试知识库文档上传功能"""
    print("🔍 测试知识库文档上传功能...")
    
    # 测试获取文档列表
    docs = get_knowledge_documents()
    print(f"📋 知识库文档列表: {docs}")
    
    print("✅ 知识库文档上传功能测试完成")

if __name__ == "__main__":
    test_upload_functionality()
    test_knowledge_upload_functionality()
