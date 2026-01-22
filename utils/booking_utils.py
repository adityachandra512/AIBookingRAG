# utils/booking_utils.py
"""
Utility functions for booking logic: find doctor, check slot, manage appointments, etc.
"""
from models.booking import Doctor, Appointment, FAQ
from typing import List, Optional

# Example in-memory data (replace with DB in production)
doctors = [
    Doctor("Dr. Alice Smith", "Cardiology", ["2026-01-22 10:00", "2026-01-22 11:00"]),
    Doctor("Dr. Bob Jones", "Dermatology", ["2026-01-22 12:00", "2026-01-22 13:00"]),
]
appointments: List[Appointment] = []
faqs = [
    FAQ("What are the clinic timings?", "Monday to Saturday, 9 AM to 6 PM."),
    FAQ("Where is the clinic located?", "123 Main St, Cityville."),
]

def find_doctor_by_name(name: str) -> Optional[Doctor]:
    for doc in doctors:
        if name.lower() in doc.name.lower():
            return doc
    return None

def is_slot_available(doctor: Doctor, slot: str) -> bool:
    return slot in doctor.available_slots and all(a.slot != slot or a.doctor_name != doctor.name for a in appointments)

def book_appointment(patient_name: str, doctor_name: str, slot: str, email: str) -> Optional[Appointment]:
    doctor = find_doctor_by_name(doctor_name)
    if doctor and is_slot_available(doctor, slot):
        appt = Appointment(patient_name, doctor.name, slot, email)
        appointments.append(appt)
        return appt
    return None

def cancel_appointment(patient_name: str, doctor_name: str, slot: str) -> bool:
    global appointments
    before = len(appointments)
    appointments = [a for a in appointments if not (a.patient_name == patient_name and a.doctor_name == doctor_name and a.slot == slot)]
    return len(appointments) < before

def get_faq_answer(question: str) -> Optional[str]:
    for faq in faqs:
        if question.lower() in faq.question.lower():
            return faq.answer
    return None
