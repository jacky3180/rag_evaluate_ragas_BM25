import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 测试表格筛选功能
def test_filter_function():
    """测试修复后的filterDataByDate函数"""
    
    # 模拟数据
    mock_data = [
        {'created_at': '2025-10-10T10:30:00', 'value': 0.80},
        {'created_at': '2025-10-12T14:45:00', 'value': 0.85},
        {'created_at': '2025-10-15T16:20:00', 'value': 0.90},
    ]
    
    # 修复后的filterDataByDate函数
    def filter_data_by_date(data, start_date, end_date):
        # 修复：移除 isDateFiltered 检查
        if not data or not start_date or not end_date: 
            return data
        
        from datetime import datetime, time
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        start = datetime.combine(start.date(), time.min)  # 设置为当天的00:00:00
        end = datetime.strptime(end_date, '%Y-%m-%d')
        end = datetime.combine(end.date(), time.max)  # 设置为当天的23:59:59.999999
        
        # 筛选指定时间范围内的所有数据
        filtered_data = []
        for item in data:
            item_date = datetime.fromisoformat(item['created_at'])
            if start <= item_date <= end:
                filtered_data.append(item)
        
        return filtered_data
    
    # 测试筛选
    start_date = '2025-10-10'
    end_date = '2025-10-15'
    
    filtered_data = filter_data_by_date(mock_data, start_date, end_date)
    
    print(f"原始数据数量: {len(mock_data)}")
    print(f"筛选日期范围: {start_date} 至 {end_date}")
    print(f"筛选后数据数量: {len(filtered_data)}")
    
    for item in filtered_data:
        print(f"  时间: {item['created_at']}, 值: {item['value']}")

if __name__ == "__main__":
    test_filter_function()