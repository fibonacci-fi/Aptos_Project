from flask import Blueprint, jsonify
from models.aptos_pool import AptosPool
from sqlalchemy import func
from extensions import db
import logging
from datetime import datetime, timezone
bp = Blueprint('providers', __name__)

# Set up a logger for error handling
logger = logging.getLogger(__name__)

@bp.route('/aptos/providers')
@bp.route('/aptos/providers/<provider_name>')
def get_providers(provider_name=None):
    """
    Retrieve provider information from the AptosPool database.

    This function queries the AptosPool database to get the latest data for each pool,
    aggregates the data by provider, and returns summary statistics for each provider.

    Args:
        provider_name (str, optional): If provided, filters the results to show data
                                       for only the specified provider.

    Returns:
        A JSON response containing a timestamp and a list of dictionaries, where each dictionary
        represents a provider and includes the following information:
        - provider: The name of the provider
        - total_tvl: Total TVL (Total Value Locked) for the provider
        - total_volume_1d: Total trading volume for the provider in the last day
        - total_volume_7d: Total trading volume for the provider in the last week
        - total_volume_30d: Total trading volume for the provider in the last month
        - avg_fees_1d: Average fees collected by the provider in the last day
        - avg_fees_7d: Average fees collected by the provider in the last week
        - avg_fees_30d: Average fees collected by the provider in the last month
        - total_pools: Total number of pools operated by the provider
        - avg_tvl_per_pool: Average TVL per pool for the provider
        - avg_slippage_1d: Average slippage for the provider in the last day
        - avg_slippage_7d: Average slippage for the provider in the last week
        - avg_slippage_30d: Average slippage for the provider in the last month

    Raises:
        500 Internal Server Error: If an exception occurs during the database query
                                   or data processing.
    """
    try:
        # Subquery to get the latest timestamp for each pool
        latest_timestamps = db.session.query(
            AptosPool.pool_address,
            func.max(AptosPool.timestamp).label('max_timestamp')
        ).group_by(AptosPool.pool_address).subquery()

        # Main query to get the latest data for each pool and aggregate by provider
        query = db.session.query(
            AptosPool.provider,
            func.sum(AptosPool.tvl).label('total_tvl'),
            func.sum(AptosPool.volume_day).label('total_volume_1d'),
            func.sum(AptosPool.volume_week).label('total_volume_7d'),
            func.sum(AptosPool.volume_month).label('total_volume_30d'),
            func.avg(AptosPool.fees_day).label('avg_fees_1d'),
            func.avg(AptosPool.fees_week).label('avg_fees_7d'),
            func.avg(AptosPool.fees_month).label('avg_fees_30d'),
            func.count(AptosPool.pool_address).label('total_pools'),
            (func.sum(AptosPool.tvl) / func.count(AptosPool.pool_address)).label('avg_tvl_per_pool'),
            func.avg(AptosPool.median_slippage_1d).label('avg_slippage_1d'),
            func.avg(AptosPool.median_slippage_7d).label('avg_slippage_7d'),
            func.avg(AptosPool.median_slippage_30d).label('avg_slippage_30d')
        ).join( 
            latest_timestamps,
            (AptosPool.pool_address == latest_timestamps.c.pool_address) &
            (AptosPool.timestamp == latest_timestamps.c.max_timestamp)
        )

        # Apply the provider_name filter directly in the query if provided
        if provider_name:
            query = query.filter(AptosPool.provider == provider_name)

        # Group by provider after filtering
        query = query.group_by(AptosPool.provider)

        # Use yield_per to optimize memory usage for large datasets
        providers = query.yield_per(100).all()

        # Get current UTC timestamp
        current_timestamp = datetime.now(timezone.utc).isoformat()

        # Format the result, handle None values by replacing them with 0
        result = {
            'timestamp': current_timestamp,
            'providers': [{
                'provider': provider,
                'total_tvl': round(float(total_tvl or 0), 2),
                'total_volume_1d': round(float(total_volume_1d or 0), 2),
                'total_volume_7d': round(float(total_volume_7d or 0), 2),
                'total_volume_30d': round(float(total_volume_30d or 0), 2),
                'avg_fees_1d': round(float(avg_fees_1d or 0), 2),
                'avg_fees_7d': round(float(avg_fees_7d or 0), 2),
                'avg_fees_30d': round(float(avg_fees_30d or 0), 2),
                'total_pools': total_pools,
                'avg_tvl_per_pool': round(float(avg_tvl_per_pool or 0), 2),
                'avg_slippage_1d': round(float(avg_slippage_1d or 0), 2),
                'avg_slippage_7d': round(float(avg_slippage_7d or 0), 2),
                'avg_slippage_30d': round(float(avg_slippage_30d or 0), 2)
            } for provider, total_tvl, total_volume_1d, total_volume_7d, total_volume_30d, avg_fees_1d, avg_fees_7d, avg_fees_30d, total_pools, avg_tvl_per_pool, avg_slippage_1d, avg_slippage_7d, avg_slippage_30d in providers]
        }

        return jsonify(result)
    
    except Exception as e:
        # Log the error for better debugging
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while processing the request"}), 500
