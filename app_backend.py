# app_backend.py
"""
Flask app entry point for AI Booking Assistant backend API.
"""
from flask import Flask
from routes.booking_api import booking_api

app = Flask(__name__)
app.register_blueprint(booking_api, url_prefix='/api')

if __name__ == '__main__':
    app.run(debug=True)
