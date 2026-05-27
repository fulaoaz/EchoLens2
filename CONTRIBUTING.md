# 贡献指南

感谢您对 EchoLens 2.0 的关注！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复或新功能
- 🌍 翻译文档

---

## 目录

1. [行为准则](#行为准则)
2. [如何贡献](#如何贡献)
3. [开发环境设置](#开发环境设置)
4. [代码规范](#代码规范)
5. [提交规范](#提交规范)
6. [Pull Request 流程](#pull-request-流程)
7. [测试要求](#测试要求)
8. [文档贡献](#文档贡献)
9. [问题反馈](#问题反馈)

---

## 行为准则

### 我们的承诺

为了营造一个开放和友好的环境，我们承诺：

- 尊重不同的观点和经验
- 接受建设性的批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

### 不可接受的行为

- 使用性化的语言或图像
- 人身攻击或侮辱性评论
- 公开或私下的骚扰
- 未经许可发布他人的私人信息
- 其他不道德或不专业的行为

---

## 如何贡献

### 报告 Bug

如果您发现了 Bug，请通过 [GitHub Issues](https://github.com/fulaoaz/EchoLens2/issues) 报告。

**Bug 报告应包含**：

1. **清晰的标题**：简洁描述问题
2. **复现步骤**：详细的操作步骤
3. **期望行为**：您期望发生什么
4. **实际行为**：实际发生了什么
5. **环境信息**：
   - 操作系统和版本
   - Python 版本
   - Node.js 版本
   - 浏览器和版本（如果是前端问题）
6. **截图或日志**：如果适用
7. **可能的解决方案**：如果您有想法

**示例**：

```markdown
## Bug 描述
数据采集时，微博平台返回 403 错误

## 复现步骤
1. 创建新项目
2. 配置微博爬虫，关键词 "iPhone 15"
3. 点击"开始采集"
4. 等待 10 秒后出现错误

## 期望行为
成功采集微博数据

## 实际行为
返回 403 Forbidden 错误

## 环境信息
- OS: Windows 11
- Python: 3.11.5
- 浏览器: Chrome 120

## 错误日志
```
[ERROR] Weibo crawler failed: 403 Forbidden
```

## 可能的解决方案
可能需要更新 User-Agent 或添加请求头
```

### 提出新功能

如果您有新功能的想法，请先通过 [GitHub Issues](https://github.com/fulaoaz/EchoLens2/issues) 讨论。

**功能建议应包含**：

1. **功能描述**：清晰描述新功能
2. **使用场景**：为什么需要这个功能
3. **预期效果**：功能应该如何工作
4. **替代方案**：是否考虑过其他方案
5. **额外信息**：相关截图、原型或参考

---

## 开发环境设置

### 前置要求

- **Python**: ≥ 3.11
- **Node.js**: ≥ 18
- **Git**: 最新版本
- **uv**: Python 包管理器（推荐）

### 克隆仓库

```bash
git clone https://github.com/fulaoaz/EchoLens2.git
cd echolens
```

### 后端设置

```bash
cd backend

# 创建虚拟环境
uv venv .venv

# 安装依赖（开发模式）
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"

# 运行测试
.venv/Scripts/python -m pytest -q

# 启动后端
.venv/Scripts/python run.py
```

### 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 运行单元测试
npm run test

# 运行 E2E 测试（需要后端运行）
npm run test:e2e:ui

# 启动开发服务器
npm run dev
```

### 环境变量

复制 `.env.example` 为 `.env` 并填入必要的配置：

```bash
cp .env.example .env
```

必需的环境变量：

- `LLM_API_KEY`: LLM API 密钥
- `LLM_BASE_URL`: LLM API 基础 URL（可选）
- `LLM_MODEL_NAME`: LLM 模型名称（可选）

---

## 代码规范

### Python 代码规范

我们遵循 [PEP 8](https://pep8.org/) 和 [PEP 484](https://www.python.org/dev/peps/pep-0484/)（类型注解）。

**工具**：

- **Formatter**: `black`
- **Linter**: `ruff`
- **Type Checker**: `mypy`

**运行检查**：

```bash
cd backend

# 格式化代码
black app/ tests/

# 运行 linter
ruff check app/ tests/

# 类型检查
mypy app/
```

**代码风格**：

- 使用 4 空格缩进
- 最大行长度 88 字符（black 默认）
- 使用类型注解
- 编写 docstring（Google 风格）

**示例**：

```python
from typing import List, Optional

def fetch_data(
    platform: str,
    keywords: List[str],
    max_items: int = 100
) -> Optional[List[dict]]:
    """从指定平台采集数据。

    Args:
        platform: 平台名称（jd, taobao, weibo, xiaohongshu）
        keywords: 关键词列表
        max_items: 最大采集数量，默认 100

    Returns:
        采集到的数据列表，失败时返回 None

    Raises:
        ValueError: 当平台名称无效时
    """
    if platform not in ["jd", "taobao", "weibo", "xiaohongshu"]:
        raise ValueError(f"Invalid platform: {platform}")
    
    # 实现逻辑...
    return []
```

### JavaScript/TypeScript 代码规范

我们遵循 [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)。

**工具**：

- **Formatter**: `prettier`
- **Linter**: `eslint`

**运行检查**：

```bash
cd frontend

# 运行 linter
npm run lint

# 自动修复
npm run lint:fix

# 格式化代码
npm run format
```

**代码风格**：

- 使用 2 空格缩进
- 使用单引号
- 使用 TypeScript 类型注解
- 使用组合式 API（Composition API）

**示例**：

```typescript
import { ref, computed } from 'vue'

interface Project {
  id: string
  name: string
  description: string
}

/**
 * 项目管理 composable
 */
export function useProjects() {
  const projects = ref<Project[]>([])
  const loading = ref(false)

  const projectCount = computed(() => projects.value.length)

  async function fetchProjects(): Promise<void> {
    loading.value = true
    try {
      const response = await api.get('/projects')
      projects.value = response.data
    } finally {
      loading.value = false
    }
  }

  return {
    projects,
    loading,
    projectCount,
    fetchProjects,
  }
}
```

---

## 提交规范

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范。

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构（既不是新功能也不是 Bug 修复）
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动
- `ci`: CI 配置文件和脚本的变动
- `revert`: 回滚之前的提交

### Scope 范围（可选）

- `backend`: 后端相关
- `frontend`: 前端相关
- `crawler`: 爬虫相关
- `simulation`: 仿真相关
- `prediction`: 预测相关
- `decision`: 决策相关
- `report`: 报告相关
- `docs`: 文档相关

### 示例

```bash
# 新功能
git commit -m "feat(crawler): add Xiaohongshu crawler support"

# Bug 修复
git commit -m "fix(frontend): resolve decision board chip highlight issue"

# 文档更新
git commit -m "docs: update API documentation for prediction endpoints"

# 重构
git commit -m "refactor(backend): extract reliability tier calculation to shared module"

# 性能优化
git commit -m "perf(frontend): optimize ECharts bundle size with code splitting"
```

### 提交消息最佳实践

1. **使用祈使句**：`add` 而不是 `added` 或 `adds`
2. **首字母小写**：`feat: add feature` 而不是 `feat: Add feature`
3. **不要以句号结尾**
4. **简洁明了**：主题行不超过 50 字符
5. **详细的 body**：如果需要，在 body 中详细说明

---

## Pull Request 流程

### 1. Fork 仓库

点击 GitHub 页面右上角的 "Fork" 按钮。

### 2. 克隆您的 Fork

```bash
git clone https://github.com/your-username/echolens.git
cd echolens
```

### 3. 创建分支

```bash
git checkout -b feature/your-feature-name
```

分支命名规范：

- `feature/xxx`: 新功能
- `fix/xxx`: Bug 修复
- `docs/xxx`: 文档更新
- `refactor/xxx`: 重构

### 4. 进行更改

- 编写代码
- 添加测试
- 更新文档

### 5. 提交更改

```bash
git add .
git commit -m "feat: add your feature"
```

### 6. 推送到您的 Fork

```bash
git push origin feature/your-feature-name
```

### 7. 创建 Pull Request

1. 访问您的 Fork 页面
2. 点击 "New Pull Request"
3. 填写 PR 描述

**PR 描述应包含**：

- **标题**：清晰描述更改
- **描述**：详细说明更改内容
- **相关 Issue**：如果有，使用 `Closes #123`
- **测试**：说明如何测试
- **截图**：如果是 UI 更改
- **Checklist**：确认所有检查项

**PR 模板**：

```markdown
## 描述
简要描述此 PR 的更改内容。

## 相关 Issue
Closes #123

## 更改类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 重构
- [ ] 文档更新
- [ ] 性能优化

## 测试
描述如何测试这些更改。

## 截图（如果适用）
添加截图以帮助解释您的更改。

## Checklist
- [ ] 代码遵循项目的代码规范
- [ ] 已添加必要的测试
- [ ] 所有测试通过
- [ ] 已更新相关文档
- [ ] 提交消息遵循 Conventional Commits 规范
```

### 8. 代码审查

- 维护者会审查您的 PR
- 根据反馈进行修改
- 所有检查通过后，PR 将被合并

---

## 测试要求

### 后端测试

**必须**：

- 新功能必须包含单元测试
- Bug 修复必须包含回归测试
- 测试覆盖率不低于 80%

**运行测试**：

```bash
cd backend

# 运行所有测试
.venv/Scripts/python -m pytest

# 运行特定测试
.venv/Scripts/python -m pytest tests/test_crawler.py

# 查看覆盖率
.venv/Scripts/python -m pytest --cov=app --cov-report=html
```

**测试示例**：

```python
import pytest
from app.services.crawler import fetch_data

def test_fetch_data_success():
    """测试成功采集数据"""
    result = fetch_data("jd", ["iPhone 15"], max_items=10)
    assert result is not None
    assert len(result) <= 10

def test_fetch_data_invalid_platform():
    """测试无效平台"""
    with pytest.raises(ValueError):
        fetch_data("invalid", ["test"])
```

### 前端测试

**必须**：

- 新组件必须包含单元测试
- 关键路径必须包含 E2E 测试

**运行测试**：

```bash
cd frontend

# 单元测试
npm run test

# E2E 测试
npm run test:e2e:ui

# 覆盖率
npm run test:coverage
```

**测试示例**：

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ProjectCard from '@/components/ProjectCard.vue'

describe('ProjectCard', () => {
  it('renders project name', () => {
    const wrapper = mount(ProjectCard, {
      props: {
        project: {
          id: '1',
          name: 'Test Project',
          description: 'Test Description',
        },
      },
    })
    expect(wrapper.text()).toContain('Test Project')
  })
})
```

---

## 文档贡献

### 文档类型

- **用户文档**：`docs/USER_MANUAL.md`
- **API 文档**：`docs/API.md`
- **开发文档**：`PROGRESS.md`
- **部署文档**：`DEPLOYMENT.md`

### 文档规范

- 使用 Markdown 格式
- 使用清晰的标题层级
- 添加代码示例
- 包含截图（如果适用）
- 保持中英文版本同步

### 更新文档

如果您的更改影响了用户使用或 API，请同时更新相关文档。

---

## 问题反馈

### 提问前

1. 搜索现有 Issues，避免重复
2. 查看文档和 FAQ
3. 尝试最新版本

### 提问时

- 使用清晰的标题
- 提供详细的上下文
- 包含复现步骤
- 附上相关日志或截图

### 获取帮助

- **GitHub Issues**: 报告 Bug 和功能请求
- **GitHub Discussions**: 一般性讨论和问题
- **邮件**: fulaoaz@qq.com

---

## 许可证

通过贡献代码，您同意您的贡献将在 [AGPL-3.0](LICENSE) 许可证下发布。

---

## 致谢

感谢所有贡献者！您的贡献让 EchoLens 变得更好。

---

**再次感谢您的贡献！** 🎉
