"""WebSocket controller for real-time updates."""
from flask_socketio import emit, join_room, leave_room
from app import socketio


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    emit('connected', {'data': 'Connected to validation server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    pass


@socketio.on('join')
def handle_join(data):
    """Join a room to receive updates for a specific app."""
    app_id = data.get('app_id')
    if app_id:
        join_room(app_id)
        emit('joined', {'app_id': app_id})


@socketio.on('leave')
def handle_leave(data):
    """Leave a room."""
    app_id = data.get('app_id')
    if app_id:
        leave_room(app_id)
        emit('left', {'app_id': app_id})
