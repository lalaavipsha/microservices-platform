from flask import Flask, jsonify, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger
import logging
import time
import os
import uuid
import random

app = Flask(__name__)

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

REQUEST_COUNT = Counter('payment_service_requests_total', 'Total requests', ['method', 'endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('payment_service_request_duration_seconds', 'Latency', ['method', 'endpoint'])
PAYMENT_PROCESSED = Counter('payment_service_payments_total', 'Payments processed', ['status', 'currency'])
PAYMENT_AMOUNT = Histogram('payment_service_payment_amount_dollars', 'Payment amount', buckets=[10, 50, 100, 250, 500, 1000, 5000])

PAYMENTS_DB = {}

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
    return jsonify({'status': 'healthy', 'service': 'payment-service', 'timestamp': time.time()})

@app.route('/ready', methods=['GET'])
def ready():
    return jsonify({'status': 'ready'})

@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/api/v1/payments', methods=['POST'])
def create_payment():
    try:
        data = request.json
        if not data or 'amount' not in data or 'order_id' not in data:
            return jsonify({'error': 'Amount and order_id required'}), 400
        amount = data['amount']
        currency = data.get('currency', 'USD')
        order_id = data['order_id']
        payment_id = str(uuid.uuid4())
        processing_time = random.uniform(0.1, 0.5)
        time.sleep(processing_time)
        success = random.random() < 0.95
        status = 'completed' if success else 'failed'
        payment = {'payment_id': payment_id, 'order_id': order_id, 'amount': amount, 'currency': currency, 'status': status, 'processing_time': round(processing_time, 3), 'created_at': time.time()}
        PAYMENTS_DB[payment_id] = payment
        PAYMENT_PROCESSED.labels(status=status, currency=currency).inc()
        PAYMENT_AMOUNT.observe(amount)
        logger.info(f'Payment {status}: {payment_id} amount={amount}')
        status_code = 201 if success else 402
        return jsonify({'message': f'Payment {status}', 'payment': payment}), status_code
    except Exception as e:
        logger.error(f'Error processing payment: {str(e)}')
        return jsonify({'error': 'Payment failed'}), 500

@app.route('/api/v1/payments/<payment_id>', methods=['GET'])
def get_payment(payment_id):
    payment = PAYMENTS_DB.get(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    return jsonify(payment)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8083))
    logger.info(f'Starting Payment Service on port {port}')
    app.run(host='0.0.0.0', port=port)
