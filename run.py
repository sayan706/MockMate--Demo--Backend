import gevent.monkey
gevent.monkey.patch_all()

import os
from app import create_app, socketio

flask_app = create_app()

if __name__ == '__main__':
    print("Type of flask_app:", type(flask_app))
    port = int(os.environ.get('PORT', 5000))
    # allow_unsafe_werkzeug=True is needed for running Flask-SocketIO locally
    socketio.run(app=flask_app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
