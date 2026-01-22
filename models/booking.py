# models/booking.py
"""
Data models for doctors, appointments, and FAQs for the AI Booking Assistant.
"""
from datetime import datetime
from typing import List, Optional

class Doctor:
    def __init__(self, name: str, specialization: str, available_slots: List[str]):
        self.name = name
        self.specialization = specialization
        self.available_slots = available_slots  # e.g., ["2026-01-22 10:00", ...]

class Appointment:
    def __init__(self, patient_name: str, doctor_name: str, slot: str, email: str):
        self.patient_name = patient_name
        self.doctor_name = doctor_name
        self.slot = slot  # e.g., "2026-01-22 10:00"
        self.email = email
        self.created_at = datetime.now()

class FAQ:
    def __init__(self, question: str, answer: str):
        self.question = question
        self.answer = answer
