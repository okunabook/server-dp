import os
import jwt

from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def create_access_token(data: dict, minutes: int):
    """function create_access_token
    parameter:
        data: dict (require)
        min (minutes) : int (require)"""
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=minutes)
        to_encode.update({"exp": expire})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        return token
    except Exception as e:
        return f"An error occurred {e}"

def decode_access_token(token: str):
    """function decode_access_token
    parameter:
        token: str (require)"""
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return "Token expired"
    except jwt.PyJWTError:
        return "Invalid token"
    except Exception as e:
        return f"An error occurred {e}"