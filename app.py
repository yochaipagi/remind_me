# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, time
import google.generativeai as genai
from twilio.rest import Client
import sqlite3
import os
from dspy import ChainOfThought, Predict
import time as time_module

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

# Initialize session state for background job
if 'job_running' not in st.session_state:
    st.session_state.job_running = False

# Database functions
def init_db():
    conn = sqlite3.connect('remind_me.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            reminder_time TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_user(name, phone, reminder_time):
    conn = sqlite3.connect('remind_me.db')
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO users (name, phone, reminder_time) VALUES (?, ?, ?)',
            (name, phone, reminder_time.strftime('%H:%M'))
        )
        conn.commit()
        success = True
        error = None
    except sqlite3.IntegrityError:
        success = False
        error = "This phone number is already registered!"
    finally:
        conn.close()
    return success, error

def get_users():
    conn = sqlite3.connect('remind_me.db')
    users = pd.read_sql_query(
        'SELECT name, phone, reminder_time, active, created_at FROM users',
        conn
    )
    conn.close()
    return users

def toggle_user_status(phone, active):
    conn = sqlite3.connect('remind_me.db')
    c = conn.cursor()
    c.execute('UPDATE users SET active = ? WHERE phone = ?', (active, phone))
    conn.commit()
    conn.close()

# Twilio and Gemini setup
@st.cache_resource
def init_clients():
    # Twilio setup
    twilio_client = Client(
        st.secrets["TWILIO_ACCOUNT_SID"],
        st.secrets["TWILIO_AUTH_TOKEN"]
    )
    
    # Gemini setup
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
    
    return twilio_client, model

# Haiku Generator
class HaikuGenerator(ChainOfThought):
    def __init__(self):
        super().__init__()
        self.prompt = Predict(
            'Generate a funny and encouraging haiku about taking birth control pills. ' +
            'Make it personal using the name {name}.'
        )

# Send reminder function
def send_reminder(twilio_client, model, user):
    try:
        # Generate haiku
        haiku_generator = HaikuGenerator()
        haiku_prompt = haiku_generator.prompt(name=user['name'])
        haiku = model.generate_text(haiku_prompt)
        
        # Create message
        message = (f"Hi {user['name']}! ✨ Remind Me! here.\n\n"
                  f"Time for your pill! 💊\n\n"
                  f"Your daily haiku:\n{haiku}\n\n"
                  f"Stay amazing! 🌟")
        
        # Send WhatsApp message
        twilio_client.messages.create(
            from_=f"whatsapp:{st.secrets['TWILIO_WHATSAPP_NUMBER']}",
            body=message,
            to=f"whatsapp:{user['phone']}"
        )
        return True, None
    except Exception as e:
        return False, str(e)

# Background job for sending reminders
def reminder_job():
    twilio_client, model = init_clients()
    while st.session_state.job_running:
        current_time = datetime.now().strftime('%H:%M')
        
        conn = sqlite3.connect('remind_me.db')
        users = pd.read_sql_query(
            'SELECT * FROM users WHERE reminder_time = ? AND active = 1',
            conn,
            params=(current_time,)
        )
        conn.close()
        
        for _, user in users.iterrows():
            send_reminder(twilio_client, model, user)
        
        time_module.sleep(60)

# Main app
def main():
    # App title and description
    st.markdown('<h1 class="big-title">Remind Me! ⏰</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Your personal birth control pill reminder assistant, '
        'delivering daily reminders with a touch of poetry ✨</p>',
        unsafe_allow_html=True
    )
    
    # Initialize database
    init_db()
    
    # Initialize clients
    twilio_client, model = init_clients()
    
    # Tabs with emojis
    tab1, tab2, tab3 = st.tabs(["✍️ Registration", "👥 Manage Users", "⚙️ Service Status"])
    
    # Registration Tab
    with tab1:
        st.header("Join Remind Me!")
        with st.form("registration_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Your Name")
            with col2:
                phone = st.text_input("WhatsApp Number (e.g., +1234567890)")
            
            reminder_time = st.time_input(
                "When should we remind you?",
                value=time(9, 0)
            )
            
            submitted = st.form_submit_button("Sign Up! 🎉")
            
            if submitted:
                if name and phone:
                    success, error = add_user(name, phone, reminder_time)
                    if success:
                        st.success("Welcome to Remind Me! 🎉")
                        test_message = (
                            f"Hi {name}! Welcome to Remind Me! 🎉\n\n"
                            f"You'll receive daily reminders at "
                            f"{reminder_time.strftime('%I:%M %p')}.\n\n"
                            f"Stay amazing! ✨"
                        )
                        try:
                            twilio_client.messages.create(
                                from_=f"whatsapp:{st.secrets['TWILIO_WHATSAPP_NUMBER']}",
                                body=test_message,
                                to=f"whatsapp:{phone}"
                            )
                            st.info("📱 Check your WhatsApp for a welcome message!")
                        except Exception as e:
                            st.error(f"Error sending welcome message: {str(e)}")
                    else:
                        st.error(error)
                else:
                    st.error("Please fill in all fields!")
    
    # Manage Users Tab
    with tab2:
        st.header("Community Members")
        users = get_users()
        if not users.empty:
            users['reminder_time'] = pd.to_datetime(users['reminder_time'], format='%H:%M').dt.strftime('%I:%M %p')
            
            # Style the dataframe
            st.dataframe(
                users,
                column_config={
                    "name": "Name",
                    "phone": "WhatsApp",
                    "reminder_time": "Reminder Time",
                    "active": "Active",
                    "created_at": "Joined On"
                },
                hide_index=True
            )
            
            # User management
            st.subheader("Manage Reminders")
            for _, user in users.iterrows():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"🤗 {user['name']} ({user['phone']})")
                with col2:
                    button_label = "🔕 Pause" if user['active'] else "🔔 Resume"
                    if st.button(button_label, key=f"toggle_{user['phone']}"):
                        toggle_user_status(user['phone'], not user['active'])
                        st.rerun()
        else:
            st.info("No members yet! Be the first to join! 🎉")
    
    # Service Status Tab
    with tab3:
        st.header("Reminder Service")
        if st.button(
            "🛑 Stop Service" if st.session_state.job_running else "▶️ Start Service",
            use_container_width=True
        ):
            st.session_state.job_running = not st.session_state.job_running
            if st.session_state.job_running:
                st.write("Starting Remind Me! service...")
                reminder_job()
            else:
                st.write("Stopping Remind Me! service...")
        
        status = "🟢 Active" if st.session_state.job_running else "🔴 Inactive"
        st.write("Current Status:", status)

if __name__ == "__main__":
    main()