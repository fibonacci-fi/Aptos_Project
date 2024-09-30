from extensions import socketio, db
from models.aptos_pool import AptosPool
from sqlalchemy import func
import time
from flask_socketio import emit, join_room, leave_room

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'data': 'Connected'})

@socketio.on('subscribe_overall_stats')
def handle_subscribe_overall_stats():
    join_room('overall_stats')
    emit_overall_stats()

@socketio.on('unsubscribe_overall_stats')
def handle_unsubscribe_overall_stats():
    leave_room('overall_stats')

@socketio.on('subscribe_pool')
def handle_subscribe_pool(data):
    pool_address = data['pool_address']
    join_room(pool_address)
    emit_pool_data(pool_address)

@socketio.on('unsubscribe_pool')
def handle_unsubscribe_pool(data):
    pool_address = data['pool_address']
    leave_room(pool_address)

def emit_overall_stats():
    while True:
        data = AptosPool.query.with_entities(
            func.sum(AptosPool.tvl).label('total_tvl'),
            func.sum(AptosPool.volume_day).label('total_volume_day'),
            func.count(AptosPool.pool_address.distinct()).label('total_pools'),
            func.count(AptosPool.provider.distinct()).label('total_providers')
        ).first()

        socketio.emit('overall_stats', {
            'total_tvl': float(data.total_tvl or 0),
            'total_volume_day': float(data.total_volume_day or 0),
            'total_pools': data.total_pools,
            'total_providers': data.total_providers,
            'timestamp': time.time()
        }, room='overall_stats')
        
        socketio.sleep(5)  # Emit data every 5 seconds

def emit_pool_data(pool_address):
    while True:
        pool = AptosPool.query.filter_by(pool_address=pool_address).order_by(AptosPool.timestamp.desc()).first()
        if pool:
            pool_data = {
                'pool_address': pool.pool_address,
                'tvl': float(pool.tvl or 0),
                'volume_day': float(pool.volume_day or 0),
                'fees_day': float(pool.fees_day or 0),
                'timestamp': time.time()
            }
            socketio.emit('pool_update', pool_data, room=pool_address)
        
        socketio.sleep(5)  # Emit data every 5 seconds

@socketio.on_error()
def error_handler(e):
    print(f"An error occurred: {str(e)}")
