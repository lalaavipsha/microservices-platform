from flask import Flask, jsonify, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger
import logging
import requests
import time
import os

app = Flask(__name__)

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

REQUEST_COUNT = Counter('api_gateway_requests_total', 'Total requests', ['method', 'endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('api_gateway_request_duration_seconds', 'Latency', ['method', 'endpoint'], buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
UPSTREAM_REQUESTS = Counter('api_gateway_upstream_requests_total', 'Upstream requests', ['service', 'status'])

SERVICES = {
    'auth': os.getenv('AUTH_SERVICE_URL', 'http://auth-service'),
    'order': os.getenv('ORDER_SERVICE_URL', 'http://order-service'),
    'payment': os.getenv('PAYMENT_SERVICE_URL', 'http://payment-service'),
    'notification': os.getenv('NOTIFICATION_SERVICE_URL', 'http://notification-service')
}

@app.before_request
def before_request():
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', str(time.time()))

@app.after_request
def after_request(response):
    latency = time.time() - g.start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path, status_code=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(latency)
    logger.info('Request completed', extra={'request_id': g.request_id, 'method': request.method, 'path': request.path, 'status_code': response.status_code, 'latency_ms': round(latency * 1000, 2)})
    response.headers['X-Request-ID'] = g.request_id
    return response

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'api-gateway', 'timestamp': time.time()})

@app.route('/ready', methods=['GET'])
def ready():
    return jsonify({'status': 'ready'})

@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def proxy_request(service_name, path, method='GET', data=None):
    service_url = SERVICES.get(service_name)
    if not service_url:
        return jsonify({'error': f'Service {service_name} not found'}), 404
    url = f"{service_url}{path}"
    try:
        if method == 'GET':
            response = requests.get(url, timeout=10, headers={'X-Request-ID': g.request_id})
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10, headers={'X-Request-ID': g.request_id, 'Content-Type': 'application/json'})
        UPSTREAM_REQUESTS.labels(service=service_name, status='success').inc()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        UPSTREAM_REQUESTS.labels(service=service_name, status='timeout').inc()
        return jsonify({'error': f'Service {service_name} timeout'}), 504
    except requests.exceptions.ConnectionError:
        UPSTREAM_REQUESTS.labels(service=service_name, status='connection_error').inc()
        return jsonify({'error': f'Service {service_name} unavailable'}), 503
    except Exception as e:
        UPSTREAM_REQUESTS.labels(service=service_name, status='error').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    return proxy_request('auth', '/api/v1/register', 'POST', request.json)

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    return proxy_request('auth', '/api/v1/login', 'POST', request.json)

@app.route('/api/v1/auth/validate', methods=['GET'])
def validate_token():
    return proxy_request('auth', '/api/v1/validate', 'GET')

@app.route('/api/v1/orders', methods=['GET'])
def get_orders():
    return proxy_request('order', '/api/v1/orders', 'GET')

@app.route('/api/v1/orders', methods=['POST'])
def create_order():
    return proxy_request('order', '/api/v1/orders', 'POST', request.json)

@app.route('/api/v1/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    return proxy_request('order', f'/api/v1/orders/{order_id}', 'GET')

@app.route('/api/v1/payments', methods=['POST'])
def process_payment():
    return proxy_request('payment', '/api/v1/payments', 'POST', request.json)

@app.route('/api/v1/payments/<payment_id>', methods=['GET'])
def get_payment(payment_id):
    return proxy_request('payment', f'/api/v1/payments/{payment_id}', 'GET')

@app.route('/api/v1/notifications', methods=['POST'])
def send_notification():
    return proxy_request('notification', '/api/v1/notifications', 'POST', request.json)

@app.route('/', methods=['GET'])
def root():
    return jsonify({'service': 'api-gateway', 'version': '1.0.0', 'endpoints': {'health': '/health', 'ready': '/ready', 'metrics': '/metrics', 'auth': '/api/v1/auth/*', 'orders': '/api/v1/orders/*', 'payments': '/api/v1/payments/*', 'notifications': '/api/v1/notifications/*'}})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f'Starting API Gateway on port {port}')
    app.run(host='0.0.0.0', port=port)
