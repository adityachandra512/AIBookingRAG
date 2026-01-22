import os
import requests

EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "https://ai-booking-email-sender.vercel.app/booking-confirmation")

def send_booking_email(to_email, booking_id, booking_data):
    payload = {
        "booking_id": booking_id,
        "to": to_email
    }
    try:
        resp = requests.post(EMAIL_SERVICE_URL, json=payload, timeout=10)
        if resp.status_code == 200 and resp.json().get("success"):
            return True
        else:
            print("Email API error:", resp.status_code, resp.text)
            return False
    except Exception as e:
        print("Email API exception:", e)
        return False
