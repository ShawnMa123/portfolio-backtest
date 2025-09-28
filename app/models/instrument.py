from datetime import datetime
from app import db

class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'STOCK', 'ETF', 'INDEX'
    exchange = db.Column(db.String(20), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    sector = db.Column(db.String(100))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'type': self.type,
            'exchange': self.exchange,
            'currency': self.currency,
            'sector': self.sector,
            'description': self.description,
            'is_active': self.is_active
        }