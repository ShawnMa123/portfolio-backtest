import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional
from app.models import Portfolio, PortfolioConfiguration, BacktestResult, Transaction, PortfolioHolding, Instrument
from app.services.data_service import DataService
from app import db

class BacktestEngine:
    def __init__(self):
        self.data_service = DataService()

    def run_backtest(self, portfolio_id: int, start_date: str, end_date: str, name: str = None) -> BacktestResult:
        """
        执行投资组合回测
        """
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        # 获取投资组合配置
        configs = PortfolioConfiguration.query.filter_by(
            portfolio_id=portfolio_id,
            is_active=True
        ).all()

        if not configs:
            raise ValueError(f"No active configurations found for portfolio {portfolio_id}")

        # 准备价格数据
        price_data = self._prepare_price_data(configs, start_date, end_date)

        # 执行回测
        backtest_result = self._execute_backtest(portfolio, configs, price_data, start_date, end_date, name)

        return backtest_result

    def _prepare_price_data(self, configs: List[PortfolioConfiguration], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        准备所有标的的价格数据
        """
        price_data = {}

        for config in configs:
            symbol = config.instrument.symbol
            data = self.data_service.get_price_data(symbol, start_date, end_date)

            if data.empty:
                raise ValueError(f"No price data found for {symbol}")

            # 设置日期为索引
            data.set_index('Date', inplace=True)
            price_data[symbol] = data

        return price_data

    def _execute_backtest(self, portfolio: Portfolio, configs: List[PortfolioConfiguration],
                         price_data: Dict[str, pd.DataFrame], start_date: str, end_date: str,
                         name: str = None) -> BacktestResult:
        """
        执行回测核心逻辑
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        # 获取所有交易日期
        all_dates = set()
        for symbol_data in price_data.values():
            all_dates.update(symbol_data.index)

        trading_dates = sorted([d for d in all_dates if start_dt <= d <= end_dt])

        # 初始化
        cash_balance = float(portfolio.initial_capital)
        holdings = {}  # {symbol: {'quantity': float, 'avg_cost': float}}
        daily_values = []
        all_transactions = []
        all_holdings = []

        # 创建回测结果记录
        backtest_result = BacktestResult(
            portfolio_id=portfolio.id,
            name=name or f"Backtest {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            start_date=start_dt,
            end_date=end_dt,
            initial_capital=portfolio.initial_capital,
            final_value=0,  # 稍后计算
            total_return=0,  # 稍后计算
            annualized_return=0,  # 稍后计算
            configuration_snapshot=self._create_config_snapshot(configs)
        )

        db.session.add(backtest_result)
        db.session.flush()  # 获取ID

        # 遍历每个交易日
        for current_date in trading_dates:
            # 执行买入策略
            new_transactions, cash_balance = self._execute_buy_strategy(
                configs, current_date, price_data, cash_balance, portfolio.id, backtest_result.id
            )

            all_transactions.extend(new_transactions)

            # 更新持仓
            self._update_holdings(holdings, new_transactions, price_data, current_date)

            # 计算当日组合价值
            portfolio_value = self._calculate_portfolio_value(holdings, price_data, current_date, cash_balance)

            daily_values.append({
                'date': current_date.isoformat(),
                'portfolio_value': portfolio_value,
                'cash_balance': cash_balance,
                'invested_amount': portfolio_value - cash_balance
            })

            # 记录当日持仓
            daily_holdings = self._create_daily_holdings(
                holdings, price_data, current_date, portfolio.id, backtest_result.id, portfolio_value
            )
            all_holdings.extend(daily_holdings)

        # 计算绩效指标
        metrics = self._calculate_performance_metrics(daily_values, all_transactions, float(portfolio.initial_capital))

        # 更新回测结果
        backtest_result.final_value = daily_values[-1]['portfolio_value'] if daily_values else float(portfolio.initial_capital)
        backtest_result.total_return = metrics['total_return']
        backtest_result.annualized_return = metrics['annualized_return']
        backtest_result.max_drawdown = metrics['max_drawdown']
        backtest_result.sharpe_ratio = metrics['sharpe_ratio']
        backtest_result.volatility = metrics['volatility']
        backtest_result.total_trades = len(all_transactions)
        backtest_result.total_fees = sum(t['fee'] for t in all_transactions)
        backtest_result.result_data = {'daily_values': daily_values, 'metrics': metrics}

        # 保存所有数据
        db.session.commit()

        # 批量插入交易记录
        for trans_data in all_transactions:
            transaction = Transaction(**trans_data)
            db.session.add(transaction)

        # 批量插入持仓记录
        for holding_data in all_holdings:
            holding = PortfolioHolding(**holding_data)
            db.session.add(holding)

        db.session.commit()

        return backtest_result

    def _execute_buy_strategy(self, configs: List[PortfolioConfiguration], current_date: date,
                             price_data: Dict[str, pd.DataFrame], cash_balance: float,
                             portfolio_id: int, backtest_result_id: int) -> Tuple[List[Dict], float]:
        """
        执行买入策略
        """
        transactions = []

        for config in configs:
            if self._should_buy_today(config, current_date):
                symbol = config.instrument.symbol

                if current_date not in price_data[symbol].index:
                    continue

                current_price = float(price_data[symbol].loc[current_date, 'adj_close'])

                if config.buy_type == 'AMOUNT':
                    buy_amount = float(config.buy_amount)
                    quantity = buy_amount / current_price
                else:
                    quantity = float(config.buy_quantity)
                    buy_amount = quantity * current_price

                # 计算手续费
                fee = buy_amount * float(config.transaction_fee_rate)
                total_cost = buy_amount + fee

                if cash_balance >= total_cost:
                    transaction_data = {
                        'portfolio_id': portfolio_id,
                        'instrument_id': config.instrument_id,
                        'backtest_result_id': backtest_result_id,
                        'transaction_date': current_date,
                        'transaction_type': 'BUY',
                        'quantity': Decimal(str(quantity)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
                        'price': Decimal(str(current_price)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
                        'fee': Decimal(str(fee)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
                        'total_amount': Decimal(str(buy_amount)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
                    }

                    transactions.append(transaction_data)
                    cash_balance -= total_cost

        return transactions, cash_balance

    def _should_buy_today(self, config: PortfolioConfiguration, current_date: date) -> bool:
        """
        判断今天是否应该买入
        """
        if current_date < config.start_date:
            return False

        if config.end_date and current_date > config.end_date:
            return False

        if config.investment_frequency == 'DAILY':
            return True
        elif config.investment_frequency == 'WEEKLY':
            target_weekday = config.frequency_detail.get('weekday', 0) if config.frequency_detail else 0
            return current_date.weekday() == target_weekday
        elif config.investment_frequency == 'MONTHLY':
            target_day = config.frequency_detail.get('day', 1) if config.frequency_detail else 1
            return current_date.day == target_day

        return False

    def _update_holdings(self, holdings: Dict, transactions: List[Dict],
                        price_data: Dict[str, pd.DataFrame], current_date: date):
        """
        更新持仓记录
        """
        for trans in transactions:
            instrument_id = trans['instrument_id']
            symbol = None

            # 找到对应的symbol
            for config_symbol, data in price_data.items():
                instrument = Instrument.query.filter_by(symbol=config_symbol).first()
                if instrument and instrument.id == instrument_id:
                    symbol = config_symbol
                    break

            if symbol is None:
                continue

            if symbol not in holdings:
                holdings[symbol] = {'quantity': 0, 'total_cost': 0}

            # 更新持仓数量和平均成本
            old_quantity = holdings[symbol]['quantity']
            old_total_cost = holdings[symbol]['total_cost']

            new_quantity = old_quantity + float(trans['quantity'])
            new_total_cost = old_total_cost + float(trans['total_amount'])

            holdings[symbol]['quantity'] = new_quantity
            holdings[symbol]['total_cost'] = new_total_cost

            if new_quantity > 0:
                holdings[symbol]['avg_cost'] = new_total_cost / new_quantity

    def _calculate_portfolio_value(self, holdings: Dict, price_data: Dict[str, pd.DataFrame],
                                  current_date: date, cash_balance: float) -> float:
        """
        计算投资组合总价值
        """
        total_value = cash_balance

        for symbol, holding in holdings.items():
            if holding['quantity'] > 0 and current_date in price_data[symbol].index:
                current_price = float(price_data[symbol].loc[current_date, 'adj_close'])
                market_value = holding['quantity'] * current_price
                total_value += market_value

        return total_value

    def _create_daily_holdings(self, holdings: Dict, price_data: Dict[str, pd.DataFrame],
                              current_date: date, portfolio_id: int, backtest_result_id: int,
                              total_portfolio_value: float) -> List[Dict]:
        """
        创建当日持仓记录
        """
        daily_holdings = []

        for symbol, holding in holdings.items():
            if holding['quantity'] > 0:
                # 获取instrument_id
                instrument = Instrument.query.filter_by(symbol=symbol).first()
                if not instrument:
                    continue

                if current_date in price_data[symbol].index:
                    current_price = float(price_data[symbol].loc[current_date, 'adj_close'])
                    market_value = holding['quantity'] * current_price
                    unrealized_pnl = market_value - holding['total_cost']
                    weight = market_value / total_portfolio_value if total_portfolio_value > 0 else 0

                    holding_data = {
                        'portfolio_id': portfolio_id,
                        'instrument_id': instrument.id,
                        'backtest_result_id': backtest_result_id,
                        'holding_date': current_date,
                        'quantity': Decimal(str(holding['quantity'])).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
                        'average_cost': Decimal(str(holding['avg_cost'])).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
                        'market_value': Decimal(str(market_value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                        'unrealized_pnl': Decimal(str(unrealized_pnl)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                        'weight': Decimal(str(weight)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                    }

                    daily_holdings.append(holding_data)

        return daily_holdings

    def _calculate_performance_metrics(self, daily_values: List[Dict], transactions: List[Dict],
                                      initial_capital: float) -> Dict:
        """
        计算绩效指标
        """
        if not daily_values:
            return {}

        values = [d['portfolio_value'] for d in daily_values]
        returns = pd.Series(values).pct_change().dropna()

        final_value = values[-1]
        total_return = (final_value - initial_capital) / initial_capital

        # 年化收益率
        days = len(values)
        years = days / 252  # 假设一年252个交易日
        annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0

        # 最大回撤
        peak = pd.Series(values).expanding().max()
        drawdown = (pd.Series(values) - peak) / peak
        max_drawdown = drawdown.min()

        # 波动率
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0

        # 夏普比率 (假设无风险利率为0)
        sharpe_ratio = returns.mean() * np.sqrt(252) / volatility if volatility > 0 else 0

        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(transactions),
            'total_fees': sum(float(t['fee']) for t in transactions)
        }

    def _create_config_snapshot(self, configs: List[PortfolioConfiguration]) -> Dict:
        """
        创建配置快照
        """
        return {
            'configurations': [config.to_dict() for config in configs],
            'snapshot_time': datetime.now().isoformat()
        }