# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, time
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dspy import ChainOfThought, Predict
import time as time_module
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# Page config
st.set_page_config(
    page_title="Remind Me!",
    page_icon="⏰",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
    }
    .big-title {
        font-size: 3rem !important;
        font-weight: 700 !important;
        margin-bottom: 2rem !important;
        color: #FF6B6B !important;
        text-align: center !important;
    }
    .subtitle {
        font-size: 1.2rem !important;
        color: #666 !important;
        text-align: center !important;
        margin-bottom: 2rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session states
if 'job_running' not in st.session_state:
    st.session_state.job_running = False
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

# Database functions
def get_db_connection():
    try:
        conn = psycopg2.connect(
            st.secrets["POSTGRES_URL"],
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        # Create users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                reminder_time TIME NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        return False
    finally:
        conn.close()

def add_user(name, email, reminder_time):
    conn = get_db_connection()
    if not conn:
        return False, "Database connection error"
    
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO users (name, email, reminder_time)
            VALUES (%s, %s, %s)
            ''',
            (name, email, reminder_time.strftime('%H:%M'))
        )
        conn.commit()
        return True, None
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False, "This email is already registered!"
    except Exception as e:
        conn.rollback()
        return False, f"Error adding user: {str(e)}"
    finally:
        conn.close()

def get_users():
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        query = '''
            SELECT name, email, 
                   reminder_time::TEXT, 
                   active, 
                   created_at::TEXT
            FROM users
            ORDER BY created_at DESC
        '''
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error fetching users: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def toggle_user_status(email, active):
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute(
            'UPDATE users SET active = %s WHERE email = %s',
            (active, email)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error toggling user status: {str(e)}")
        return False
    finally:
        conn.close()

# Admin authentication
def check_admin_password():
    admin_password = st.secrets.get("ADMIN_PASSWORD")
    if admin_password is None:
        st.error("Admin password not configured in secrets!")
        return False
    
    entered_password = st.sidebar.text_input("Admin Password", type="password")
    if entered_password:
        if entered_password == admin_password:
            st.session_state.admin_authenticated = True
            return True
        else:
            st.sidebar.error("Incorrect password!")
            st.session_state.admin_authenticated = False
            return False
    return False

# Email and Gemini setup
@st.cache_resource
def init_clients():
    try:
        # Gemini setup
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-pro')
        return True, model
    except Exception as e:
        st.error(f"Error initializing Gemini: {str(e)}")
        return False, None

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["GMAIL_SENDER"]
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(st.secrets["GMAIL_SENDER"], st.secrets["GMAIL_APP_PASSWORD"])
        server.send_message(msg)
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)

def send_test_email(email, name, reminder_time):
    subject = "Welcome to Remind Me! 🎉"
    body = (
        f"Hi {name}!\n\n"
        f"Welcome to Remind Me! You're all set to receive daily reminders "
        f"at {reminder_time.strftime('%I:%M %p')}.\n\n"
        f"We'll send you a unique haiku each day to make taking your pill more fun!\n\n"
        f"Stay amazing! ✨\n"
        f"- The Remind Me! Team"
    )
    
    success, error = send_email(email, subject, body)
    return success, error

# Rest of the code remains the same...
# (main function and Haiku generator class remain unchanged)

if __name__ == "__main__":
    main()