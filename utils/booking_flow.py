from models.llm import get_gemini_llm
from utils.rag_pipeline import answer_query_with_rag, find_doctor_suggestions
from db.supabase_client import save_booking as _save_booking

class BookingFlow:
    REQUIRED_FIELDS = ["name", "email", "phone", "booking_type", "date", "time"]
    TIME_OPTIONS = [
        "09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"
    ]
    BOOKING_TYPE_OPTIONS = [
        "Doctor Appointment"
    ]

    def __init__(self):
        self.data = {}
        self.awaiting_confirmation = False
        self.active = False
        self.doctor_info = None  # holds suggested doctor dict if any

    def start_booking(self, doctor_info=None):
        # initialize booking; if doctor_info provided prefill booking_type and doctor data
        self.data = {}
        self.awaiting_confirmation = False
        self.active = True
        self.doctor_info = doctor_info
        if doctor_info:
            self.data["booking_type"] = "Doctor Appointment"
            # store doctor name for reference
            self.data["doctor_name"] = doctor_info.get("name", "")

    def reset(self):
        self.data = {}
        self.awaiting_confirmation = False
        self.active = False
        self.doctor_info = None

    def handle_message(self, message, history):
        if not self.active:
            return "If you'd like to make a booking say 'I want to book' or 'book an appointment'.", False, None

        # Slot filling: extract fields from message
        for field in self.REQUIRED_FIELDS:
            if field not in self.data:
                # field:value style
                if ":" in message:
                    for part in message.split(","):
                        if ":" in part:
                            k, v = part.split(":",1)
                            if k.strip().lower() == field:
                                self.data[field] = v.strip().strip('"').strip("'")
                # CSV style quick entry
                elif "," in message and all(f in message.lower() for f in ["@", "com"]):
                    parts = [p.strip() for p in message.split(",")]
                    if len(parts) >= 6:
                        self.data["name"] = parts[0]
                        self.data["email"] = parts[1]
                        self.data["phone"] = parts[2]
                        self.data["booking_type"] = parts[3]
                        self.data["date"] = parts[4]
                        self.data["time"] = str(parts[5]).strip().strip('"').strip("'")
                        break
                # single value heuristics
                elif field == "name":
                    if "@" not in message and len(message.split()) <= 4:
                        self.data[field] = message.strip().strip('"').strip("'")
                elif field == "email" and "@" in message:
                    self.data[field] = message.strip().strip('"').strip("'")
                elif field == "phone" and any(ch.isdigit() for ch in message):
                    self.data[field] = message.strip().strip('"').strip("'")
                elif field == "booking_type" and message.strip() in self.BOOKING_TYPE_OPTIONS:
                    self.data[field] = message.strip()
                elif field == "date" and len(message.strip()) == 10 and "-" in message:
                    self.data[field] = message.strip()
                elif field == "time":
                    # Automatically set time to "09:00" (beginning hour) if not already set
                    self.data[field] = "09:00"

        missing = [f for f in self.REQUIRED_FIELDS if f not in self.data]
        if not missing and not self.awaiting_confirmation:
            # ensure time is string
            if "time" in self.data:
                self.data["time"] = str(self.data["time"])
            summary = "\n".join(f"{k.title()}: {v}" for k, v in self.data.items())
            self.awaiting_confirmation = True
            return f"Please confirm your booking details:\n{summary}\nReply 'yes' to confirm or 'no' to cancel.", False, None
        if self.awaiting_confirmation:
            if "yes" in message.lower():
                self.awaiting_confirmation = False
                self.active = False
                return "Thank you! Your booking is confirmed and will be sent to your email.", True, self.data
            elif "no" in message.lower():
                self.reset()
                return "Booking cancelled. Let's start over. Please provide your name.", False, None
            else:
                return "Please reply 'yes' to confirm or 'no' to cancel.", False, None

        if missing:
            next_field = missing[0]
            return get_field_prompt(next_field), False, None

    def save_booking(self, booking_data):
        # wrapper to call DB save and return booking id
        return _save_booking(booking_data)

def get_field_prompt(field):
    if field == "name":
        return "Please provide your name."
    elif field == "email":
        return "Please provide your email address."
    elif field == "phone":
        return "Please provide your phone number."
    elif field == "booking_type":
        options = ", ".join(BookingFlow.BOOKING_TYPE_OPTIONS)
        return f"Please select your booking type from the following options: {options}"
    elif field == "date":
        return "Please provide your preferred date (YYYY-MM-DD)."
    elif field == "time":
        options = ", ".join(BookingFlow.TIME_OPTIONS)
        return f"Please enter your preferred time (e.g., 09:00). Doctor's available times will be used when possible: {options}"
    else:
        return f"Please provide {field.replace('_', ' ')}."
