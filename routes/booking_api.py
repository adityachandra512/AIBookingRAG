# routes/booking_api.py
"""
Flask API routes for booking assistant actions: book, cancel, FAQ, etc.
"""
from flask import Blueprint, request, jsonify
from utils.booking_utils import book_appointment, cancel_appointment, get_faq_answer

booking_api = Blueprint('booking_api', __name__)

@booking_api.route('/book', methods=['POST'])
def book():
    data = request.json
    appt = book_appointment(
        patient_name=data.get('patient_name'),
        doctor_name=data.get('doctor_name'),
        slot=data.get('slot'),
        email=data.get('email')
    )
    if appt:
        return jsonify({'status': 'success', 'appointment': appt.__dict__})
    return jsonify({'status': 'error', 'message': 'Slot not available or doctor not found'}), 400

@booking_api.route('/cancel', methods=['POST'])
def cancel():
    data = request.json
    success = cancel_appointment(
        patient_name=data.get('patient_name'),
        doctor_name=data.get('doctor_name'),
        slot=data.get('slot')
    )
    if success:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Appointment not found'}), 400

@booking_api.route('/faq', methods=['GET'])
def faq():
    question = request.args.get('question')
    answer = get_faq_answer(question)
    if answer:
        return jsonify({'answer': answer})
    return jsonify({'answer': 'Sorry, I do not have an answer for that.'}), 404
