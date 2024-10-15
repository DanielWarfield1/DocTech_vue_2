from flask import Flask, request, jsonify
import os
import ffmpeg

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    temp_path = os.path.join(UPLOAD_FOLDER, 'temp.ogg')
    file.save(temp_path)

    mp3_path = os.path.join(UPLOAD_FOLDER, 'recording.mp3')

    # Convert to MP3 using ffmpeg
    try:
        ffmpeg.input(temp_path).output(mp3_path).run()
        os.remove(temp_path)  # Remove temporary OGG file
        return jsonify({'message': 'File uploaded and saved as MP3', 'file_path': mp3_path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
