# 性能优化 - 快速启动指南

## 🚀 5分钟启用性能优化

### 步骤1: 应用数据库索引（必需）

```bash
# 在项目根目录执行
python database/apply_performance_indexes.py
```

**预期输出**:
```
🚀 开始应用数据库性能优化索引...
📊 数据库类型: SQLITE
📝 找到 9 个索引创建语句
  [1/9] 创建索引: idx_bm25_evaluation_time...
  [2/9] 创建索引: idx_bm25_created_at...
  ...
📊 索引应用结果统计:
  ✅ 成功创建: 9 个
  ⏭️  已存在跳过: 0 个
  ❌ 创建失败: 0 个
🎉 数据库性能优化索引应用成功！
```

### 步骤2: 重启服务（必需）

```bash
# 停止当前服务（Ctrl+C）
# 重新启动
python run_server.py
```

### 步骤3: 验证优化效果

访问历史数据页面：
```
http://localhost:8000/static/history.html
```

观察浏览器控制台输出：
```
📊 开始批量加载图表数据...
✅ 图表加载完成，耗时: 523.45ms  # 优化后应该在1秒以内
```

---

## ✅ 优化已自动启用的功能

以下优化功能已集成到代码中，无需额外配置：

- ✅ API响应缓存（自动）
- ✅ 批量数据查询（自动）
- ✅ 前端数据缓存（自动）
- ✅ 防抖节流（自动）
- ✅ Plotly渲染优化（自动）

---

## 🔧 可选配置

### 调整缓存时间

编辑 `api_cache.py`:

```python
# 默认设置
_history_cache = APICache(ttl=300)  # 历史数据缓存5分钟
_stats_cache = APICache(ttl=60)     # 统计数据缓存1分钟
_eval_cache = APICache(ttl=600)     # 评估结果缓存10分钟

# 根据需要调整TTL（秒）
```

### 手动清除缓存

当添加新评估结果后，建议清除缓存：

```bash
curl -X POST http://localhost:8000/api/cache/clear
```

或在浏览器控制台：
```javascript
fetch('/api/cache/clear', {method: 'POST'})
    .then(r => r.json())
    .then(console.log);
```

---

## 📊 性能监控

### 查看缓存统计

```bash
curl http://localhost:8000/api/cache/stats
```

**示例输出**:
```json
{
  "success": true,
  "data": {
    "history_cache": {
      "size": 6,
      "hit_count": 48,
      "miss_count": 8,
      "total_requests": 56,
      "hit_rate": "85.71%",
      "ttl": 300
    },
    ...
  }
}
```

### 监控页面性能

在浏览器开发者工具的 **Network** 标签：

**优化前**:
- 请求数: 8个
- 总时间: ~2.8s
- 传输: ~180KB

**优化后**:
- 请求数: 2个
- 总时间: ~0.8s
- 传输: ~60KB

---

## ⚠️ 注意事项

### 1. 索引创建

- 首次创建可能需要几秒钟
- 已存在的索引会自动跳过
- 不影响现有数据

### 2. 缓存行为

- 缓存在服务重启时清空
- TTL到期后自动失效
- 数据更新后需手动清除缓存

### 3. 兼容性

- 支持MySQL和SQLite
- 支持所有现代浏览器
- 向后兼容旧代码

---

## 🆘 问题排查

### 问题: 索引创建失败

**解决方案**:
```bash
# 检查数据库连接
python database/init_database.py

# 查看详细错误
python database/apply_performance_indexes.py
```

### 问题: 性能没有提升

**检查清单**:
- [ ] 确认索引已成功创建
- [ ] 确认服务已重启
- [ ] 检查缓存统计（命中率应>80%）
- [ ] 清空浏览器缓存后重试

### 问题: 数据不是最新的

**原因**: 缓存未更新

**解决方案**:
```bash
# 清除服务端缓存
curl -X POST http://localhost:8000/api/cache/clear

# 清除浏览器缓存
按 Ctrl+Shift+R 强制刷新
```

---

## 📈 性能对比

| 操作 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 首次加载历史页面 | 2.8s | 0.8s | **71%** ↑ |
| 切换日期筛选 | 1.5s | 0.1s | **93%** ↑ |
| 图表渲染 | 1.2s | 0.5s | **58%** ↑ |

---

## 💡 最佳实践

1. **定期清理缓存**: 每次添加新评估后清除
2. **监控命中率**: 保持在80%以上
3. **适时调整TTL**: 根据更新频率调整
4. **生产环境**: 使用MySQL + 长缓存时间

---

## 📞 获取帮助

- 详细文档: [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)
- 主文档: [README.md](README.md)
- 问题反馈: 创建Issue

---

**最后更新**: 2025-10-29  
**版本**: 1.0.0

