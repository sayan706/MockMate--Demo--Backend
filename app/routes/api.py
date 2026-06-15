import os
import uuid
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
from app.services.utils import load_interviews
from app.services.cv_parser import parse_cv, allowed_file
from app.config import Config

api_bp = Blueprint('api', __name__)

@api_bp.route('/interviews', methods=['GET'])
def get_interviews():
    return jsonify(load_interviews())

@api_bp.route('/upload-cv', methods=['POST'])
def upload_cv():
    """
    Upload a CV/Resume file (PDF or DOCX) for RAG-based interview personalization.
    
    Returns:
        JSON with cv_text (extracted text) and cv_id (unique identifier)
    """
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided. Please upload a CV file.'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400
    
    # Validate file extension
    if not allowed_file(file.filename, Config.ALLOWED_CV_EXTENSIONS):
        return jsonify({
            'error': f'Unsupported file format. Allowed formats: {", ".join(Config.ALLOWED_CV_EXTENSIONS)}'
        }), 400
    
    # Generate unique filename to avoid collisions
    ext = os.path.splitext(secure_filename(file.filename))[1]
    cv_id = str(uuid.uuid4())
    safe_filename = f"{cv_id}{ext}"
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_filename)
    
    try:
        # Save file temporarily
        file.save(file_path)
        
        # Extract text from CV
        cv_text = parse_cv(file_path)
        
        print(f"CV uploaded and parsed successfully: {file.filename} ({len(cv_text)} chars)")
        
        return jsonify({
            'cv_id': cv_id,
            'cv_text': cv_text,
            'filename': file.filename,
            'char_count': len(cv_text),
            'message': 'CV uploaded and parsed successfully.'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"CV upload error: {e}")
        return jsonify({'error': 'Failed to process CV. Please try again.'}), 500
    finally:
        # Clean up: remove the uploaded file after extraction
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
