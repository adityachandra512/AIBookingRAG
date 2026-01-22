import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in your environment or .env file.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_booking(data):
    # Ensure customer exists or upsert
    customer_payload = {
        "name": data["name"],
        "email": data["email"],
        "phone": data["phone"]
    }
    # Using upsert with on_conflict if supported, else select/insert
    try:
        customer_resp = supabase.table("customers").upsert(customer_payload, on_conflict="email").execute()
        if customer_resp.data:
            customer = customer_resp.data[0]
        else:
            raise RuntimeError("Failed to upsert customer")
    except Exception as e:
        # Fallback if upsert fails or behaves unexpectedly
        sel = supabase.table("customers").select("*").eq("email", data["email"]).execute()
        if sel.data:
            customer = sel.data[0]
        else:
            customer_resp = supabase.table("customers").insert(customer_payload).execute()
            customer = customer_resp.data[0]

    customer_id = customer.get("customer_id")

    booking_payload = {
        "customer_id": customer_id,
        "booking_type": data.get("booking_type", "Doctor Appointment"),
        "date": data.get("date"),
        "time": data.get("time"),
        "status": "confirmed",
        "doctor_name": data.get("doctor_name")
    }
    booking_resp = supabase.table("bookings").insert(booking_payload).execute()
    if not booking_resp.data:
        raise RuntimeError("Failed to insert booking")
    
    booking = booking_resp.data[0]
    return booking["id"]

def get_all_bookings():
    resp = supabase.table("bookings").select("id,customer_id,booking_type,date,time,status,created_at,doctor_name").execute()
    return resp.data

# Simple user functions for signup/login (not secure for production)
def create_user(email, password, is_admin=False):
    try:
        resp = supabase.table("users").upsert({
            "email": email,
            "password": password,
            "is_admin": is_admin
        }, on_conflict="email").execute()
        return resp.data[0] if resp.data else None
    except Exception:
        return None

def authenticate_user(email, password):
    try:
        resp = supabase.table("users").select("email,is_admin").eq("email", email).eq("password", password).single().execute()
        return resp.data
    except Exception:
        return None
