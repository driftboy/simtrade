# SimTrade 外贸模拟实训平台

面向高校国际贸易专业的模拟实训系统。

## 技术栈

- Django 3.2 LTS
- Python 3.8+
- PostgreSQL 12+ / SQLite
- Bootstrap 3 (兼容 IE8+)

## 功能特性

- [x] 用户认证与 RBAC 权限系统
- [x] 核心数据模型（国家、港口、货币）
- [x] 数据初始化命令
- [ ] 交易管理
- [ ] 单证系统
- [ ] 评分系统

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件配置数据库等信息
```

### 数据库迁移

```bash
python manage.py migrate
```

### 初始化数据

```bash
python manage.py init_data
```

### 创建管理员

```bash
python manage.py createsuperuser
```

### 运行开发服务器

```bash
python manage.py runserver
```

访问 http://localhost:8000

## 测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest apps/users/tests/
pytest apps/core/tests/

# 查看覆盖率报告
pytest --cov=apps --cov-report=html
```

## API 文档

详见 [API.md](docs/API.md)

## 项目结构

```
simtrade/
├── apps/
│   ├── users/          # 用户与权限
│   └── core/           # 核心数据
├── templates/          # 模板文件
├── static/             # 静态文件
├── docs/               # 文档
└── simtrade/           # 项目配置
```

## 代码规范

```bash
# 格式化代码
black .

# 检查代码风格
flake8
```

## License

MIT
