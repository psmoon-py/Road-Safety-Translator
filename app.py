import os
import re
import logging
import sqlite3
from flask import Flask, request, jsonify, render_template
import PyPDF2
from googletrans import Translator

app = Flask(__name__, static_folder="static", template_folder="templates")

# Initialize the translator
translator = Translator()

# Create database connection for road safety messages and feedback
def init_db():
    conn = sqlite3.connect("road_safety.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS safety_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT,
            message TEXT,
            language TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_text TEXT,
            translated_text TEXT,
            user_feedback TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')  # Ensure you have an index.html file in the templates folder

# API to upload and process PDF
@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename.endswith('.pdf'):
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() or ""  # Handle None return from extract_text
            
            # Sanitize the text (remove excessive whitespace and unsupported characters)
            pdf_text = re.sub(r'\s+', ' ', pdf_text).strip()  # Replace multiple spaces with a single space
            
            return jsonify({"content": pdf_text}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500
    return jsonify({"error": "Invalid file type. Please upload a PDF."}), 400

# API for translation
logging.basicConfig(level=logging.INFO)

@app.route('/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Request body is empty or not valid JSON"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid JSON payload: {str(e)}"}), 400

    original_text = data.get("text")
    target_language = data.get("language")

    if not original_text:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    if not target_language:
        return jsonify({"error": "Missing 'language' parameter"}), 400

    try:
        translated_text = translator.translate(original_text, dest=target_language).text
        return jsonify({"translated_text": translated_text}), 200
    except Exception as e:
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500

# API to submit user feedback
@app.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    original_text = data.get("original_text")
    translated_text = data.get("translated_text")
    user_feedback = data.get("feedback")
    
    if not original_text or not translated_text or not user_feedback:
        return jsonify({"error": "All fields are required"}), 400

    # Store feedback in the database
    conn = sqlite3.connect("road_safety.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO feedback (original_text, translated_text, user_feedback)
        VALUES (?, ?, ?)
    """, (original_text, translated_text, user_feedback))
    conn.commit()
    conn.close()

    return jsonify({"message": "Feedback submitted successfully"}), 200

@app.route('/get_message', methods=['GET'])
def get_message():
    region = request.args.get("region")
    language = request .get("language")
    
    conn = sqlite3.connect("road_safety.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message FROM safety_messages
        WHERE region = ? AND language = ?
    """, (region, language))
    message = cursor.fetchone()
    conn.close()
    
    if message:
        return jsonify({"message": message[0]}), 200
    return jsonify({"error": "No messages found for the specified region and language"}), 404

# Adding messages to the database (Admin functionality)
@app.route('/add_message', methods=['POST'])
def add_message():
    data = request.json
    region = data.get("region")
    message = data.get("message")
    language = data.get("language")

    if not region or not message or not language:
        return jsonify({"error": "All fields are required"}), 400

    conn = sqlite3.connect("road_safety.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO safety_messages (region, message, language)
        VALUES (?, ?, ?)
    """, (region, message, language))
    conn.commit()
    conn.close()

    return jsonify({"message": "Safety message added successfully"}), 201

if __name__ == '__main__':
    app.run(debug=True)
