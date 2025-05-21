import os
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv()


SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def _send_email(title: str, from_: str, to_: str, content: str):
    """function send_email
    parameter:
        title: str (require)
        _from: str (require)
        _to: str (require)
        content: str (require)"""
    
    try: 
        msg = EmailMessage()
        msg["Subject"] = title
        msg["From"] = from_
        msg["To"] = to_
        msg.set_content(content)
        
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smpt:
            smpt.starttls()
            smpt.login(from_, SMTP_PASSWORD)
            smpt.send_message(msg)
        
        return "Send email successful"
    except Exception as e:
        return f"An error occurred: {e}"