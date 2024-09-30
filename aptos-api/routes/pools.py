from flask import Blueprint, jsonify, request
from models.aptos_pool import AptosPool
from extensions import db
import logging
bp = Blueprint('pools', __name__)
from sqlalchemy import func, Integer, Float, and_ 
from datetime import datetime, timedelta, timezone

# Set up a logger for error handling
logger = logging.getLogger(__name__)

@bp.route('/aptos/pool/<pool_address>/current')
def get_pool(pool_address):
    """
    Retrieve the current data for a specific pool.

    Args:
        pool_address (str): The address of the pool to retrieve.

    Returns:
        JSON: A dictionary containing the pool's current data.

    Raises:
        404: If the pool is not found.
        500: If there's an internal server error.
    """
    try:
        # Query to get the latest entry for the given pool_address
        pool = db.session.query(AptosPool).filter_by(pool_address=pool_address).order_by(AptosPool.timestamp.desc()).first_or_404()

        # Convert the pool object to a dictionary and replace None values accordingly
        pool_dict = {
            key: (0 if value is None and isinstance(pool.__table__.c[key].type, (Integer, Float)) else value or '')
            for key, value in pool.to_dict().items()
        }

        return jsonify(pool_dict)
    
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({'error': 'An error occurred while processing the request'}), 500

@bp.route('/aptos/pools')
def get_current_pools():
    """
    Retrieve the current data for all pools.

    Returns:
        JSON: A list of dictionaries, each containing a pool's current data.

    Raises:
        500: If there's an internal server error.
    """
    try:
        # Subquery to get the latest timestamp for each pool
        latest_timestamps = db.session.query(
            AptosPool.pool_address,
            func.max(AptosPool.timestamp).label('max_timestamp')
        ).group_by(AptosPool.pool_address).subquery()

        # Main query to get the latest data for each pool
        query = db.session.query(AptosPool).join(
            latest_timestamps,
            (AptosPool.pool_address == latest_timestamps.c.pool_address) &
            (AptosPool.timestamp == latest_timestamps.c.max_timestamp)
        )

        # Use yield_per for memory efficiency
        pools = query.yield_per(100)

        # Optimize result formatting
        result = [
            {key: (0 if value is None and isinstance(pool.__table__.c[key].type, (db.Integer, db.Float)) 
                   else ('' if value is None else value))
             for key, value in pool.to_dict().items()}
            for pool in pools
        ]

        return jsonify(result)

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while processing the request"}), 500


@bp.route('/aptos/pool/<pool_address>/history')
def get_pool_history(pool_address):
    """
    Retrieve historical data for a specific pool.

    Args:
        pool_address (str): The address of the pool to retrieve history for.

    Query Parameters:
        range (str): The time range for the history. Can be 'day', 'week', or 'month'.

    Returns:
        JSON: A list of dictionaries, each containing the pool's data at a specific timestamp.

    Raises:
        400: If an invalid time range is provided.
        500: If there's an internal server error.
    """
    try:
        # Get the time range parameter
        time_range = request.args.get('range', '1day')
        
        # Calculate the start date based on the time range
        now = datetime.now(timezone.utc)
        if time_range == 'day':
            start_date = now - timedelta(days=1)
        elif time_range == 'week':
            start_date = now - timedelta(weeks=1)
        elif time_range == 'month':
            start_date = now - timedelta(days=30)
        else:
            return jsonify({"error": "Invalid time range. Use 'day', 'week', or 'month'."}), 400

        # Query to get historical data for the specified pool
        query = db.session.query(AptosPool).filter(
            AptosPool.pool_address == pool_address,
            AptosPool.timestamp >= start_date
        ).order_by(AptosPool.timestamp.asc())

        # Use yield_per for memory efficiency
        pool_history = query.yield_per(100)

        # Format the result
        result = []
        for pool in pool_history:
            pool_dict = {
                key: (0 if value is None and isinstance(pool.__table__.c[key].type, (db.Integer, db.Float)) 
                      else ('' if value is None else value))
                for key, value in pool.to_dict().items()
            }
            result.append(pool_dict)

        return jsonify(result)

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while processing the request"}), 500


@bp.route('/top', methods=['GET'])
def get_top_pools():
    """
    Get the top 10 pools based on TVL, volume, or fees, optionally filtered by provider.

    Query Parameters:
        metric (str): The metric to sort by. Can be 'tvl', 'volume_day', or 'fees_day'. Defaults to 'tvl'.
        provider (str): The provider to filter by. If not provided, no filtering is applied.

    Returns:
        JSON: A list of dictionaries, each containing the pool's data.

    Raises:
        400: If an invalid metric is provided.
        500: If there's an internal server error.
    """
    try:
        metric = request.args.get('metric', 'tvl').lower()
        provider = request.args.get('provider')

        if metric not in ['tvl', 'volume_day', 'fees_day']:
            return jsonify({"error": "Invalid metric. Use 'tvl', 'volume_day', or 'fees_day'."}), 400

        # Map the metric to the corresponding database column
        metric_column = {
            'tvl': AptosPool.tvl,
            'volume_day': AptosPool.volume_day,
            'fees_day': AptosPool.fees_day
        }[metric]

        # Query to get the latest data for each pool, sorted by the specified metric
        subquery = db.session.query(
            AptosPool.pool_address,
            func.max(AptosPool.timestamp).label('max_timestamp')
        ).group_by(AptosPool.pool_address).subquery()

        query = db.session.query(AptosPool).join(
            subquery,
            and_(
                AptosPool.pool_address == subquery.c.pool_address,
                AptosPool.timestamp == subquery.c.max_timestamp
            )
        )

        # Apply provider filter if provided
        if provider:
            query = query.filter(AptosPool.provider == provider)

        query = query.order_by(metric_column.desc()).limit(10)

        top_pools = query.all()

        # Format the result
        result = []
        for pool in top_pools:
            pool_dict = {
                key: (0 if value is None and isinstance(pool.__table__.c[key].type, (db.Integer, db.Float)) 
                      else ('' if value is None else value))
                for key, value in pool.to_dict().items()
            }
            result.append(pool_dict)

        return jsonify(result)

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while processing the request"}), 500
