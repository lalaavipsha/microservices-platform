from flask import Flask, jsonify, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger
import logging
import requests
import time
import os
import uuid

app = Flask(__name__)

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

REQUEST_COUNT = Counter('order_service_requests_total', 'Total requests', ['method', 'endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('order_service_request_duration_seconds', 'Latency', ['method', 'endpoint'])
ORDER_CREATED = Counter('order_service_orders_created_total', 'Orders created', ['status'])
ORDER_VALUE = Histogram('order_service_order_value_dollars', 'Order value', buckets=[10, 50, 100, 250, 500, 1000, 5000])

ORDERS_DB = {}
PAYMENT_SERVICE_URL = os.getenv('PAYMENT_SERVICE_URL', 'http://payment-service')

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
    return jsonify({'status': 'healthy', 'service': 'order-service', 'timestamp': time.time()})

@app.route('/ready', methods=['GET'])
def ready():
    return jsonify({'status': 'ready'})

@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/api/v1/orders', methods=['GET'])
def get_orders():
    return jsonify({'orders': list(ORDERS_DB.values()), 'total': len(ORDERS_DB)})

@app.route('/api/v1/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    order = ORDERS_DB.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify(order)

@app.route('/api/v1/orders', methods=['POST'])
def create_order():
    try:
        data = request.json
        if not data or 'items' not in data:
            return jsonify({'error': 'Items required'}), 400
        order_id = str(uuid.uuid4())
        total = sum(item.get('price', 0) * item.get('quantity', 1) for item in data['items'])
        order = {'order_id': order_id, 'items': data['items'], 'total': total, 'status': 'pending', 'created_at': time.time()}
        ORDERS_DB[order_id] = order
        ORDER_CREATED.labels(status='pending').inc()
        ORDER_VALUE.observe(total)
        logger.info(f'Order created: {order_id} total={total}')
        try:
            payment_response = requests.post(f"{PAYMENT_SERVICE_URL}/api/v1/payments", json={'order_id': order_id, 'amount': total, 'currency': 'USD'}, headers={'X-Request-ID': g.request_id}, timeout=10)
            if payment_response.status_code == 201:
                order['status'] = 'payment_initiated'
                order['payment_id'] = payment_response.json().get('payment_id')
        except Exception as e:
            logger.warning(f'Payment call failed: {str(e)}')
        return jsonify({'message': 'Order created successfully', 'order': order}), 201
    except Exception as e:
        ORDER_CREATED.labels(status='failed').inc()
        logger.error(f'Error creating order: {str(e)}')
        return jsonify({'error': 'Failed to create order'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8082))
    logger.info(f'Starting Order Service on port {port}')
    app.run(host='0.0.0.0', port=port)
