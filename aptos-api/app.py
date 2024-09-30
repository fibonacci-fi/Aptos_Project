from flask import Flask, jsonify, request
from config import Config
from extensions import db, socketio
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from flask_swagger_ui import get_swaggerui_blueprint


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    from routes import providers, pools
    app.register_blueprint(providers.bp)
    app.register_blueprint(pools.bp)

    limiter = Limiter(
        key_func=get_remote_address,  # Make sure this is passed only once
        app=app,
        default_limits=["200 per day", "50 per hour"]
    )
    app.limiter = limiter  # Store limiter on app for global access

    # Swagger UI setup
    SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI (without trailing '/')
    API_URL = '/static/swagger.json'  # Our API url (can of course be a local resource)

    # Call factory function to create our blueprint
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={  # Swagger UI config overrides
            'app_name': "Aptos Dashboard API"
        }
    )

    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    @app.route('/health')
    def health_check():
        return jsonify(status='healthy !'), 200

    @app.before_request
    def log_request_info():
        # app.logger.info('Headers: %s', request.headers)
        app.logger.info('Body: %s', request.get_data())

    @app.after_request
    def log_response_info(response):
        app.logger.info('Response Status: %s', response.status)
        return response

    return app

app = create_app()

@app.route('/')
def default_route():
    return "Welcome to the Aptos Dashboard API"

@app.route('/api/resource')
@app.limiter.limit("100 per day")
def rate_limited_resource():
    return jsonify(data='This is rate limited')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port, log_output=True, allow_unsafe_werkzeug=True)

