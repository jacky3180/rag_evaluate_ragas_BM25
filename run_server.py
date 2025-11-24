from config import debug_print, verbose_print, info_print, error_print, QUIET_MODE
#!/usr/bin/env python3
"""
RAG评估系统启动脚本
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

def main():
    """启动Web服务器"""
    # 加载环境变量
    load_dotenv()
    
    # 检查必要的环境变量
    required_vars = ['QWEN_API_KEY', 'QWEN_API_BASE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        info_print("❌ 缺少必要的环境变量:")
        for var in missing_vars:
            info_print(f"  - {var}")
        info_print("\n请在.env文件中设置这些变量，或设置系统环境变量")
        info_print("示例.env文件内容:")
        info_print("QWEN_API_KEY=your_api_key_here")
        info_print("QWEN_API_BASE=https://your-api-base-url")
        info_print("QWEN_MODEL_NAME=qwen-plus")
        info_print("QWEN_EMBEDDING_MODEL=text-embedding-v1")
        info_print("EXCEL_FILE_PATH=standardDataset/standardDataset.xlsx")
        return 1
    
    # 检查数据文件
    excel_file = os.getenv('EXCEL_FILE_PATH')
    if not excel_file:
        info_print("⚠️  警告: 未设置EXCEL_FILE_PATH环境变量")
        info_print("请在.env文件中设置EXCEL_FILE_PATH=standardDataset/standardDataset.xlsx")
        excel_file = None
    if excel_file and not os.path.exists(excel_file):
        info_print(f"⚠️  警告: 数据文件不存在: {excel_file}")
        info_print("请确保数据文件存在，或设置正确的EXCEL_FILE_PATH环境变量")
    
    info_print("🚀 启动RAG评估系统...")
    info_print("=" * 50)
    info_print(f"📊 数据文件: {excel_file}")
    info_print(f"🤖 模型: {os.getenv('QWEN_MODEL_NAME', 'qwen-plus')}")
    info_print(f"🔧 Embedding模型: {os.getenv('QWEN_EMBEDDING_MODEL', 'text-embedding-v1')}")
    info_print("=" * 50)
    info_print("🌐 访问地址: http://localhost:8000")
    info_print("📚 API文档: http://localhost:8000/docs")
    info_print("=" * 50)
    
    try:
        # 启动服务器
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        info_print("\n👋 服务器已停止")
        return 0
    except Exception as e:
        info_print(f"❌ 启动失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
