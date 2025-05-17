import os
import bcrypt
import secrets
import requests

from datetime import datetime
from bson.objectid import ObjectId
from fastapi import FastAPI, HTTPException, Cookie
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database.mongodb import mongo_client
from database.base_model import Register, Login, RePassword, GoogleToken, Question, Admin, Report, PromptUpdate, PromptUpdateJV, PromptUpdateTS, PromptUpdateJVTS
from middleware.send_email import _send_email
from middleware.tokens import create_access_token, decode_access_token
from chatbot import main

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = 1440
VERIFY_TOKEN_EXPIRE_MINUTES = 10
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_URL = os.getenv("CLIENT_URL")
DOMAIN = os.getenv("DOMAIN")

app = FastAPI(description="DPUCARE web chatbot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CLIENT_URL,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_collection = mongo_client(database="dpu_care", collection="user")
section_collection = mongo_client(database="dpu_care", collection="section")
history_collection = mongo_client(database="dpu_care", collection="history")
admin_collection = mongo_client(database="dpu_care", collection="admin_config")
report_collection = mongo_client(database="dpu_care", collection="reports")
checkpoints_collection = mongo_client(database="dpu_care", collection="checkpoints")
checkpoint_writes_collection = mongo_client(database="dpu_care", collection="checkpoint_writes")

def loop_data(data: list):
    """function loop_data
    parameter:
        data: list (require)"""
    
    raw_data = []
    for detail in data:
        raw_object = {}
        for key, value in detail.items():
            raw_object[key] = str(value)
        raw_data.append(raw_object)
    
    return raw_data

def generate_verification_code():
    return str(secrets.randbelow(1000000)).zfill(6)

def verify_google_token(access_token: str):
    try:
        response = requests.get(f'https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={access_token}')

        if response.status_code != 200:
            raise ValueError('Invalid access token or expired token')

        token_info = response.json()
        
        if 'error' in token_info:
            raise ValueError(f"Error verifying token: {token_info['error']}")

        return token_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {e}")
    
# API for Test Connect
@app.get("/test-connect")
async def test_connect():
    return { "msg": "Connect successful" }

# API for Protected
@app.get("/protected")
async def protected(access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    return {"msg": f"{payload['sub']}"}

# API for Get User Data
@app.get("/get-user")
async def get_user(user_id: str = Cookie(None), role: str = Cookie(None), section_id: str = Cookie(None), access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    return {
        "user_id": user_id,
        "section_id": section_id,
        "role": role
        }

# API for Google Sign IN / Sign Up
@app.post("/auth-google")
async def google_login(google_token: GoogleToken):
    user_data = verify_google_token(google_token.token)
    email = user_data['email']
    user_info = user_collection.find_one({"email": email})
    token = create_access_token(data={"sub": email}, minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    ck_user = user_collection.find_one({"email": email})
    
    if ck_user:
        responese = JSONResponse(content={"msg": "Login successful"})
        responese.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            domain=DOMAIN,
            samesite="None",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )
        responese.set_cookie(
            key="user_id",
            value=user_info.get("_id"),
            httponly=True,
            secure=True,
            domain=DOMAIN,
            samesite="None",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )
        responese.set_cookie(
            key="role",
            value=user_info.get("role"),
            httponly=True,
            secure=True,
            domain=DOMAIN,
            samesite="None",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )
        
        return responese
    
    email_sp = email.split("@")
    user_collection.insert_one({
        "username": email_sp[0],
        "email": email,
        "role": "user"
    })
    
    responese = JSONResponse(content={"msg": "Register successful"})
    responese.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        domain=DOMAIN,
        samesite="None",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    return responese

# API for Sendemail
@app.get("/send-email/{email}")
async def send_email(email: str):
    verification_code = generate_verification_code()
    smpt_user = os.getenv("SMTP_USER")
    
    message = f"""สวัสดีค่ะ/ครับ\n\nขอบคุณที่ลงทะเบียนกับเรา!\nเพื่อความปลอดภัยและยืนยันตัวตนของคุณ กรุณากรอกรหัสยืนยันด้านล่างนี้ในหน้าเว็บไซต์:\n\nรหัสยืนยัน: [{verification_code}]\n\nรหัสนี้จะหมดอายุภายใน [{VERIFY_TOKEN_EXPIRE_MINUTES} minutes] หากคุณไม่ได้ทำการสมัครสมาชิกหรือไม่ขอรับรหัสยืนยันนี้ กรุณาติดต่อเราที่ [{os.getenv("SMTP_USER")}].\n\nขอบคุณค่ะ/ครับ\nทีมงาน [DPUCARE]"""
    
    retult = _send_email(
        title="Verify Email",
        from_=smpt_user,
        to_=email,
        content=message
        )
    verify_token = create_access_token(data={"sub": email}, minutes=VERIFY_TOKEN_EXPIRE_MINUTES)
    
    return {
        "msg": retult,
        "verify_tk": verify_token,
        "verification_code": verification_code
    }

# API for Register
@app.post("/register/{verify_tk}/{verification_code}")
async def register(form_data: Register, verify_tk: str, verification_code: str):
    playload = decode_access_token(token=verify_tk)
    
    if (playload == "Invalid token"): return "Invalid token"
    if (playload == "Token expired"): return "Token expired"
    else:
        if (form_data.verify_code == verification_code):
            ck_user = user_collection.find_one({"username": form_data.username})
            check_email = user_collection.find_one({"email": form_data.email})
            
            if ck_user:
                raise HTTPException(status_code=400, detail="user already exists")
            if check_email:
                raise HTTPException(status_code=400, detail="email already exists")
            
            hash_password = bcrypt.hashpw(form_data.password.encode("utf-8"), bcrypt.gensalt())
            
            user_info = user_collection.insert_one({
                "username": form_data.username,
                "password": hash_password.decode("utf-8"),
                "email": form_data.email,
                "role": "user"
            })
            
            token =  create_access_token(data={"sub": form_data.username}, minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            responese = JSONResponse(content={"msg": "Register successful"})
            responese.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=True,
                domain=DOMAIN,
                samesite="None",
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                path="/"
            )
            responese.set_cookie(
                key="user_id",
                value=str(user_info.inserted_id),
                httponly=True,
                secure=True,
                domain=DOMAIN,
                samesite="None",
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                path="/"
            )
            responese.set_cookie(
                key="role",
                value="user",
                httponly=True,
                secure=True,
                domain=DOMAIN,
                samesite="None",
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                path="/"
            )
            
            return responese
        else:
            return "verification_code fail"


# API for Login
@app.post("/login")
async def login(form_data: Login):
    user = user_collection.find_one(
        {"$or": [{"username": form_data.username}, {"email": form_data.username}]}
    )
    
    if not user:
        raise HTTPException(status_code=400, detail="user or email not found")
    if not bcrypt.checkpw(
        form_data.password.encode("utf-8"), user["password"].encode("utf-8")
    ):
        raise HTTPException(status_code=400, detail="password is incorrect")
    
    token =  create_access_token(data={"sub": form_data.username}, minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
    responese = JSONResponse(content={"msg": "Login successful"})
    responese.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        domain=DOMAIN,
        samesite="None",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    responese.set_cookie(
        key="user_id",
        value=str(user.get("_id")),
        httponly=True,
        secure=True,
        domain=DOMAIN,
        samesite="None",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    responese.set_cookie(
        key="role",
        value=str(user.get("role")),
        httponly=True,
        secure=True,
        domain=DOMAIN,
        samesite="None",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    return responese

# API for Forgot Password
@app.put("/forgot-password/{verify_tk}/{verification_code}")
async def forgot_password(form_data: RePassword, verify_tk: str, verification_code: str):
    playload = decode_access_token(token=verify_tk)
    if (playload == "Invalid token"): return "Invalid token"
    if (playload == "Token expired"): return "Token expired"
    else:
        user_info = user_collection.find_one({"email": form_data.email})
        if not user_info:
            raise HTTPException(status_code=400, detail="no found email")
        
        if (form_data.verify_code == verification_code):
            hash_password = bcrypt.hashpw(form_data.password.encode("utf-8"), bcrypt.gensalt())
            user_collection.update_one({"email": form_data.email}, {"$set": {"password": hash_password.decode("utf-8")}})
            
            return {
                "msg": "Update password success"
            }
        else:
            return "verification_code fail"

# API for Login
@app.get("/logout")
async def logout():
    response = JSONResponse(content={"msg": "Logged out"})
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="user_id")
    response.delete_cookie(key="section_id")
    response.delete_cookie(key="role")
    
    return response

# API for Create Section
@app.post("/section/{user_id}")
async def create_section(user_id: str, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    dt = datetime.now()
    
    data = {
        "user_id": user_id,
        "time": f"{dt.day}-{dt.month}-{dt.year}",
    }
    res = section_collection.insert_one(data)
    
    responese = JSONResponse(content={"msg": "Create section successful"})
    responese.set_cookie(
        key="section_id",
        value=str(res.inserted_id),
        httponly=True,
        secure=True,
        domain=DOMAIN,
        samesite="None",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    return responese

# API for Get Section
@app.get("/section/{user_id}")
async def get_section(user_id: str, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    res = section_collection.find(
        {"user_id": user_id}
    )
    
    result = loop_data(data=res)
    
    return result

# API for Delete Section
@app.delete("/section/{section_id}")
async def delete_section(section_id: str, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    checkpoint_writes_collection.delete_many({"thread_id": section_id})
    checkpoints_collection.delete_many({"thread_id": section_id})
    history_collection.delete_many({"section_id": section_id})
    section_collection.delete_one({"_id": ObjectId(section_id)})
    
    return {
        "msg": "delete section successful"
    }

# API for Delete Section (non user)
@app.delete("/section-non-user/{section_id}")
async def delete_section(section_id: str):
    
    checkpoint_writes_collection.delete_many({"thread_id": section_id})
    checkpoints_collection.delete_many({"thread_id": section_id})
    
    return {
        "msg": "delete section non-user successful"
    }

# API for Create History (Main Chatbot)
@app.post("/main-chatbot/{section_id}")
async def create_history(section_id: str, question: Question, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    chatbot_info = admin_collection.find({})
    res_info = loop_data(chatbot_info)
    
    llm = main(
        model_name="gpt-4o",
        system_template=res_info[0]["prompt_template"],
        text=question.human,
        thread_id=section_id
    )
    
    new_data = {
        "section_id": section_id,
        "question": question.human,
        "answer": llm["response"]
    }
    
    update_tokens = {
        "total_tokens" : int(res_info[0]["total_tokens"]) + int(llm["total_tokens"])
    }
    
    result = history_collection.insert_one(new_data)
    admin_collection.update_one({"_id": ObjectId(res_info[0]["_id"])}, {"$set": update_tokens})
    
    return {
        "msg": "create new history successful",
        "id": str(result.inserted_id),
        "section_id": section_id,
        "question": question.human,
        "answer": llm["response"]
    }

# API for Get History
@app.get("/history/{section_id}")
async def get_history(section_id: str, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    response = history_collection.find({"section_id": section_id})
    
    result = loop_data(data=response)
    
    return result

# API for Chatbot (just_venting)
@app.post("/just-venting-chatbot/{section_id}")
async def chatbot_secondery(section_id: str, question: Question, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    chatbot_info = admin_collection.find({})
    res_info = loop_data(data=chatbot_info)

    llm = main(
        model_name="gpt-4o",
        system_template=res_info[0]["prompt_template_just_venting"],
        text=question.human,
        thread_id=section_id
    )
    
    update_tokens = {
        "total_tokens" : int(res_info[0]["total_tokens"]) + int(llm["total_tokens"])
    }
    
    admin_collection.update_one({"_id": ObjectId(res_info[0]["_id"])}, {"$set": update_tokens})
    
    return {
        "question": question.human,
        "answer": llm["response"]
    }

# API for None-Login Test Chatbot (limit 3 question)
@app.post("/test-chatbot/{section_id}")
async def non_user_create_history(section_id: str, question: Question):
    chatbot_info = admin_collection.find({})
    res_info = loop_data(data=chatbot_info)

    llm = main(
        model_name="gpt-4o-mini",
        system_template=res_info[0]["prompt_template"],
        text=question.human,
        thread_id=section_id
    )
    
    update_tokens = {
        "total_tokens" : int(res_info[0]["total_tokens"]) + int(llm["total_tokens"])
    }
    
    admin_collection.update_one({"_id": ObjectId(res_info[0]["_id"])}, {"$set": update_tokens})
    
    return {
        "question": question.human,
        "answer": llm["response"]
    }

# API for Get Chatbot Config
@app.get("/chatbot-config/{user_id}")
async def get_chatbot_config(user_id: str, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")
    
    chatbot_config = admin_collection.find_one({"user_id": user_id})
    
    return {
        "prompt_template": chatbot_config.get("prompt_template"),
        "prompt_template_just_venting": chatbot_config.get("prompt_template_just_venting"),
        "prompt_template_test": chatbot_config.get("prompt_template_test"),
        "prompt_template_just_venting_test": chatbot_config.get("prompt_template_just_venting_test"),
        "total_tokens": chatbot_config.get("total_tokens")
    }

# API for Create Report
@app.post("/report")
async def create_report(report: Report):
    new_data = {
        "user_id": report.user_id,
        "timestamp": report.timestamp,
        "title": report.title,
        "description": report.description,
        "status": report.status
    }
    
    report_collection.insert_one(new_data)
    
    return {
        "msg": "create report successful"
    }

# API for Get Report
@app.get("/report/{user_id}")
async def get_report(user_id: str, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")
    
    report_info = report_collection.find({})
    res_report = loop_data(report_info)
    
    return res_report

# API for Delete an Report
@app.delete("/report/{user_id}/{report_id}")
async def delete_report(user_id: str, report_id: str, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")
    
    report_collection.delete_one({"_id": ObjectId(report_id)})
    
    return {
        "msg": "delete report successful"
    }


# API for Test Chatbot (Admin)
@app.post("/test-main-chatbot/{user_id}/{section_id}")
async def chatbot_admin(user_id: str, section_id: str, form_data: Admin, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")
    
    chatbot_info = admin_collection.find({})
    res_info = loop_data(data=chatbot_info)

    llm = main(
        model_name="gpt-4o",
        system_template=res_info[0][form_data.mode],
        text=form_data.human,
        thread_id=section_id
    )
    
    update_tokens = {
        "total_tokens" : int(res_info[0]["total_tokens"]) + int(llm["total_tokens"])
    }
    
    admin_collection.update_one({"_id": ObjectId(res_info[0]["_id"])}, {"$set": update_tokens})
    
    return {
        "msg": "create new history successful",
        "question": form_data.human,
        "answer": llm["response"]
    }

# API for Get Count All User
@app.get("/get-count-all-user/{user_id}")
async def get_count_all_user(user_id: str, access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)
    
    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)
    
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")
    
    user_count = user_collection.count_documents({})
    return {
        "msg": "get user count successful",
        "total_user": user_count
    }


#API for Update Prompt Template
@app.put("/update-prompt-template/{user_id}")
async def update_prompt_template(user_id: str, form_data: PromptUpdate,access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)

    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)

    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")

    update_prompt = {
        "prompt_template": form_data.prompt_template
    }

    admin_collection.update_one({"user_id": user_id}, {"$set": update_prompt})

    return {
        "msg": "update prompt template successful"
    }

#API for Update prompt_justventing
@app.put("/update-prompt-justventing/{user_id}")
async def update_prompt_templateJV(user_id: str, form_data: PromptUpdateJV,access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)

    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)

    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")

    update_prompt = {
        "prompt_template_just_venting": form_data.prompt_template_just_venting
    }

    admin_collection.update_one({"user_id": user_id}, {"$set": update_prompt})

    return {
        "msg": "update prompt template successful"
    }

#API for Update rompt_template_test
@app.put("/update-prompt-template-test/{user_id}")
async def prompt_template_test(user_id: str, form_data: PromptUpdateTS,access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)

    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)

    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")

    update_prompt = {
        "prompt_template_test": form_data.prompt_template_test
    }

    admin_collection.update_one({"user_id": user_id}, {"$set": update_prompt})

    return {
        "msg": "update prompt template successful"
    }

#API for Update prompt_justventing_test
@app.put("/update-prompt-justventing-test/{user_id}")
async def update_prompt_templateJVTS(user_id: str, form_data: PromptUpdateJVTS,access_token: str = Cookie(None)):
    payload = decode_access_token(token=access_token)

    if payload in ["Invalid token", "Token expired"]:
        raise HTTPException(status_code=401, detail=payload)

    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied: not an admin")

    update_prompt = {
        "prompt_template_just_venting_test": form_data.prompt_template_just_venting_test
    }

    admin_collection.update_one({"user_id": user_id}, {"$set": update_prompt})

    return {
        "msg": "update prompt template successful"
    }