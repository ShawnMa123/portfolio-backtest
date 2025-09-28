from datetime import datetime
from decimal import Decimal
from app import db

class Portfolio(db.Model):
    __tablename__ = 'portfolios'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    initial_capital = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(20), default='ACTIVE')  # 'ACTIVE', 'PAUSED', 'ARCHIVED'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    configurations = db.relationship('PortfolioConfiguration', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    backtest_results = db.relationship('BacktestResult', backref='portfolio', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'initial_capital': float(self.initial_capital),
            'currency': self.currency,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class PortfolioConfiguration(db.Model):
    __tablename__ = 'portfolio_configurations'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    weight = db.Column(db.Numeric(5, 4))  # 权重 (0-1)
    investment_frequency = db.Column(db.String(20), nullable=False)  # 'DAILY', 'WEEKLY', 'MONTHLY', 'CUSTOM'
    frequency_detail = db.Column(db.JSON)  # 详细频率配置
    transaction_fee_rate = db.Column(db.Numeric(10, 6), default=Decimal('0.0003'))
    buy_type = db.Column(db.String(20), nullable=False)  # 'AMOUNT', 'QUANTITY'
    buy_amount = db.Column(db.Numeric(15, 2))  # 固定金额买入
    buy_quantity = db.Column(db.Integer)  # 固定数量买入
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instrument = db.relationship('Instrument', backref='portfolio_configurations')

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'instrument_id': self.instrument_id,
            'instrument': self.instrument.to_dict() if self.instrument else None,
            'weight': float(self.weight) if self.weight else None,
            'investment_frequency': self.investment_frequency,
            'frequency_detail': self.frequency_detail,
            'transaction_fee_rate': float(self.transaction_fee_rate),
            'buy_type': self.buy_type,
            'buy_amount': float(self.buy_amount) if self.buy_amount else None,
            'buy_quantity': self.buy_quantity,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active
        }