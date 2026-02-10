from flask import Flask, jsonify, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger
import logging
import jwt
import bcrypt
import time
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

REQUEST_COUNT = Counter('auth_service_requests_total', 'Total requests', ['method', 'endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('auth_service_request_duration_seconds', 'Latency', ['method', 'endpoint'])
AUTH_ATTEMPTS = Counter('auth_service_auth_attempts_total', 'Auth attempts', ['type', 'result'])

USERS_DB = {}

@app.before_request
def before_request():
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

@app.after_request
def after_request(response):
    latency = time.time() - g.start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path, status_code=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(latency)
    return response

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'auth-service', 'timestamp': time.time()})

@app.route('/ready', methods=['GET'])
def ready():
    return jsonify({'status': 'ready'})

@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/api/v1/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not data or 'email' not in data or 'password' not in data:
            AUTH_ATTEMPTS.labels(type='register', result='invalid_request').inc()
            return jsonify({'error': 'Email and password required'}), 400
        email = data['email']
        password = data['password']
        if email in USERS_DB:
            AUTH_ATTEMPTS.labels(type='register', result='user_exists').inc()
            return jsonify({'error': 'User already exists'}), 409
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_id = str(uuid.uuid4())
        USERS_DB[email] = {'id': user_id, 'email': email, 'password_hash': password_hash, 'created_at': time.time()}
        AUTH_ATTEMPTS.labels(type='register', result='success').inc()
        logger.info(f'User registered: {email}')
        return jsonify({'message': 'User registered successfully', 'user_id': user_id}), 201
    except Exception as e:
        AUTH_ATTEMPTS.labels(type='register', result='error').inc()
        logger.error(f'Registration error: {str(e)}')
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/v1/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data or 'email' not in data or 'password' not in data:
            AUTH_ATTEMPTS.labels(type='login', result='invalid_request').inc()
            return jsonify({'error': 'Email and password required'}), 400
        email = data['email']
        password = data['password']
        user = USERS_DB.get(email)
        if not user:
            AUTH_ATTEMPTS.labels(type='login', result='user_not_found').inc()
            return jsonify({'error': 'Invalid credentials'}), 401
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            AUTH_ATTEMPTS.labels(type='login', result='wrong_password').inc()
            return jsonify({'error': 'Invalid credentials'}), 401
        token = jwt.encode({'user_id': user['id'], 'email': email, 'exp': time.time() + 3600}, app.config['SECRET_KEY'], algorithm='HS256')
        AUTH_ATTEMPTS.labels(type='login', result='success').inc()
        logger.info(f'User logged in: {email}')
        return jsonify({'message': 'Login successful', 'token': token, 'user_id': user['id']})
    except Exception as e:
        AUTH_ATTEMPTS.labels(type='login', result='error').inc()
        logger.error(f'Login error: {str(e)}')
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/v1/validate', methods=['GET'])
def validate():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'valid': False, 'error': 'No token provided'}), 401
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return jsonify({'valid': True, 'user_id': payload['user_id'], 'email': payload['email']})
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'valid': False, 'error': 'Invalid token'}), 401

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8081))
    logger.info(f'Starting Auth Service on port {port}')
    app.run(host='0.0.0.0', port=port)
