"""
Smallest.ai TTS Proxy Route
Proxies text-to-speech requests to Smallest.ai to keep the API key secure.
"""

import requests as http_requests
from flask import Blueprint, request, Response, jsonify
from app.config import Config

tts_bp = Blueprint('tts', __name__)

@tts_bp.route('/tts', methods=['POST'])
def text_to_speech():
    """
    Proxy TTS request to Smallest.ai API.
    
    Accepts JSON: { "text": "...", "voice_gender": "male" | "female" }
    Returns: WAV audio binary
    """
    if not Config.SMALLEST_API_KEY:
        return jsonify({'error': 'Smallest.ai API key not configured'}), 503

    data = request.get_json()
    if not data or not data.get('text'):
        return jsonify({'error': 'text is required'}), 400

    text = data['text']
    voice_gender = data.get('voice_gender', 'male')

    # Select voice based on gender
    if voice_gender == 'female':
        speaker = "divya"
    else:
        speaker = "ryan"

    # Truncate very long text to avoid huge TTS costs (max ~500 chars)
    if len(text) > 500:
        text = text[:500]

    url = "https://api.smallest.ai/waves/v1/lightning-v3.1/get_speech"

    headers = {
        "Authorization": f"Bearer {Config.SMALLEST_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "voice_id": speaker,
        "sample_rate": 24000,
        "output_format": "wav"
    }

    try:
        response = http_requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='audio/wav',
                headers={
                    'Content-Type': 'audio/wav',
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            error_msg = response.text[:200] if response.text else 'Unknown Smallest AI error'
            print(f"Smallest AI API error ({response.status_code}): {error_msg}")
            
            # fallback to divya if speaker not found
            if response.status_code == 400 and "Invalid Voice ID" in error_msg:
                payload["voice_id"] = "divya"
                retry_response = http_requests.post(url, json=payload, headers=headers, timeout=30)
                if retry_response.status_code == 200:
                    return Response(
                        retry_response.content,
                        mimetype='audio/wav',
                        headers={
                            'Content-Type': 'audio/wav',
                            'Cache-Control': 'no-cache'
                        }
                    )
            
            return jsonify({
                'error': f'Smallest AI API error: {response.status_code}',
                'details': error_msg
            }), response.status_code

    except http_requests.exceptions.Timeout:
        return jsonify({'error': 'TTS request timed out'}), 504
    except Exception as e:
        print(f"TTS proxy error: {e}")
        return jsonify({'error': 'TTS service unavailable'}), 500
