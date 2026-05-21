# SimTrade 外贸模拟实训平台

面向高校国际贸易专业的模拟实训系统。

## 技术栈

- Django 3.2 LTS
- Python 3.8+
- PostgreSQL 12+
- Bootstrap 3 (兼容 IE8+)

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
pytest
```

## 代码规范

```bash
# 格式化
black .

# 检查
flake8
```
