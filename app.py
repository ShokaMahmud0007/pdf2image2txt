from flask import Flask, render_template, request, send_file
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os
import json
import re
import zipfile
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, "images")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    extracted_text = ""
    json_output = ""
    show_download = False
    show_images = False
    image_files = []
    download_json = False
    download_zip = False

    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        selected_options = request.form.getlist('options')
        save_images = 'images' in selected_options
        save_json = 'json' in selected_options
        extract_text = 'text' in selected_options

        json_data = []
        download_links = []

        for file in uploaded_files:
            ext = os.path.splitext(file.filename)[1].lower()
            unique_id = uuid.uuid4().hex
            temp_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_{file.filename}")
            file.save(temp_path)

            if ext == '.pdf':
                images = convert_from_path(temp_path)
            else:
                images = [Image.open(temp_path)]

            for idx, img in enumerate(images):
                if extract_text or save_json:
                    text = pytesseract.image_to_string(img, lang='eng+ben')
                    if extract_text:
                        extracted_text += f"\n{text.strip()}"
                    if save_json:
                        for line in text.strip().splitlines():
                            line = re.sub(r'^[\d\s:.\-]*', '', line)
                            if "-" in line:
                                parts = line.split("-", 1)
                                json_data.append({
                                    "en": parts[0].strip(),
                                    "bn": parts[1].strip()
                                })

                if save_images:
                    img_filename = f"{unique_id}_{idx}.png"
                    img_path = os.path.join(IMAGE_FOLDER, img_filename)
                    img.save(img_path)
                    download_links.append(img_filename)

        if save_json and json_data:
            with open(os.path.join(UPLOAD_FOLDER, "output.json"), "w", encoding="utf-8") as f:
                json_output = json.dumps(json_data, ensure_ascii=False, indent=2)
                f.write(json_output)
            download_json = True

        if save_images and download_links:
            zip_path = os.path.join(UPLOAD_FOLDER, "images.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for img_file in download_links:
                    zipf.write(os.path.join(IMAGE_FOLDER, img_file), arcname=img_file)
            show_images = True
            download_zip = True
            image_files = download_links

    return render_template('index.html',
                           text=extracted_text,
                           json_text=json_output,
                           show_images=show_images,
                           show_download_json=download_json,
                           show_download_zip=download_zip)

@app.route('/download/json')
def download_json():
    return send_file(os.path.join(UPLOAD_FOLDER, "output.json"), as_attachment=True)

@app.route('/download/zip')
def download_zip():
    return send_file(os.path.join(UPLOAD_FOLDER, "images.zip"), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
