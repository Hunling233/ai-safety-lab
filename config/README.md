# 配置说明 / Configuration Guide

## OpenAI API 配置

本项目需要 OpenAI API Key 来运行可解释性测试和其他功能。

### 快速设置

1. **复制配置模板**
   ```bash
   cp config/openai.env.example config/openai.env
   ```

2. **编辑配置文件**
   ```bash
   # 在 config/openai.env 中设置你的 API Key
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

3. **或使用环境变量**
   ```powershell
   # PowerShell
   $env:OPENAI_API_KEY="sk-your-actual-api-key-here"
   ```
   
   ```bash
   # Linux/Mac
   export OPENAI_API_KEY="sk-your-actual-api-key-here"
   ```

### 获取 API Key

1. 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
2. 登录你的 OpenAI 账户
3. 点击 "Create new secret key"
4. 复制生成的 API Key
5. 将其粘贴到配置文件中

### 验证配置

运行以下命令验证配置是否正确：

```bash
python orchestrator/Li-run.py
```

如果配置正确，你会看到 "✅ 从配置文件获取 OPENAI_API_KEY" 的提示。

### 安全提醒

- ⚠️ **永远不要**将真实的 API Key 提交到版本控制系统
- ✅ `openai.env` 文件已在 `.gitignore` 中被忽略
- ✅ 只提交 `openai.env.example` 模板文件
- 🔒 将 API Key 视为密码，不要在代码或文档中明文展示

### 配置优先级

系统按以下优先级查找 API Key：

1. **环境变量** `OPENAI_API_KEY` (最高优先级)
2. **配置文件** `config/openai.env`

### 故障排除

如果遇到 "❌ 未找到有效的 OPENAI_API_KEY" 错误：

1. 检查 `config/openai.env` 文件是否存在
2. 确认 API Key 格式正确（以 `sk-` 开头）
3. 验证 API Key 有效性（在 OpenAI Dashboard 中检查）
4. 确保没有多余的空格或引号

### 支持的功能

配置完成后，以下功能将可用：
- 可解释性测试 (`testsuites/explainability/`)
- AI 安全性评估
- 模型对话和分析