from flask import Flask, render_template, request, send_from_directory
import os
import subprocess
from werkzeug.utils import secure_filename
from stegano import lsb

app = Flask(__name__)

# Batas ukuran file (contoh: 200 MB)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

# Folder penyimpanan
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/output'
STATIC_UPLOADS = os.path.join('static', 'uploads')

# Pastikan semua folder ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(STATIC_UPLOADS, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    media_type = request.form.get('type')
    secret_message = request.form.get('message')

    if not file or file.filename == '':
        return "❌ Tidak ada file yang dipilih."

    # Amankan nama file
    filename = secure_filename(file.filename)
    upload_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(upload_path)

    # Nama file hasil kompresi
    output_filename = f"compressed_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    try:
        # Proses kompresi
        if media_type == 'image':
            subprocess.run(['ffmpeg', '-i', upload_path, '-vf', 'scale=iw/2:ih/2', output_path], check=True)
            if secret_message:
                stego_filename = f"stego_{filename}"
                stego_output = os.path.join(OUTPUT_FOLDER, stego_filename)
                lsb.hide(output_path, secret_message).save(stego_output)
                output_filename = stego_filename
                output_path = stego_output
        elif media_type == 'audio':
            subprocess.run(['ffmpeg', '-i', upload_path, '-b:a', '128k', output_path], check=True)
        elif media_type == 'video':
            subprocess.run(['ffmpeg', '-i', upload_path, '-vcodec', 'libx264', '-crf', '28', output_path], check=True)
        else:
            return "❌ Tipe media tidak dikenali."

        # Pindahkan hasil ke static/uploads agar bisa di-preview
        final_static_path = os.path.join(STATIC_UPLOADS, output_filename)
        os.rename(output_path, final_static_path)

        # Hitung ukuran file
        original_size = os.path.getsize(upload_path) // 1024
        compressed_size = os.path.getsize(final_static_path) // 1024
        compression_ratio = round((compressed_size / original_size) * 100, 2)

        return render_template("result.html",
                               filename=output_filename,
                               filetype=media_type,
                               original_size=original_size,
                               compressed_size=compressed_size,
                               compression_ratio=compression_ratio)

    except Exception as e:
        return f"❌ Terjadi kesalahan saat memproses file: {str(e)}"

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(STATIC_UPLOADS, filename, as_attachment=True)

@app.route('/reveal_stego', methods=['POST'])
def reveal_from_upload():
    file = request.files.get('stego_file')
    if not file:
        return "❌ Tidak ada file yang dipilih."

    filepath = os.path.join(UPLOAD_FOLDER, 'temp_stego.png')
    file.save(filepath)

    try:
        message = lsb.reveal(filepath)
        return render_template("reveal.html", message=message)
    except:
        return render_template("reveal.html", message=None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
