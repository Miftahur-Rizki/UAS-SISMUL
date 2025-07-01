from flask import Flask, render_template, request, send_from_directory
import os
import subprocess
from stegano import lsb

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def run_ffmpeg(command):
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ FFmpeg success:", result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg error:", e.stderr.decode())
        raise RuntimeError("FFmpeg gagal dijalankan. Pastikan ffmpeg tersedia.")


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

    try:
        if media_type == 'image':
            run_ffmpeg(['ffmpeg', '-i', upload_path, '-vf', 'scale=iw/2:ih/2', output_path])
            if secret_message:
                stego_filename = f"stego_{filename}"
                stego_output = os.path.join(OUTPUT_FOLDER, stego_filename)
                lsb.hide(output_path, secret_message).save(stego_output)
                output_filename = stego_filename

        elif media_type == 'audio':
            run_ffmpeg(['ffmpeg', '-i', upload_path, '-b:a', '128k', output_path])

        elif media_type == 'video':
            run_ffmpeg(['ffmpeg', '-i', upload_path, '-vcodec', 'libx264', '-crf', '28', output_path])

        else:
            return "Tipe media tidak dikenali."

    except RuntimeError as e:
        return f"<h3>Error saat memproses file: {str(e)}</h3>"

    return render_template("result.html",
                           filename=output_filename,
                           filetype=media_type,
                           original_size=os.path.getsize(upload_path) // 1024,
                           compressed_size=os.path.getsize(os.path.join(OUTPUT_FOLDER, output_filename)) // 1024,
                           compression_ratio=round(100 * os.path.getsize(os.path.join(OUTPUT_FOLDER, output_filename)) /
                                                   os.path.getsize(upload_path), 2))


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


@app.route('/reveal_stego', methods=['POST'])
def reveal_from_upload():
    file = request.files.get('stego_file')
    if not file:
        return "Tidak ada file yang dipilih."

    filepath = os.path.join(UPLOAD_FOLDER, 'temp_stego.png')
    file.save(filepath)

    try:
        message = lsb.reveal(filepath)
        return render_template("reveal.html", message=message)
    except:
        return render_template("reveal.html", message=None)


# Jalankan di Railway
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
