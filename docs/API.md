# SimTrade API 文档

## 基础信息

- 基础路径：`/api/v1/`
- 认证方式：Session Authentication
- 响应格式：JSON

## 响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {...}
}
```

### 错误响应

```json
{
  "code": 1001,
  "message": "错误描述",
  "errors": {...}
}
```

## 认证接口

### 用户登录

**请求**
```
POST /api/v1/auth/login/
Content-Type: application/json

{
  "username": "testuser",
  "password": "password123"
}
```

**响应**
```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "user_type": "student"
  }
}
```

### 用户登出

**请求**
```
POST /api/v1/auth/logout/
```

**响应**
```json
{
  "code": 0,
  "message": "登出成功"
}
```

### 获取当前用户

**请求**
```
GET /api/v1/auth/me/
Authorization: Session cookie
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "user_type": "student"
  }
}
```

## 错误码

| 错误码 | 分类 | 说明 |
|--------|------|------|
| 0 | 成功 | 请求成功 |
| 1000 | 通用 | 未知错误 |
| 1001 | 认证 | 用户不存在 |
| 1002 | 认证 | 密码错误 |
| 1003 | 认证 | Token 无效 |
| 1004 | 认证 | Token 过期 |
| 1005 | 认证 | 未登录 |
| 2001 | 权限 | 无权限访问 |
| 2002 | 权限 | 资源不属于当前用户 |
| 3001 | 参数 | 参数缺失 |
| 3002 | 参数 | 参数格式错误 |
| 3003 | 参数 | 参数值无效 |
| 4001 | 资源 | 资源不存在 |
| 4002 | 资源 | 资源已存在 |
| 4003 | 资源 | 资源已被删除 |
| 4004 | 资源 | 资源状态不允许此操作 |
| 5001 | 业务 | 业务规则校验失败 |
| 5002 | 业务 | 单证校验不通过 |
| 5003 | 业务 | 余额不足 |
| 5004 | 业务 | 库存不足 |
| 5005 | 业务 | 交易状态不允许此操作 |
| 6001 | 系统 | 系统繁忙 |
| 6002 | 系统 | 服务维护中 |
| 9999 | 系统 | 内部错误 |
