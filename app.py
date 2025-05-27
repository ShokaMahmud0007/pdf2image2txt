from flask import Flask, render_template, request, send_file, send_from_directory, jsonify
import pytesseract
import zipfile
import io
from PIL import Image
from pdf2image import convert_from_path
import os
import json
import re
import uuid
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, "images")
OUTPUT_FILE = os.path.join(UPLOAD_FOLDER, "output.json")
PROGRESS_FILE = os.path.join(UPLOAD_FOLDER, "progress.json")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Set tesseract and poppler path
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

@app.route('/', methods=['GET', 'POST'])
def index():
    extracted_text = ""
    json_output = ""
    show_json = False
    show_images = False
    download_links = []

    # Clean old files
    for f in os.listdir(IMAGE_FOLDER):
        os.remove(os.path.join(IMAGE_FOLDER, f))
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({"progress": 0, "current": 0, "total": 0}, f)

    if request.method == 'POST':
        files = request.files.getlist('images')
        extract_text = request.form.get('extract_text')
        to_json = request.form.get('to_json')
        save_images = request.form.get('save_images')

        all_lines = []
        image_count = 0
        total_files = len(files)

        for idx, uploaded in enumerate(files):
            ext = os.path.splitext(uploaded.filename)[1].lower()
            filename = str(uuid.uuid4()) + ext
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            uploaded.save(file_path)

            if ext == '.pdf':
                images = convert_from_path(file_path, poppler_path=POPPLER_PATH)
                for i, img in enumerate(images):
                    image_count += 1
                    if save_images:
                        img_name = f"page_{idx}_{i}.jpg"
                        img_path = os.path.join(IMAGE_FOLDER, img_name)
                        img.save(img_path)
                        download_links.append(img_name)
                    if extract_text or to_json:
                        text = pytesseract.image_to_string(img, lang='eng+ben')
                        all_lines.extend(text.strip().splitlines())
            else:
                img = Image.open(file_path)
                image_count += 1
                if save_images:
                    img_name = f"image_{idx}.jpg"
                    img_path = os.path.join(IMAGE_FOLDER, img_name)
                    img.save(img_path)
                    download_links.append(img_name)
                if extract_text or to_json:
                    text = pytesseract.image_to_string(img, lang='eng+ben')
                    all_lines.extend(text.strip().splitlines())

            # Update progress
            with open(PROGRESS_FILE, 'w') as f:
                json.dump({
                    "progress": int((idx + 1) / total_files * 100),
                    "current": idx + 1,
                    "total": total_files
                }, f)

        if extract_text:
            extracted_text = "\n".join(all_lines)

        if to_json:
            formatted = []
            for line in all_lines:
                line = re.sub(r'^[\d\s:.\-]*', '', line)
                if "-" in line:
                    parts = line.split("-", 1)
                    formatted.append({
                        "en": parts[0].strip(),
                        "bn": parts[1].strip()
                    })
            json_output = json.dumps(formatted, ensure_ascii=False, indent=4)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(json_output)
            show_json = True

        if save_images and download_links:
            show_images = True
            # Create ZIP of images if requested and images exist
        if save_images and download_links:
            zip_path = os.path.join(UPLOAD_FOLDER, "images.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for img_file in download_links:
                    img_full_path = os.path.join(IMAGE_FOLDER, img_file)
                    zipf.write(img_full_path, arcname=img_file)
            show_images = True


    return render_template('index.html',
                           text=extracted_text,
                           json_text=json_output,
                           show_json=show_json,
                           show_images=show_images,
                           images=download_links)

@app.route('/download/json')
def download_json():
    return send_file(OUTPUT_FILE, as_attachment=True)

@app.route('/download/image/<filename>')
def download_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename, as_attachment=True)

@app.route('/progress')
def progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({"progress": 0, "current": 0, "total": 0})

@app.route('/download/images_zip')
def download_images_zip():
    zip_path = os.path.join(UPLOAD_FOLDER, "images.zip")
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
