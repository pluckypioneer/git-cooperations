# 企业微信健康管理机器人

这是一个基于FastAPI的企业微信健康管理机器人系统，提供健康食谱推荐、体重记录和定时提醒等功能。

## 功能特点

- 企业微信机器人集成
- 健康食谱推荐
- 体重/BMI数据记录
- 定时健康提醒
- JWT认证
- MongoDB数据存储

## 安装要求

- Python 3.8+
- MongoDB
- 企业微信开发者账号

## 安装步骤

1. 克隆项目
```bash
git clone [项目地址]
cd [项目目录]
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
复制 `.env.example` 到 `.env` 并填写相关配置：
```
CORP_ID=your_corp_id
AGENT_ID=your_agent_id
SECRET=your_secret
TOKEN=your_token
ENCODING_AES_KEY=your_encoding_aes_key
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=health_bot
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

4. 启动服务
```bash
uvicorn app.main:app --reload
```

## API文档

启动服务后访问 `http://localhost:8000/docs` 查看完整的API文档。

### 主要API端点

- POST /wechat/webhook: 企业微信机器人消息入口
- POST /api/recipes: 生成健康食谱
- POST /api/health-data: 记录健康数据
- GET /api/reminders: 触发定时提醒

## 企业微信机器人使用说明

1. 在群聊中@机器人并发送指令：
```
@健康助手 食谱 食材:鸡胸肉,菠菜 排除:高糖
```

2. 机器人将返回符合要求的健康食谱推荐。

## 安全说明

- 所有API请求都需要JWT认证
- 敏感数据使用加密存储
- 实现了请求频率限制
- 企业微信消息签名验证

## 贡献指南

欢迎提交Issue和Pull Request。

## 许可证

MIT License 