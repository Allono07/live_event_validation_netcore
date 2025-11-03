"""Application entry point."""
import sys
import os
from app import create_app, socketio
from config.database import db


app = create_app()


if __name__ == '__main__':
    # Check for commands
    if len(sys.argv) > 1 and sys.argv[1] == 'init-db':
        print("Database tables already created during app initialization!")
        print("Database file: validation_dashboard.db")
    else:
        # Run the application with SocketIO
        socketio.run(app, 
                    host='0.0.0.0',
                    port=int(os.environ.get('PORT', 5001)),
                    debug=app.config['DEBUG'])
