# test_email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_gmail_connection(sender_email, app_password, test_receiver_email):
    print(f"\nTesting email configuration...")
    print(f"From: {sender_email}")
    print(f"To: {test_receiver_email}")
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = test_receiver_email
        msg['Subject'] = "Test Email from Remind Me!"
        
        body = """
        Hello!
        
        This is a test email to verify the email configuration is working correctly.
        
        If you received this, the email setup is working! 🎉
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        print("\nConnecting to SMTP server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        
        print("Starting TLS...")
        server.starttls()
        
        print("Logging in...")
        server.login(sender_email, app_password)
        
        print("Sending email...")
        server.send_message(msg)
        
        print("Closing connection...")
        server.quit()
        
        print("\n✅ Success! Email sent successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    # Your Gmail credentials
    SENDER_EMAIL = "yochai.pagi1997@gmail.com"  # Replace with your Gmail
    APP_PASSWORD = "ljow eegi mybw qtzd"  # Replace with your app password
    TEST_RECEIVER_EMAIL = "yochai.pagi1997@gmail.com"  # Replace with test recipient email
    
    test_gmail_connection(SENDER_EMAIL, APP_PASSWORD, TEST_RECEIVER_EMAIL)