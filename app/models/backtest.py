from datetime import datetime
from decimal import Decimal
from app import db

class BacktestResult(db.Model):
    __tablename__ = 'backtest_results'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    initial_capital = db.Column(db.Numeric(15, 2), nullable=False)
    final_value = db.Column(db.Numeric(15, 2), nullable=False)
    total_return = db.Column(db.Numeric(10, 6), nullable=False)
    annualized_return = db.Column(db.Numeric(10, 6), nullable=False)
    max_drawdown = db.Column(db.Numeric(10, 6))
    sharpe_ratio = db.Column(db.Numeric(10, 6))
    volatility = db.Column(db.Numeric(10, 6))
    total_trades = db.Column(db.Integer, default=0)
    total_fees = db.Column(db.Numeric(15, 2), default=0)
    result_data = db.Column(db.JSON)  # 详细的每日净值数据
    configuration_snapshot = db.Column(db.JSON)  # 回测时的配置快照
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    transactions = db.relationship('Transaction', backref='backtest_result', lazy=True, cascade='all, delete-orphan')
    holdings = db.relationship('PortfolioHolding', backref='backtest_result', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': float(self.initial_capital),
            'final_value': float(self.final_value),
            'total_return': float(self.total_return),
            'annualized_return': float(self.annualized_return),
            'max_drawdown': float(self.max_drawdown) if self.max_drawdown else None,
            'sharpe_ratio': float(self.sharpe_ratio) if self.sharpe_ratio else None,
            'volatility': float(self.volatility) if self.volatility else None,
            'total_trades': self.total_trades,
            'total_fees': float(self.total_fees),
            'result_data': self.result_data,
            'configuration_snapshot': self.configuration_snapshot,
            'created_at': self.created_at.isoformat()
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    backtest_result_id = db.Column(db.Integer, db.ForeignKey('backtest_results.id'))
    transaction_date = db.Column(db.Date, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'BUY', 'SELL'
    quantity = db.Column(db.Numeric(15, 6), nullable=False)  # 支持碎股
    price = db.Column(db.Numeric(15, 6), nullable=False)
    fee = db.Column(db.Numeric(15, 6), default=0)
    total_amount = db.Column(db.Numeric(15, 6), nullable=False)
    exchange_rate = db.Column(db.Numeric(10, 6), default=Decimal('1.0'))  # 汇率
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    instrument = db.relationship('Instrument', backref='transactions')

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'instrument_id': self.instrument_id,
            'instrument': self.instrument.to_dict() if self.instrument else None,
            'backtest_result_id': self.backtest_result_id,
            'transaction_date': self.transaction_date.isoformat(),
            'transaction_type': self.transaction_type,
            'quantity': float(self.quantity),
            'price': float(self.price),
            'fee': float(self.fee),
            'total_amount': float(self.total_amount),
            'exchange_rate': float(self.exchange_rate),
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }

class PortfolioHolding(db.Model):
    __tablename__ = 'portfolio_holdings'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    backtest_result_id = db.Column(db.Integer, db.ForeignKey('backtest_results.id'))
    holding_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Numeric(15, 6), nullable=False)
    average_cost = db.Column(db.Numeric(15, 6), nullable=False)
    market_value = db.Column(db.Numeric(15, 2), nullable=False)
    unrealized_pnl = db.Column(db.Numeric(15, 2))
    weight = db.Column(db.Numeric(5, 4))  # 在组合中的权重
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    instrument = db.relationship('Instrument', backref='holdings')

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('portfolio_id', 'instrument_id', 'backtest_result_id', 'holding_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'instrument_id': self.instrument_id,
            'instrument': self.instrument.to_dict() if self.instrument else None,
            'backtest_result_id': self.backtest_result_id,
            'holding_date': self.holding_date.isoformat(),
            'quantity': float(self.quantity),
            'average_cost': float(self.average_cost),
            'market_value': float(self.market_value),
            'unrealized_pnl': float(self.unrealized_pnl) if self.unrealized_pnl else None,
            'weight': float(self.weight) if self.weight else None,
            'created_at': self.created_at.isoformat()
        }