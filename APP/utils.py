from Crypto.Cipher import AES
import base64
import hashlib
import hmac
import time
import json
from typing import Dict, Any

def encrypt_data(data: Dict[str, Any], key: str) -> str:
    """加密数据"""
    key = key.encode('utf-8')
    data = json.dumps(data).encode('utf-8')
    
    # 使用PKCS7填充
    pad = lambda s: s + (16 - len(s) % 16) * chr(16 - len(s) % 16)
    data = pad(data.decode('utf-8')).encode('utf-8')
    
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    encrypted = cipher.encrypt(data)
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_data(encrypted_data: str, key: str) -> Dict[str, Any]:
    """解密数据"""
    key = key.encode('utf-8')
    encrypted = base64.b64decode(encrypted_data)
    
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    decrypted = cipher.decrypt(encrypted)
    
    # 去除PKCS7填充
    unpad = lambda s: s[:-ord(s[len(s)-1:])]
    decrypted = unpad(decrypted).decode('utf-8')
    
    return json.loads(decrypted)

def verify_signature(token: str, timestamp: str, nonce: str, signature: str) -> bool:
    """验证企业微信消息签名"""
    items = [token, timestamp, nonce]
    items.sort()
    message = ''.join(items)
    
    # 计算签名
    hash_obj = hashlib.sha1()
    hash_obj.update(message.encode('utf-8'))
    calculated_signature = hash_obj.hexdigest()
    
    return calculated_signature == signature

def generate_jwt_token(user_id: str, secret_key: str, algorithm: str = "HS256", expires_delta: int = 30) -> str:
    """生成JWT令牌"""
    from jose import jwt
    
    expire = time.time() + expires_delta * 60
    to_encode = {
        "sub": user_id,
        "exp": expire
    }
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)

def calculate_bmi(weight: float, height: float) -> float:
    """计算BMI指数"""
    height_m = height / 100  # 转换为米
    return weight / (height_m * height_m)

def format_recipe_message(recipe: Dict[str, Any]) -> str:
    """格式化食谱消息"""
    return f"""
健康食谱推荐：{recipe['title']}

食材：
{', '.join(recipe['ingredients'])}

烹饪步骤：
{recipe['instructions']}

营养信息：
- 热量：{recipe.get('calories', 'N/A')} 卡路里
- 蛋白质：{recipe.get('protein', 'N/A')} 克
- 碳水化合物：{recipe.get('carbs', 'N/A')} 克
- 脂肪：{recipe.get('fat', 'N/A')} 克
""" 