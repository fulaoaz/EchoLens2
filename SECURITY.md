# 安全政策

## 支持的版本

我们为以下版本提供安全更新：

| 版本 | 支持状态 |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

---

## 报告安全漏洞

我们非常重视安全问题。如果您发现了安全漏洞，请**不要**通过公开的 GitHub Issues 报告。

### 报告流程

1. **发送邮件**至 fulaoaz@qq.com，包含：
   - 漏洞描述
   - 复现步骤
   - 影响范围
   - 可能的解决方案（如果有）

2. **等待确认**：我们会在 48 小时内确认收到您的报告

3. **协作修复**：我们会与您协作修复漏洞

4. **发布修复**：修复完成后，我们会发布安全更新

5. **公开致谢**：在您同意的情况下，我们会在安全公告中致谢

### 响应时间

- **初步响应**：48 小时内
- **漏洞确认**：7 天内
- **修复发布**：根据严重程度，14-90 天

---

## 安全最佳实践

### 部署安全

#### 1. 环境变量保护

**不要**将敏感信息提交到代码仓库：

```bash
# ❌ 错误
LLM_API_KEY=sk-1234567890abcdef

# ✅ 正确
# 使用环境变量或密钥管理服务
export LLM_API_KEY=sk-1234567890abcdef
```

**使用 `.env` 文件**：

```bash
# .env 文件应该在 .gitignore 中
echo ".env" >> .gitignore
```

#### 2. HTTPS 配置

生产环境**必须**使用 HTTPS：

```nginx
# Nginx 配置示例
server {
    listen 443 ssl http2;
    server_name echolens.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 其他配置...
}
```

#### 3. 防火墙配置

限制对后端服务的直接访问：

```bash
# 只允许本地访问后端
ufw allow from 127.0.0.1 to any port 5001

# 允许 Nginx 访问
ufw allow 'Nginx Full'
```

#### 4. 数据库安全

- 使用强密码
- 限制数据库访问权限
- 定期备份数据
- 加密敏感数据

#### 5. API 密钥管理

**推荐使用密钥管理服务**：

- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault
- Google Cloud Secret Manager

**本地开发**：

```bash
# 使用 .env 文件
cp .env.example .env
# 编辑 .env，填入密钥
# 确保 .env 在 .gitignore 中
```

### 应用安全

#### 1. 输入验证

**后端**：

```python
from pydantic import BaseModel, Field, validator

class CrawlerRequest(BaseModel):
    platform: str = Field(..., regex="^(jd|taobao|weibo|xiaohongshu)$")
    keywords: list[str] = Field(..., min_items=1, max_items=10)
    max_items: int = Field(100, ge=1, le=10000)

    @validator('keywords')
    def validate_keywords(cls, v):
        for keyword in v:
            if len(keyword) > 100:
                raise ValueError('Keyword too long')
        return v
```

**前端**：

```typescript
// 使用 Zod 进行验证
import { z } from 'zod'

const projectSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500),
})

function validateProject(data: unknown) {
  return projectSchema.parse(data)
}
```

#### 2. XSS 防护

**前端**：

```typescript
// Vue 3 自动转义 HTML
// ✅ 安全
<template>
  <div>{{ userInput }}</div>
</template>

// ❌ 危险（避免使用 v-html）
<template>
  <div v-html="userInput"></div>
</template>

// 如果必须使用 v-html，先清理输入
import DOMPurify from 'dompurify'

const cleanHtml = DOMPurify.sanitize(userInput)
```

**后端**：

```python
from markupsafe import escape

def render_user_content(content: str) -> str:
    return escape(content)
```

#### 3. SQL 注入防护

**使用参数化查询**：

```python
# ✅ 安全
cursor.execute(
    "SELECT * FROM projects WHERE name = ?",
    (project_name,)
)

# ❌ 危险
cursor.execute(
    f"SELECT * FROM projects WHERE name = '{project_name}'"
)
```

#### 4. CSRF 防护

**后端**：

```python
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)
```

**前端**：

```typescript
// Axios 自动处理 CSRF token
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
```

#### 5. 速率限制

**后端**：

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route("/api/projects", methods=["POST"])
@limiter.limit("10 per minute")
def create_project():
    # ...
```

#### 6. 认证与授权

**JWT Token**（未来版本）：

```python
from flask_jwt_extended import JWTManager, jwt_required

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

@app.route("/api/projects", methods=["GET"])
@jwt_required()
def get_projects():
    # ...
```

### 依赖安全

#### 1. 定期更新依赖

**后端**：

```bash
# 检查过时的包
uv pip list --outdated

# 更新包
uv pip install --upgrade package-name
```

**前端**：

```bash
# 检查过时的包
npm outdated

# 更新包
npm update

# 检查安全漏洞
npm audit

# 自动修复
npm audit fix
```

#### 2. 使用依赖扫描工具

- **Dependabot**（GitHub）：自动创建 PR 更新依赖
- **Snyk**：扫描已知漏洞
- **Safety**（Python）：检查 Python 依赖安全性

```bash
# 安装 Safety
pip install safety

# 检查依赖
safety check
```

#### 3. 锁定依赖版本

**后端**：

```txt
# requirements.txt
flask==3.0.0
pydantic==2.5.0
```

**前端**：

```json
// package.json
{
  "dependencies": {
    "vue": "3.5.0",
    "naive-ui": "2.40.0"
  }
}
```

### 数据安全

#### 1. 敏感数据加密

**存储加密**：

```python
from cryptography.fernet import Fernet

# 生成密钥
key = Fernet.generate_key()
cipher = Fernet(key)

# 加密
encrypted = cipher.encrypt(b"sensitive data")

# 解密
decrypted = cipher.decrypt(encrypted)
```

#### 2. 日志脱敏

**不要记录敏感信息**：

```python
# ❌ 危险
logger.info(f"User API key: {api_key}")

# ✅ 安全
logger.info(f"User API key: {api_key[:8]}...")
```

#### 3. 数据备份

定期备份数据，并加密备份文件：

```bash
# 备份数据库
sqlite3 data.db ".backup 'backup.db'"

# 加密备份
gpg --encrypt --recipient your@email.com backup.db
```

### Docker 安全

#### 1. 使用非 root 用户

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 切换到非 root 用户
USER appuser

# ...
```

#### 2. 最小化镜像

```dockerfile
# 使用 slim 或 alpine 基础镜像
FROM python:3.11-slim

# 只安装必要的包
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*
```

#### 3. 扫描镜像漏洞

```bash
# 使用 Trivy 扫描
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image echolens:latest
```

---

## 安全检查清单

### 部署前检查

- [ ] 所有敏感信息都使用环境变量
- [ ] HTTPS 已配置
- [ ] 防火墙规则已设置
- [ ] 数据库访问受限
- [ ] API 密钥已安全存储
- [ ] 依赖已更新到最新安全版本
- [ ] 日志不包含敏感信息
- [ ] 备份策略已实施
- [ ] 速率限制已配置
- [ ] CSRF 保护已启用

### 定期检查

- [ ] 每月检查依赖更新
- [ ] 每季度进行安全审计
- [ ] 每年更新 SSL 证书
- [ ] 定期审查访问日志
- [ ] 定期测试备份恢复

---

## 已知安全限制

### 当前版本（2.0.0-rc1）

1. **无认证系统**：当前版本不包含用户认证，适合内网部署
2. **无速率限制**：API 请求无速率限制
3. **无审计日志**：不记录用户操作审计日志

### 计划改进

- [ ] 添加 JWT 认证系统
- [ ] 实施 API 速率限制
- [ ] 添加操作审计日志
- [ ] 实施细粒度权限控制
- [ ] 添加数据加密选项

---

## 安全更新通知

订阅安全更新：

- **GitHub Watch**：Watch 仓库并选择 "Releases only"
- **邮件列表**：发送邮件至 fulaoaz@qq.com
- **RSS Feed**：订阅 GitHub Releases RSS

---

## 联系方式

- **安全问题报告**：fulaoaz@qq.com
- **一般问题**：fulaoaz@qq.com
- **GitHub Issues**：https://github.com/yourusername/echolens/issues

---

## 致谢

感谢所有负责任地披露安全漏洞的研究人员。

---

**最后更新**：2026-05-25  
**版本**：2.0.0-rc1
