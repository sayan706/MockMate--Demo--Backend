"""
ElevenLabs TTS Proxy Route
Proxies text-to-speech requests to ElevenLabs API to keep the API key secure.
"""

import requests as http_requests
from flask import Blueprint, request, Response, jsonify
from app.config import Config

tts_bp = Blueprint('tts', __name__)


@tts_bp.route('/tts', methods=['POST'])
def text_to_speech():
    """
    Proxy TTS request to ElevenLabs API.
    
    Accepts JSON: { "text": "...", "voice_gender": "male" | "female" }
    Returns: MP3 audio binary
    """
    if not Config.ELEVENLABS_API_KEY:
        return jsonify({'error': 'ElevenLabs API key not configured'}), 503

    data = request.get_json()
    if not data or not data.get('text'):
        return jsonify({'error': 'text is required'}), 400

    text = data['text']
    voice_gender = data.get('voice_gender', 'male')

    # Select voice based on gender
    if voice_gender == 'female':
        voice_id = Config.ELEVENLABS_FEMALE_VOICE_ID
    else:
        voice_id = Config.ELEVENLABS_MALE_VOICE_ID

    # Truncate very long text to avoid huge TTS costs (max ~5000 chars)
    if len(text) > 5000:
        text = text[:5000]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": Config.ELEVENLABS_API_KEY
    }

    payload = {
        "text": text,
        "model_id": Config.ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }

    try:
        response = http_requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='audio/mpeg',
                headers={
                    'Content-Type': 'audio/mpeg',
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            error_msg = response.text[:200] if response.text else 'Unknown ElevenLabs error'
            print(f"ElevenLabs API error ({response.status_code}): {error_msg}")
            return jsonify({
                'error': f'ElevenLabs API error: {response.status_code}',
                'details': error_msg
            }), response.status_code

    except http_requests.exceptions.Timeout:
        return jsonify({'error': 'TTS request timed out'}), 504
    except Exception as e:
        print(f"TTS proxy error: {e}")
        return jsonify({'error': 'TTS service unavailable'}), 500
