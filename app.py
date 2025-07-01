from flask import Flask, render_template, request, send_from_directory
import os
import subprocess
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================
# LSB STEGANOGRAFI (MANUAL)
# =========================

def lsb_hide(image_path, message, output_path):
    img = Image.open(image_path)
    encoded = img.copy()
    width, height = img.size
    message += chr(0)  # Akhiri pesan dengan karakter NULL
    
    data_index = 0
    binary_message = ''.join([format(ord(char), '08b') for char in message])

    for y in range(height):
        for x in range(width):
            if data_index < len(binary_message):
                pixel = list(img.getpixel((x, y)))
                for i in range(3):  # R, G, B
                    if data_index < len(binary_message):
                        pixel[i] = pixel[i] & ~1 | int(binary_message[data_index])
                        data_index += 1
                encoded.putpixel((x, y), tuple(pixel))
            else:
                encoded.save(output_path)
                return

def lsb_reveal(image_path):
    img = Image.open(image_path)
    width, height = img.size
    binary_message = ''
    
    for y in range(height):
        for x in range(width):
            pixel = img.getpixel((x, y))
            for i in range(3):
                binary_message += str(pixel[i] & 1)
    
    chars = [binary_message[i:i+8] for i in range(0, len(binary_message), 8)]
    message = ''
    for c in chars:
        if c == '00000000':  # NULL char
            break
        message += chr(int(c, 2))
    return message

# ============================
# ROUTING FLASK
# ============================

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

    # Kompresi dan steganografi berdasarkan jenis media
    if media_type == 'image':
        subprocess.run(['ffmpeg', '-i', upload_path, '-vf', 'scale=iw/2:ih/2', output_path])
        if secret_message:
            stego_filename = f"stego_{filename}"
            stego_output = os.path.join(OUTPUT_FOLDER, stego_filename)
            lsb_hide(output_path, secret_message, stego_output)
            output_filename = stego_filename
    elif media_type == 'audio':
        subprocess.run(['ffmpeg', '-i', upload_path, '-b:a', '128k', output_path])
    elif media_type == 'video':
        subprocess.run(['ffmpeg', '-i', upload_path, '-vcodec', 'libx264', '-crf', '28', output_path])
    else:
        return "Tipe media tidak dikenali."

    return render_template('result.html',
                           filename=output_filename,
                           filetype=media_type,
                           original_size=round(os.path.getsize(upload_path) / 1024, 2),
                           compressed_size=round(os.path.getsize(os.path.join(OUTPUT_FOLDER, output_filename)) / 1024, 2),
                           compression_ratio=round(100 * os.path.getsize(os.path.join(OUTPUT_FOLDER, output_filename)) / os.path.getsize(upload_path), 2))

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
        message = lsb_reveal(filepath)
        return render_template('reveal.html', message=message)
    except:
        return render_template('reveal.html', message=None)

# Run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
