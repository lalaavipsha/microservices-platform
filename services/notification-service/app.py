from flask import Flask, jsonify, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger
import logging
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

REQUEST_COUNT = Counter('notification_service_requests_total', 'Total requests', ['method', 'endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('notification_service_request_duration_seconds', 'Latency', ['method', 'endpoint'])
NOTIFICATIONS_SENT = Counter('notification_service_notifications_total', 'Notifications sent', ['type', 'status'])

NOTIFICATIONS_DB = {}

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
    return jsonify({'status': 'healthy', 'service': 'notification-service', 'timestamp': time.time()})

@app.route('/ready', methods=['GET'])
def ready():
    return jsonify({'status': 'ready'})

@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/api/v1/notifications', methods=['POST'])
def send_notification():
    try:
        data = request.json
        if not data or 'type' not in data or 'recipient' not in data:
            return jsonify({'error': 'Type and recipient required'}), 400
        notification_type = data['type']
        recipient = data['recipient']
        notification_id = str(uuid.uuid4())
        time.sleep(0.05)
        notification = {
            'notification_id': notification_id,
            'type': notification_type,
            'recipient': recipient,
            'status': 'sent',
            'created_at': time.time()
        }
        NOTIFICATIONS_DB[notification_id] = notification
        NOTIFICATIONS_SENT.labels(type=notification_type, status='sent').inc()
        logger.info(f'Notification sent: {notification_id} type={notification_type}')
        return jsonify({'message': 'Notification sent', 'notification': notification}), 201
    except Exception as e:
        logger.error(f'Error sending notification: {str(e)}')
        return jsonify({'error': 'Failed to send notification'}), 500

@app.route('/api/v1/notifications/<notification_id>', methods=['GET'])
def get_notification(notification_id):
    notification = NOTIFICATIONS_DB.get(notification_id)
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    return jsonify(notification)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8084))
    logger.info(f'Starting Notification Service on port {port}')
    app.run(host='0.0.0.0', port=port)
