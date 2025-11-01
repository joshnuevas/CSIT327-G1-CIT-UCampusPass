import smtplib
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

print(f"Testing with user: {EMAIL_HOST_USER}")  # Mask password for security
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    print("✅ SMTP login successful! Credentials are good.")
    server.quit()
except Exception as e:
    print(f"❌ SMTP error: {e}")
    print("Possible fixes: Regenerate App Password, check 2FA, or try a different email provider.")