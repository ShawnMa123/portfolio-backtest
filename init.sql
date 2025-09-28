-- 创建数据库扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 插入一些示例投资标的数据
INSERT INTO instruments (symbol, name, type, exchange, currency, sector, description) VALUES
('SPY', 'SPDR S&P 500 ETF Trust', 'ETF', 'NYSE', 'USD', 'Financial', 'Tracks the S&P 500 Index'),
('QQQ', 'Invesco QQQ Trust', 'ETF', 'NASDAQ', 'USD', 'Technology', 'Tracks the NASDAQ-100 Index'),
('VTI', 'Vanguard Total Stock Market ETF', 'ETF', 'NYSE', 'USD', 'Financial', 'Tracks the total U.S. stock market'),
('AAPL', 'Apple Inc.', 'STOCK', 'NASDAQ', 'USD', 'Technology', 'Technology company'),
('MSFT', 'Microsoft Corporation', 'STOCK', 'NASDAQ', 'USD', 'Technology', 'Software and cloud services'),
('GOOGL', 'Alphabet Inc.', 'STOCK', 'NASDAQ', 'USD', 'Technology', 'Internet and technology services'),
('AMZN', 'Amazon.com Inc.', 'STOCK', 'NASDAQ', 'USD', 'Consumer Cyclical', 'E-commerce and cloud services'),
('TSLA', 'Tesla Inc.', 'STOCK', 'NASDAQ', 'USD', 'Consumer Cyclical', 'Electric vehicles and energy storage'),
('NVDA', 'NVIDIA Corporation', 'STOCK', 'NASDAQ', 'USD', 'Technology', 'Graphics processing units and AI chips'),
('META', 'Meta Platforms Inc.', 'STOCK', 'NASDAQ', 'USD', 'Technology', 'Social media and virtual reality')
ON CONFLICT (symbol) DO NOTHING;