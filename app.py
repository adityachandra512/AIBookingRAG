import streamlit as st
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from models.llm import get_gemini_llm
from models.embeddings import get_gemini_embeddings
from utils.rag_pipeline import ingest_pdfs, answer_query_with_rag, find_doctor_suggestions
from utils.booking_flow import BookingFlow
from db.supabase_client import get_all_bookings, create_user, authenticate_user
from tools.email_tool import send_booking_email
from streamlit_option_menu import option_menu

def is_booking_intent(message: str) -> bool:
    booking_keywords = [
        "book", "appointment", "reserve", "reservation", "register", "schedule", "meeting", "slot"
    ]
    return any(word in message.lower() for word in booking_keywords)

def is_doctor_search_intent(message: str) -> bool:
    doctor_keywords = ["doctor", "physician", "specialist", "find", "suggest", "recommend", "search"]
    return any(word in message.lower() for word in doctor_keywords)

def show_chat_page():
    st.markdown("<h1 class='main-header'>🤖 AI Booking Assistant</h1>", unsafe_allow_html=True)
    
    if "booking_flow" not in st.session_state or not isinstance(st.session_state.booking_flow, BookingFlow):
        st.session_state.booking_flow = BookingFlow()
    booking_flow = st.session_state.booking_flow

    # PDF upload integrated into chat
    with st.expander("Upload PDFs for RAG (optional)"):
        uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True, key="chat_pdf")
        if uploaded_files:
            try:
                ingest_pdfs(uploaded_files)
                st.success("PDFs processed for this session.")
            except Exception as e:
                st.error(f"Failed to process PDFs: {e}")

    # display previous messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages[-25:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input
    prompt = st.chat_input("Type your message here...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # If booking intent detected and not already in booking flow, ask for confirmation
        if is_booking_intent(prompt) and not booking_flow.active and not st.session_state.get("booking_intent_asked"):
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown("Do you want to book an appointment? (yes/no)")
            st.session_state.messages.append({"role": "assistant", "content": "Do you want to book an appointment? (yes/no)"})
            st.session_state.booking_intent_asked = True
            st.rerun()

        # If user replies "yes" to booking intent, start booking flow
        if prompt.strip().lower() in ["yes", "y"] and st.session_state.get("booking_intent_asked") and not booking_flow.active:
            # Check if we have a suggested doctor to prefill
            doctor_info = st.session_state.get("last_suggested_doctor")
            booking_flow.start_booking(doctor_info=doctor_info)
            
            st.session_state.booking_intent_asked = False
            resp, ready, data = booking_flow.handle_message("", st.session_state.messages)
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            st.rerun()

        # If booking flow active, route input to booking flow (no RAG)
        if booking_flow.active:
            resp, ready, data = booking_flow.handle_message(prompt, st.session_state.messages)
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})

            if ready and data:
                try:
                    booking_id = booking_flow.save_booking(data)
                except Exception as e:
                    st.error(f"Failed to save booking: {e}")
                    booking_flow.reset()
                    st.session_state.messages = []
                    st.rerun()
                email_sent = send_booking_email(data["email"], booking_id, data)
                if email_sent:
                    st.success(f"Thank you! Your booking is confirmed and will be sent to your email. Booking ID: {booking_id}")
                else:
                    st.warning(f"Booking saved, but email could not be sent. Booking ID: {booking_id}")
                st.session_state.booking_flow = BookingFlow()
                st.session_state.messages = []
                st.rerun()
            elif resp.lower().startswith("booking cancelled"):
                st.session_state.booking_flow = BookingFlow()
                st.session_state.messages = []
                st.rerun()

        # Only run general Q&A when booking flow is NOT active
        if not booking_flow.active and not st.session_state.get("booking_intent_asked"):
            # Check if it's a doctor search
            if is_doctor_search_intent(prompt):
                doctors = find_doctor_suggestions(prompt)
                if doctors:
                    st.session_state.last_suggested_doctor = doctors[0]
                    answer = f"I found some doctors for you. Here is the best match: **{doctors[0].get('name')}** ({doctors[0].get('specialization')}). Would you like to book an appointment with them?"
                else:
                    answer = "I couldn't find any doctors matching your request in the documents."
            else:
                answer = answer_query_with_rag(prompt)
            
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(answer or "Not found in documents.")
            st.session_state.messages.append({"role": "assistant", "content": answer})

def show_login_page():
    st.markdown("<h1 class='main-header'>Admin Access</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                user = authenticate_user(email, password)
                if user:
                    st.session_state.user = {"email": user["email"], "is_admin": user.get("is_admin", False)}
                    st.success("Logged in successfully!")
                    if st.session_state.user["is_admin"]:
                        st.rerun()
                else:
                    st.error("Invalid credentials")

def show_admin_page():
    if not st.session_state.user or not st.session_state.user.get("is_admin"):
        st.error("Admin access required.")
        return

    st.markdown("<h1 class='main-header'>Admin Dashboard - Bookings</h1>", unsafe_allow_html=True)
    bookings = get_all_bookings()
    if bookings:
        st.dataframe(bookings, use_container_width=True)
    else:
        st.info("No bookings found.")

def main():
    st.set_page_config(page_title="AI Booking Assistant", page_icon="🤖", layout="wide")

    # Custom CSS for a premium look
    st.markdown("""
        <style>
        .stApp {
            background-color: #0d1117;
            color: #c9d1d9;
        }
        [data-testid="stSidebar"] {
            background-color: #161b22;
            border-right: 1px solid #30363d;
        }
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 2rem;
            background: linear-gradient(90deg, #58a6ff 0%, #1f6feb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        div.stButton > button {
            background-color: #238636;
            color: white;
            border-radius: 6px;
            border: 1px solid rgba(240,246,252,0.1);
            padding: 0.5rem 1.2rem;
            font-weight: 600;
            transition: 0.2s;
        }
        div.stButton > button:hover {
            background-color: #2ea043;
            border-color: #8b949e;
        }
        .stDataFrame {
            border: 1px solid #30363d;
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    if "user" not in st.session_state:
        st.session_state.user = None

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #58a6ff; margin-bottom: 2rem;'>ASSISTANT</h2>", unsafe_allow_html=True)
        
        if st.session_state.user:
            email = st.session_state.user["email"]
            is_admin = st.session_state.user["is_admin"]
            st.markdown(f"<div style='padding: 1rem; background: #21262d; border-radius: 8px; margin-bottom: 1rem; border: 1px solid #30363d;'>"
                        f"<p style='margin:0; font-size: 0.8rem; color: #8b949e;'>Logged in as</p>"
                        f"<p style='margin:0; font-weight: 600; color: #58a6ff;'>{email}</p>"
                        f"</div>", unsafe_allow_html=True)
            
            nav_items = ["Chat", "Logout"]
            nav_icons = ["chat-dots", "box-arrow-right"]
            
            if is_admin:
                nav_items.insert(1, "Admin Dashboard")
                nav_icons.insert(1, "database-fill")
            
            selected = option_menu(
                None, nav_items, 
                icons=nav_icons, 
                menu_icon="cast", default_index=0,
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": "#8b949e", "font-size": "18px"}, 
                    "nav-link": {"font-size": "15px", "text-align": "left", "margin":"4px 0px", "color": "#c9d1d9", "border-radius": "6px"},
                    "nav-link-selected": {"background-color": "#21262d", "color": "#58a6ff", "font-weight": "600"},
                }
            )
        else:
            selected = option_menu(
                None, ["Chat", "Admin Login"], 
                icons=["chat-dots", "person-badge"], 
                menu_icon="cast", default_index=0,
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": "#8b949e", "font-size": "18px"}, 
                    "nav-link": {"font-size": "15px", "text-align": "left", "margin":"4px 0px", "color": "#c9d1d9", "border-radius": "6px"},
                    "nav-link-selected": {"background-color": "#21262d", "color": "#58a6ff", "font-weight": "600"},
                }
            )

    if selected == "Logout":
        st.session_state.user = None
        st.rerun()

    if selected == "Chat":
        show_chat_page()
    elif selected == "Admin Login":
        show_login_page()
    elif selected == "Admin Dashboard":
        show_admin_page()

if __name__ == "__main__":
    main()
