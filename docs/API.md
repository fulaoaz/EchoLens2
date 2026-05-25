# EchoLens 2.0 API 文档

> **版本**: 2.0.0-rc1  
> **更新时间**: 2026-05-25

---

## 目录

1. [概述](#概述)
2. [认证](#认证)
3. [通用规范](#通用规范)
4. [项目管理 API](#项目管理-api)
5. [材料上传 API](#材料上传-api)
6. [数据采集 API](#数据采集-api)
7. [知识图谱 API](#知识图谱-api)
8. [仿真 API](#仿真-api)
9. [预测 API](#预测-api)
10. [决策 API](#决策-api)
11. [报告 API](#报告-api)
12. [系统 API](#系统-api)
13. [错误码](#错误码)

---

## 概述

EchoLens 2.0 提供 RESTful API，支持完整的电商舆情分析工作流。

**Base URL**: `http://localhost:5001/api`

**支持格式**: JSON

**字符编码**: UTF-8

---

## 认证

当前版本暂不需要认证。未来版本将支持 API Key 或 JWT Token。

---

## 通用规范

### 请求头

```http
Content-Type: application/json
Accept: application/json
```

### 响应格式

**成功响应**:

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

**错误响应**:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  }
}
```

### 分页

支持分页的接口使用以下参数：

- `page`: 页码（从 1 开始）
- `page_size`: 每页数量（默认 20，最大 100）

分页响应格式：

```json
{
  "success": true,
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

## 项目管理 API

### 创建项目

**请求**:

```http
POST /api/projects
Content-Type: application/json

{
  "name": "iPhone 15 舆情分析",
  "description": "分析 iPhone 15 在社交媒体上的舆情表现"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "project_id": "proj_abc123",
    "name": "iPhone 15 舆情分析",
    "description": "分析 iPhone 15 在社交媒体上的舆情表现",
    "created_at": "2026-05-25T10:00:00Z",
    "updated_at": "2026-05-25T10:00:00Z",
    "status": "created"
  }
}
```

### 获取项目列表

**请求**:

```http
GET /api/projects?page=1&page_size=20
```

**响应**:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "project_id": "proj_abc123",
        "name": "iPhone 15 舆情分析",
        "description": "...",
        "created_at": "2026-05-25T10:00:00Z",
        "status": "completed"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20
  }
}
```

### 获取项目详情

**请求**:

```http
GET /api/projects/{project_id}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "project_id": "proj_abc123",
    "name": "iPhone 15 舆情分析",
    "description": "...",
    "created_at": "2026-05-25T10:00:00Z",
    "updated_at": "2026-05-25T10:30:00Z",
    "status": "completed",
    "stats": {
      "documents": 5,
      "entities": 120,
      "simulations": 3,
      "predictions": 2,
      "reports": 1
    }
  }
}
```

### 更新项目

**请求**:

```http
PUT /api/projects/{project_id}
Content-Type: application/json

{
  "name": "iPhone 15 Pro 舆情分析",
  "description": "更新后的描述"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "project_id": "proj_abc123",
    "name": "iPhone 15 Pro 舆情分析",
    "description": "更新后的描述",
    "updated_at": "2026-05-25T11:00:00Z"
  }
}
```

### 删除项目

**请求**:

```http
DELETE /api/projects/{project_id}
```

**响应**:

```json
{
  "success": true,
  "message": "项目已删除"
}
```

---

## 材料上传 API

### 上传文件

**请求**:

```http
POST /api/projects/{project_id}/documents
Content-Type: multipart/form-data

file: <binary>
```

**响应**:

```json
{
  "success": true,
  "data": {
    "document_id": "doc_xyz789",
    "filename": "product_intro.pdf",
    "size": 1024000,
    "mime_type": "application/pdf",
    "uploaded_at": "2026-05-25T10:05:00Z",
    "status": "processing"
  }
}
```

### 获取文档列表

**请求**:

```http
GET /api/projects/{project_id}/documents
```

**响应**:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "document_id": "doc_xyz789",
        "filename": "product_intro.pdf",
        "size": 1024000,
        "uploaded_at": "2026-05-25T10:05:00Z",
        "status": "processed"
      }
    ]
  }
}
```

### 获取 Seed Report

**请求**:

```http
GET /api/projects/{project_id}/seed-report
```

**响应**:

```json
{
  "success": true,
  "data": {
    "report_id": "seed_abc123",
    "content": "# Seed Report\n\n## 商品概述\n...",
    "entities": [
      {
        "name": "iPhone 15",
        "type": "Product",
        "properties": { ... }
      }
    ],
    "generated_at": "2026-05-25T10:10:00Z"
  }
}
```

---

## 数据采集 API

### 启动数据采集

**请求**:

```http
POST /api/projects/{project_id}/crawler/start
Content-Type: application/json

{
  "platforms": ["jd", "taobao", "weibo", "xiaohongshu"],
  "keywords": ["iPhone 15", "苹果手机"],
  "max_items": 500
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "task_id": "task_crawler_123",
    "status": "running",
    "started_at": "2026-05-25T10:15:00Z"
  }
}
```

### 获取采集状态

**请求**:

```http
GET /api/projects/{project_id}/crawler/status/{task_id}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "task_id": "task_crawler_123",
    "status": "completed",
    "progress": {
      "total": 500,
      "completed": 500,
      "failed": 0
    },
    "results": {
      "jd": 150,
      "taobao": 120,
      "weibo": 130,
      "xiaohongshu": 100
    },
    "started_at": "2026-05-25T10:15:00Z",
    "completed_at": "2026-05-25T10:25:00Z"
  }
}
```

### 获取采集数据

**请求**:

```http
GET /api/projects/{project_id}/crawler/data?platform=jd&page=1&page_size=20
```

**响应**:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "item_123",
        "platform": "jd",
        "title": "Apple iPhone 15 Pro Max",
        "price": 9999.00,
        "rating": 4.8,
        "comment_count": 5000,
        "collected_at": "2026-05-25T10:20:00Z"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 知识图谱 API

### 构建知识图谱

**请求**:

```http
POST /api/projects/{project_id}/graph/build
Content-Type: application/json

{
  "source": "documents",
  "options": {
    "include_crawler_data": true
  }
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "task_id": "task_graph_456",
    "status": "running",
    "started_at": "2026-05-25T10:30:00Z"
  }
}
```

### 获取图谱统计

**请求**:

```http
GET /api/projects/{project_id}/graph/stats
```

**响应**:

```json
{
  "success": true,
  "data": {
    "entities": {
      "total": 120,
      "by_type": {
        "Product": 5,
        "Brand": 3,
        "User": 80,
        "Topic": 32
      }
    },
    "relationships": {
      "total": 450,
      "by_type": {
        "购买": 80,
        "评论": 150,
        "转发": 120,
        "点赞": 100
      }
    }
  }
}
```

### 搜索实体

**请求**:

```http
GET /api/projects/{project_id}/graph/search?q=iPhone&type=Product
```

**响应**:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "entity_id": "ent_123",
        "name": "iPhone 15",
        "type": "Product",
        "properties": {
          "price": 5999,
          "brand": "Apple"
        },
        "relationships": [
          {
            "type": "购买",
            "target": "ent_456",
            "count": 50
          }
        ]
      }
    ]
  }
}
```

---

## 仿真 API

### 启动仿真

**请求**:

```http
POST /api/projects/{project_id}/simulation/start
Content-Type: application/json

{
  "agent_count": 10000,
  "rounds": 50,
  "stimulus": {
    "type": "positive",
    "intensity": 0.8
  },
  "config": {
    "social_network": "scale_free",
    "influence_model": "threshold"
  }
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim_789",
    "status": "running",
    "started_at": "2026-05-25T10:40:00Z"
  }
}
```

### 获取仿真状态

**请求**:

```http
GET /api/projects/{project_id}/simulation/status/{simulation_id}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim_789",
    "status": "completed",
    "progress": {
      "current_round": 50,
      "total_rounds": 50
    },
    "started_at": "2026-05-25T10:40:00Z",
    "completed_at": "2026-05-25T11:00:00Z"
  }
}
```

### 获取仿真结果

**请求**:

```http
GET /api/projects/{project_id}/simulation/results/{simulation_id}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim_789",
    "metrics": {
      "purchase_intention": {
        "initial": 0.3,
        "final": 0.65,
        "change": 0.35
      },
      "sentiment": {
        "positive": 0.7,
        "neutral": 0.2,
        "negative": 0.1
      },
      "influence_ranking": [
        {
          "agent_id": "agent_001",
          "influence_score": 0.95
        }
      ]
    },
    "time_series": [
      {
        "round": 1,
        "purchase_intention": 0.3,
        "sentiment_positive": 0.5
      }
    ]
  }
}
```

---

## 预测 API

### 启动预测

**请求**:

```http
POST /api/projects/{project_id}/prediction/start
Content-Type: application/json

{
  "type": "time_series",
  "model": "arima",
  "target": "sales",
  "horizon": 30,
  "config": {
    "confidence_level": 0.95
  }
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "prediction_id": "pred_101",
    "status": "running",
    "started_at": "2026-05-25T11:05:00Z"
  }
}
```

### 获取预测结果

**请求**:

```http
GET /api/projects/{project_id}/prediction/results/{prediction_id}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "prediction_id": "pred_101",
    "type": "time_series",
    "model": "arima",
    "predictions": [
      {
        "date": "2026-05-26",
        "value": 1500,
        "lower_bound": 1200,
        "upper_bound": 1800
      }
    ],
    "metrics": {
      "mae": 50.5,
      "rmse": 75.2,
      "mape": 0.05
    }
  }
}
```

---

## 决策 API

### 生成决策

**请求**:

```http
POST /api/projects/{project_id}/decision/generate
Content-Type: application/json

{
  "dimensions": ["market", "user_feedback", "competition", "risk"],
  "weights": {
    "market": 0.3,
    "user_feedback": 0.3,
    "competition": 0.2,
    "risk": 0.2
  }
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "decision_id": "dec_202",
    "overall_score": 0.75,
    "dimensions": {
      "market": {
        "score": 0.8,
        "reliability": 0.7,
        "evidence": [
          {
            "type": "simulation",
            "run_id": "sim_789",
            "metric": "purchase_intention",
            "value": 0.65
          }
        ]
      }
    },
    "recommendations": [
      "建议加大营销投入",
      "关注负面舆情风险"
    ],
    "generated_at": "2026-05-25T11:10:00Z"
  }
}
```

### 获取决策详情

**请求**:

```http
GET /api/projects/{project_id}/decision/{decision_id}
```

**响应**: 同上

---

## 报告 API

### 生成报告

**请求**:

```http
POST /api/projects/{project_id}/report/generate
Content-Type: application/json

{
  "format": "html",
  "sections": [
    "executive_summary",
    "data_collection",
    "simulation_results",
    "prediction_trends",
    "decision_recommendations"
  ]
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "report_id": "rep_303",
    "status": "generating",
    "started_at": "2026-05-25T11:15:00Z"
  }
}
```

### 获取报告状态

**请求**:

```http
GET /api/projects/{project_id}/report/status/{report_id}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "report_id": "rep_303",
    "status": "completed",
    "format": "html",
    "size": 2048000,
    "generated_at": "2026-05-25T11:20:00Z"
  }
}
```

### 下载报告

**请求**:

```http
GET /api/projects/{project_id}/report/download/{report_id}
```

**响应**: 文件流（HTML/PDF/Markdown）

---

## 系统 API

### 获取系统状态

**请求**:

```http
GET /api/system/health
```

**响应**:

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "2.0.0-rc1",
    "uptime": 3600,
    "services": {
      "database": "healthy",
      "graph": "healthy",
      "llm": "healthy"
    }
  }
}
```

### 获取系统配置

**请求**:

```http
GET /api/system/config
```

**响应**:

```json
{
  "success": true,
  "data": {
    "max_upload_size": 10485760,
    "supported_platforms": ["jd", "taobao", "weibo", "xiaohongshu"],
    "supported_models": ["arima", "prophet", "dowhy"],
    "max_agents": 100000,
    "max_rounds": 1000
  }
}
```

---

## 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| `PROJECT_NOT_FOUND` | 404 | 项目不存在 |
| `DOCUMENT_NOT_FOUND` | 404 | 文档不存在 |
| `INVALID_FILE_FORMAT` | 400 | 不支持的文件格式 |
| `FILE_TOO_LARGE` | 400 | 文件过大 |
| `CRAWLER_FAILED` | 500 | 数据采集失败 |
| `GRAPH_BUILD_FAILED` | 500 | 图谱构建失败 |
| `SIMULATION_FAILED` | 500 | 仿真运行失败 |
| `PREDICTION_FAILED` | 500 | 预测失败 |
| `REPORT_GENERATION_FAILED` | 500 | 报告生成失败 |
| `INVALID_PARAMETERS` | 400 | 参数错误 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `INTERNAL_ERROR` | 500 | 内部错误 |

---

## 速率限制

当前版本暂无速率限制。未来版本将实施以下限制：

- **标准用户**: 100 请求/分钟
- **高级用户**: 1000 请求/分钟

超出限制将返回 `429 Too Many Requests`。

---

## 示例代码

### Python

```python
import requests

BASE_URL = "http://localhost:5001/api"

# 创建项目
response = requests.post(
    f"{BASE_URL}/projects",
    json={
        "name": "iPhone 15 舆情分析",
        "description": "分析 iPhone 15 在社交媒体上的舆情表现"
    }
)
project = response.json()["data"]
project_id = project["project_id"]

# 上传文件
with open("product_intro.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/projects/{project_id}/documents",
        files={"file": f}
    )
document = response.json()["data"]

# 启动数据采集
response = requests.post(
    f"{BASE_URL}/projects/{project_id}/crawler/start",
    json={
        "platforms": ["jd", "weibo"],
        "keywords": ["iPhone 15"],
        "max_items": 500
    }
)
task = response.json()["data"]
```

### JavaScript

```javascript
const BASE_URL = "http://localhost:5001/api";

// 创建项目
const createProject = async () => {
  const response = await fetch(`${BASE_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "iPhone 15 舆情分析",
      description: "分析 iPhone 15 在社交媒体上的舆情表现"
    })
  });
  const { data } = await response.json();
  return data.project_id;
};

// 上传文件
const uploadDocument = async (projectId, file) => {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(
    `${BASE_URL}/projects/${projectId}/documents`,
    {
      method: "POST",
      body: formData
    }
  );
  return await response.json();
};
```

---

## 更新日志

### 2.0.0-rc1 (2026-05-25)
- 初始 API 文档发布
- 支持完整的项目管理、数据采集、仿真、预测、决策、报告生成工作流

---

**版权所有 © 2026 EchoLens Team**  
**许可证**: AGPL-3.0
