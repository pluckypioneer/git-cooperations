from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv
from jose import JWTError, jwt
from pydantic import BaseModel
import json
from Crypto.Cipher import AES
import base64
import xml.etree.ElementTree as ET
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 加载环境变量
load_dotenv()

app = FastAPI(title="健康管理机器人API")

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库连接
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "health_bot")

try:
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
except Exception as e:
    print(f"数据库连接错误: {str(e)}")
    raise

# JWT设置
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# 企业微信配置
CORP_ID = os.getenv("CORP_ID")
AGENT_ID = os.getenv("AGENT_ID")
SECRET = os.getenv("SECRET")
TOKEN = os.getenv("TOKEN")
ENCODING_AES_KEY = os.getenv("ENCODING_AES_KEY")

# 检查必要的配置
if not all([CORP_ID, AGENT_ID, SECRET, TOKEN, ENCODING_AES_KEY]):
    print("警告: 企业微信配置不完整，请检查.env文件")

# 数据模型
class HealthData(BaseModel):
    user_id: str
    weight: float
    height: float
    bmi: float
    timestamp: datetime = datetime.now()

class RecipeRequest(BaseModel):
    include_ingredients: list[str]
    exclude_tags: list[str]

# 企业微信消息解密
def decrypt_message(encrypted_msg: str) -> str:
    key = base64.b64decode(ENCODING_AES_KEY + '=')
    encrypted = base64.b64decode(encrypted_msg)
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    decrypted = cipher.decrypt(encrypted)
    unpad = lambda s: s[:-ord(s[len(s)-1:])]
    return unpad(decrypted[16:]).decode('utf-8')

# JWT认证
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user_id

# 企业微信消息处理
@app.post("/wechat/webhook")
async def wechat_webhook(request: Request):
    body = await request.body()
    xml_data = ET.fromstring(body.decode('utf-8'))
    
    # 验证签名
    msg_signature = request.query_params.get("msg_signature")
    timestamp = request.query_params.get("timestamp")
    nonce = request.query_params.get("nonce")
    
    # 解析消息
    msg_type = xml_data.find("MsgType").text
    if msg_type == "text":
        content = xml_data.find("Content").text
        from_user = xml_data.find("FromUserName").text
        
        # 处理@消息
        if "@健康助手" in content:
            # 解析指令
            command = content.split("@健康助手")[1].strip()
            if command.startswith("食谱"):
                # 解析食材需求
                ingredients = []
                exclude_tags = []
                if "食材:" in command:
                    ingredients = command.split("食材:")[1].split("排除:")[0].strip().split(",")
                if "排除:" in command:
                    exclude_tags = command.split("排除:")[1].strip().split(",")
                
                # 生成食谱
                recipe = await generate_recipe(ingredients, exclude_tags)
                
                # 发送企业微信消息
                await send_wechat_message(from_user, recipe)
    
    return {"status": "success"}

# 食谱生成
async def generate_recipe(include_ingredients: list[str], exclude_tags: list[str]) -> dict:
    # 1. 优先匹配包含指定食材的食谱
    recipes = await db.recipes.find({
        "ingredients": {"$all": include_ingredients},
        "tags": {"$nin": exclude_tags}
    }).to_list(length=1)
    
    if recipes:
        return recipes[0]
    
    # 2. 调用Nutrition API生成新食谱
    # TODO: 实现Nutrition API调用
    return {"title": "示例食谱", "ingredients": include_ingredients, "instructions": "烹饪步骤..."}

# 发送企业微信消息
async def send_wechat_message(user_id: str, content: dict):
    access_token = await get_wechat_access_token()
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    
    data = {
        "touser": user_id,
        "msgtype": "news",
        "agentid": AGENT_ID,
        "news": {
            "articles": [{
                "title": content["title"],
                "description": "健康食谱推荐",
                "url": "https://example.com/recipe",
                "picurl": "https://example.com/recipe.jpg"
            }]
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            return await response.json()

# 获取企业微信访问令牌
async def get_wechat_access_token() -> str:
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={SECRET}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data["access_token"]

# 健康数据记录
@app.post("/api/health-data")
async def record_health_data(data: HealthData, current_user: str = Depends(get_current_user)):
    data.user_id = current_user
    await db.health_data.insert_one(data.dict())
    return {"status": "success"}

# 定时提醒
scheduler = AsyncIOScheduler()

async def send_reminders():
    users = await db.users.find({"reminders_enabled": True}).to_list(length=None)
    for user in users:
        await send_wechat_message(user["user_id"], {
            "title": "健康提醒",
            "content": "该记录今天的健康数据了！"
        })

scheduler.add_job(send_reminders, CronTrigger(hour=9, minute=0))
scheduler.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 