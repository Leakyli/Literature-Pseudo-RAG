import os
from flask import Flask, request, jsonify
import pymupdf4llm

app = Flask(__name__)

@app.route('/v1/convert/file', methods=['POST'])
def convert_pdf():
    # 1. Catch the file from n8n
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
        
    pdf_file = request.files['file']
    temp_path = f"/tmp/{pdf_file.filename}"
    pdf_file.save(temp_path)
    
    try:
        # 2. Instantly convert to Markdown using PyMuPDF4LLM
        md_text = pymupdf4llm.to_markdown(temp_path)
        
        # 3. Return the exact JSON structure Docling used!
        return jsonify({
            "document": {
                "md_content": md_text
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
