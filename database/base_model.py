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

class CreateSection(BaseModel):
    name: str

class CreateTemplate(BaseModel):
    name: str
    template: str

class UpdateTemplate(BaseModel):
    template: str

class SelectMainTemplate(BaseModel):
    select_main: str

class SelectSeconderyTemplate(BaseModel):
    select_secondery: str