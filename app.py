from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session
import os
import subprocess
from stegano import lsb

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'devsecret')

# Folder Upload dan Output
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    media_type = request.form.get('type')
    secret_message = request.form.get('message')

    if not file or file.filename == '':
        return "Tidak ada file yang dipilih."

    filename = file.filename
    upload_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(upload_path)

    output_filename = f"compressed_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    # Kompresi berdasarkan media type
    if media_type == 'image':
        subprocess.run(['ffmpeg', '-i', upload_path, '-vf', 'scale=iw/2:ih/2', output_path])
        if secret_message:
            stego_filename = f"stego_{filename}"
            stego_output = os.path.join(OUTPUT_FOLDER, stego_filename)
            lsb.hide(output_path, secret_message).save(stego_output)
            output_filename = stego_filename
    elif media_type == 'audio':
        subprocess.run(['ffmpeg', '-i', upload_path, '-b:a', '128k', output_path])
    elif media_type == 'video':
        subprocess.run(['ffmpeg', '-i', upload_path, '-vcodec', 'libx264', '-crf', '28', output_path])
    else:
        return "Tipe media tidak dikenali."

    # Simpan info hasil ke session
    session['result_file'] = output_filename
    session['filetype'] = media_type
    session['original_size'] = round(os.path.getsize(upload_path) / 1024, 2)
    session['compressed_size'] = round(os.path.getsize(os.path.join(OUTPUT_FOLDER, output_filename)) / 1024, 2)

    return redirect(url_for('result'))

@app.route('/result')
def result():
    filename = session.get('result_file')
    original_size = session.get('original_size', 0)
    compressed_size = session.get('compressed_size', 0)
    filetype = session.get('filetype', '')
    compression_ratio = round(100 * compressed_size / original_size, 2) if original_size else 0

    return render_template('result.html',
                           filename=filename,
                           original_size=original_size,
                           compressed_size=compressed_size,
                           compression_ratio=compression_ratio,
                           filetype=filetype)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

@app.route('/reveal_stego', methods=['POST'])
def reveal_from_upload():
    file = request.files.get('stego_file')
    if not file:
        return render_template('reveal.html', message=None)

    filepath = os.path.join(UPLOAD_FOLDER, 'temp_stego.png')
    file.save(filepath)

    try:
        message = lsb.reveal(filepath)
        return render_template('reveal.html', message=message)
    except:
        return render_template('reveal.html', message=None)

# Untuk favicon (opsional)
@app.route('/favicon.ico')
def favicon():
    return '', 204

# Run Flask untuk Railway/Render
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
