from pydantic import BaseModel

class Register(BaseModel):
    username: str
    password: str
    email: str
    verify_code: str

class Login(BaseModel):
    username: str
    password: str

class RePassword(BaseModel):
    email: str
    password: str
    verify_code: str

class GoogleToken(BaseModel):
    token: str

class Question(BaseModel):
    human: str

class Admin(BaseModel):
    human: str
    mode: str

class Report(BaseModel):
    user_id: str
    timestamp: str
    title: str
    description: str
    status: int

class PromptUpdate(BaseModel):
    prompt_template: str

class PromptUpdateJV(BaseModel):
    prompt_template_just_venting: str

class PromptUpdateTS(BaseModel):
    prompt_template_test: str

class PromptUpdateJVTS(BaseModel):
    prompt_template_just_venting_test: str