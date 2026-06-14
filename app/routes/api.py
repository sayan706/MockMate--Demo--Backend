from flask import Blueprint, jsonify
from app.services.utils import load_interviews

api_bp = Blueprint('api', __name__)

@api_bp.route('/interviews', methods=['GET'])
def get_interviews():
    return jsonify(load_interviews())
