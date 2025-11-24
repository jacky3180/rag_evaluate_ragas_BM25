# Contributing Guide

感谢你愿意为 **RAG评估系统** 做出贡献！为了保持项目稳定可靠，请在提交贡献前阅读并遵循以下指南。

## 参与方式

1. **提出想法或问题**  
   - 使用 GitHub Issues 描述 Bug、改进建议或新功能需求。  
   - 尽量提供复现步骤、截图或日志，帮助我们更快定位问题。

2. **认领任务**  
   - 在对应 Issue 下留言认领。若超过 3 天未提交进展，任务会重新开放给其他贡献者。

3. **提交变更**  
   - Fork 本仓库并创建特性分支，例如 `feat/add-mrr-docs`。  
   - 变更完成后提交 Pull Request，并在描述中关联相关 Issue。

## 开发准则

- **模块化与抽象**：新增功能必须使用函数或类进行封装，避免将全部逻辑写在一个代码块中。  
- **配置与密钥**：任何访问密钥、模型配置等都必须从 `.env` 读取，禁止硬编码。  
- **测试隔离**：测试、调试脚本及虚拟数据必须放置在 `test/` 目录，评估结束后如无必要请删除临时文件。  
- **文档同步**：新增或变更功能时，请更新 `README.md`、相关模块文档以及 `CHANGELOG.md`。  
- **代码风格**：遵循 PEP 8，保持清晰的命名与注释。必要时请补充类型注解。  
- **提交信息**：使用简洁明确的英文描述，如 `fix: handle empty retrieved contexts`。

## 开发环境

1. 克隆仓库并安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 复制环境变量模版并填写实际值：
   ```bash
   cp env.example .env
   ```
3. 如需本地运行 Web 界面：
   ```bash
   python run_server.py
   ```

## 质量保障

- 请针对修改运行相应的评估脚本（如 `rag_evaluator.py`、`BM25_evaluate.py`）。  
- 如果引入了新模块或关键逻辑，建议在 `test/` 下添加自测脚本或说明。  
- 提交前确保：
  - 本地 lint / type check 通过（如适用）。  
  - 未提交 `.env`、数据库文件或其他敏感信息。  
  - `CHANGELOG.md` 已记录变更。

## 社区守则

本项目遵循 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。请以尊重、包容的态度参与讨论和协作。

## 发布流程（维护者）

1. 更新版本号与 `CHANGELOG.md`。  
2. 确认测试通过、依赖可安装。  
3. 创建 GitHub Release，并附上更新摘要。

期待你的贡献！🙏

