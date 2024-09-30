from extensions import db

class AptosPool(db.Model):
    __tablename__ = 'aptos_pools'

    # ... (rest of the model definition remains the same)

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False)
    provider = db.Column(db.String, nullable=False)
    pool_address = db.Column(db.String, nullable=False)
    token_a = db.Column(db.String, nullable=False)
    token_b = db.Column(db.String, nullable=False)
    tvl = db.Column(db.Numeric, nullable=False)
    volume_day = db.Column(db.Numeric, nullable=False)
    volume_week = db.Column(db.Numeric, nullable=False)
    volume_month = db.Column(db.Numeric, nullable=False)
    fees_day = db.Column(db.Numeric, nullable=False)
    fees_week = db.Column(db.Numeric, nullable=False)
    fees_month = db.Column(db.Numeric, nullable=False)
    state = db.Column(db.String, nullable=False)

    # Add the new slippage columns
    median_slippage_1d = db.Column(db.Numeric, nullable=True)
    median_slippage_7d = db.Column(db.Numeric, nullable=True)
    median_slippage_30d = db.Column(db.Numeric, nullable=True)

    def to_dict(self):
        return {
            'id': self.id or 0,
            'timestamp': self.timestamp.isoformat() if self.timestamp else '',
            'provider': self.provider or '',
            'pool_address': self.pool_address or '',
            'token_a': self.token_a or '',
            'token_b': self.token_b or '',
            'tvl': float(self.tvl or 0.0),
            'volume_day': float(self.volume_day or 0.0),
            'volume_week': float(self.volume_week or 0.0),
            'volume_month': float(self.volume_month or 0.0),
            'fees_day': float(self.fees_day or 0.0),
            'fees_week': float(self.fees_week or 0.0),
            'fees_month': float(self.fees_month or 0.0),
            'state': self.state or '',
            'median_slippage_1d': float(self.median_slippage_1d or 0.0),
            'median_slippage_7d': float(self.median_slippage_7d or 0.0),
            'median_slippage_30d': float(self.median_slippage_30d or 0.0),
        }
