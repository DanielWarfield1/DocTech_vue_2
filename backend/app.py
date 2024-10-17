# main_app.py
from flask import Flask, request, jsonify, send_from_directory
import os
import ffmpeg
from openai import OpenAI
from docTech import decide_and_respond, handle_action  # Assuming these are in docTech.py

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/decide_and_respond', methods=['POST'])
def decide_and_respond_endpoint():
    if 'audio' not in request.files:
        print("No audio file found in request.")
        return jsonify({'error': 'No file part'}), 400

    file = request.files['audio']
    temp_path = os.path.join(UPLOAD_FOLDER, 'temp.ogg')
    mp3_path = os.path.join(UPLOAD_FOLDER, 'recording.mp3')

    try:
        # Save the file temporarily
        print("Saving uploaded audio file...")
        file.save(temp_path)
        
        # Convert the audio to MP3
        print("Converting audio file to MP3 format...")
        ffmpeg.input(temp_path).output(mp3_path).overwrite_output().run()
        os.remove(temp_path)

        # Transcribe the audio to text using Whisper
        print("Transcribing audio to text with Whisper...")
        client = OpenAI()
        with open(mp3_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        transcribed_text = transcription.text
        print("Transcription result:", transcribed_text)

        # Use the transcribed text in decide_and_respond
        context = {"current_page": request.args.get("current_page", 1)}
        print("Passing transcription to decide_and_respond...")
        plan_data = decide_and_respond(transcribed_text, context)
        print("Response from decide_and_respond:", plan_data)

        return jsonify({
            'audio_url': f"http://localhost:5000/audio_response?filename=speech.mp3",
            'plan': plan_data
        }), 200
    except Exception as e:
        print("An error occurred:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/audio_response')
def audio_response():
    filename = request.args.get('filename')
    print("Serving audio response file:", filename)
    return send_from_directory(UPLOAD_FOLDER, filename, mimetype="audio/mpeg")

@app.route('/execute_plan', methods=['POST'])
def execute_plan():
    try:
        plan = request.json
        print("Executing plan:", plan)
        response = handle_action(plan)
        print("Response from handle_action:", response)
        return jsonify(response), 200
    except Exception as e:
        print("An error occurred while executing plan:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
