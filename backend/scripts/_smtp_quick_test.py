import smtplib
from email.message import EmailMessage

# ✅ Replace with your Gmail + App Password
EMAIL_ADDRESS = "pradeepmuthuselvan08@gmail.com"
APP_PASSWORD = "gnsxioqranhspohm"  # remove any spaces

# Create the email
msg = EmailMessage()
msg['Subject'] = 'SMTP Test — Fix Applied'
msg['From'] = EMAIL_ADDRESS
msg['To'] = EMAIL_ADDRESS
msg.set_content('Hello! This is a test email to confirm SMTP delivery works properly.')

# Send email via Gmail SMTP
try:
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()              # Enable TLS
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)
    print("✅ Email sent successfully — check inbox (or spam).")
except Exception as e:
    print(f"❌ Email failed: {e}")
