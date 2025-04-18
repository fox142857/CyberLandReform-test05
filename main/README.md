# 文件哈希读取API

这是一个基于FastAPI实现的文件哈希计算服务，提供以下功能：

- 计算上传文件的哈希值
- 批量计算多个上传文件的哈希值
- 异步批量处理上传文件的哈希计算
- 验证上传文件的哈希值是否与预期值匹配
- 计算服务器上指定路径文件的哈希值
- 批量计算目录中文件的哈希值
- 获取支持的哈希算法列表

## 安装

```bash
pip install -r requirements.txt
```

## 运行服务

```bash
python file_hash_api_server.py
```

服务默认会在 http://0.0.0.0:8000 上启动。

## API端点

### 基础信息
- `GET /api/v1/hash`: 欢迎信息
- `GET /api/v1/hash/algorithms`: 获取支持的哈希算法列表

### 单文件处理
- `POST /api/v1/hash/file`: 计算上传文件的哈希值

### 批量文件处理
- `POST /api/v1/hash/files`: 批量计算多个上传文件的哈希值
- `POST /api/v1/hash/verify`: 验证上传文件的哈希值是否与预期值匹配
- `POST /api/v1/hash/upload/batch`: 异步批量处理上传文件并计算哈希值
- `GET /api/v1/hash/upload/batch/{task_id}`: 获取上传文件批处理任务的状态
- `GET /api/v1/hash/upload/batch/{task_id}/results`: 获取上传文件批处理任务的结果

### 服务器文件处理
- `POST /api/v1/hash/path`: 计算指定路径文件的哈希值
- `POST /api/v1/hash/batch`: 异步处理目录中的文件
- `GET /api/v1/hash/batch/{task_id}`: 获取批处理任务的状态
- `GET /api/v1/hash/batch/{task_id}/results`: 获取批处理任务的结果

## API文档

服务运行后，可以访问以下URL查看API文档：

- **Swagger UI**: http://localhost:8000/docs
  - 提供交互式API文档，可以直接在浏览器中测试API
  - 包含所有API端点的详细说明、参数定义、请求示例和响应格式
  - 按功能分类组织API端点，方便查找

- **ReDoc**: http://localhost:8000/redoc
  - 提供更美观、易读的API文档
  - 支持搜索功能，快速定位API信息
  - 提供完整的API模型定义和示例

## 使用示例

### 计算单个文件哈希

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/hash/file' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@example.txt' \
  -F 'algorithm=sha256'
```

### 批量计算哈希

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/hash/files' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@file1.txt' \
  -F 'files=@file2.txt' \
  -F 'algorithm=sha256'
```

### 验证文件哈希

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/hash/verify' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@example.txt' \
  -F 'expected_hashes=[{"file_name":"example.txt","expected_hash":"a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"}]' \
  -F 'algorithm=sha256'
``` 