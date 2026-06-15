import gevent.monkey
gevent.monkey.patch_all()

from app import create_app, socketio

flask_app = create_app()

if __name__ == '__main__':
    print("Type of flask_app:", type(flask_app))
    # allow_unsafe_werkzeug=True is needed for running Flask-SocketIO locally
    socketio.run(app=flask_app, debug=True, port=5000, allow_unsafe_werkzeug=True)
