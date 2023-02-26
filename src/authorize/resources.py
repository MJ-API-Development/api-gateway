from src.views_cache.cache import cached

resource_paths: dict[str, str] = {
    "fundamentals.general": "/api/v1/fundamental/general",
    "financial_statements.term": "/api/v1/fundamentals/financial-statements/by-term",
    "financial_statements.year": "/api/v1/fundamentals/financial-statements/exchange-year/",
    "fundamentals.complete": "/api/v1/fundamental/company/",
    "stocks.complete": "/api/v1/stocks",
    "exchange.complete": "/api/v1/exchanges",
    "exchange.companies": "/api/v1/exchange/listed-companies/",
    "exchange.stocks": "/api/v1/exchange/listed-stocks/",
    "exchange.stocks.code": "/api/v1/stocks/exchange/code/",
    "exchange.stocks.id": "/api/v1/stocks/exchange/id/",
    "stocks.currency": "/api/v1/stocks/currency/",
    "stocks.country": "/api/v1/stocks/country/",
    "financial_statements.balance_sheet.annual": "/api/v1/fundamentals/annual-balance-sheet/",
    "financial_statements.balance_sheet.quarterly": "/api/v1/fundamentals/quarterly-balance-sheet/",
    "financial_statements.tech_indicators.exchange_code": "/api/v1/fundamentals/tech-indicators-by-exchange/exchange-code/",
    "eod.all": "/api/v1/eod/",
    "fundamentals.analyst_ranks": "/api/v1/fundamentals/exchange-analyst-rankings/exchange-code/",
    "financial_statements.company": "/api/v1/fundamentals/financial-statements/company-statement/",
    "fundamentals.insider.stock_code": "/api/v1/fundamentals/company-insider-transactions/stock-code/",
    "fundamentals.tech_indicators.stock_code": "/api/v1/fundamentals/tech-indicators-by-company/stock-code/",
    "fundamentals.valuations.stock_code": "/api/v1/fundamentals/company-valuations/stock-code/",
    "options.contracts": "/api/v1/stocks/contract/",
    "exchange.code": "/api/v1/exchange/code/",
    "exchange.id": "/api/v1/exchange/id/",
    "exchange.with_tickers.code": "/api/v1/exchange/exchange-with-tickers/code/",
    "fundamentals.tech-indicators.exchange": "/api/v1/fundamentals/ex-technical-indicators/exchange-code/",
    "news.article": "/api/v1/news/article/",
    "news.articles.bound": "/api/v1/news/articles-bounded/",
    "news.articles.date": "/api/v1/news/articles-by-date/",
    "news.articles.publisher": "/api/v1/news/articles-by-publisher/",
    "news.articles.stock_code": "/api/v1/news/articles-by-ticker/",
    "stocks.code": "/api/v1/stock/code/",
    "stocks.options": "/api/v1/stocks/options/stock/",
    "fundamentals.company": "/api/v1/fundamentals/company-details/id/",
    "fundamentals.highlights.id": "/api/v1/fundamentals/highlights/id/",
    "fundamentals.company_address.id": "/api/v1/fundamentals/company-address/id/",
    "fundamentals.company_details": "/api/v1/fundamentals/company-details/stock/",
    "fundamentals.highlights.stock_code": "/api/v1/fundamentals/highlights/stock/",
    "fundamentals.company_address.stock_code": "/api/v1/fundamentals/company-address/stock/",
    "fundamentals.valuations.exchange": "/api/v1/fundamentals/exchange-valuations/exchange-code/",
    "financial_statements.stock_code.date": "/api/v1/fundamentals/financial-statements/filing-date-ticker/",
    "financial_statements.income_statement.id": "/api/v1/fundamentals/financials/income-statements/",
    "financial_statements.stock_code.date_range": "/api/v1/fundamentals/financial-statements/ticker-date-range/",
    "sentiment_analysis.stock_code": "/api/v1/sentiment/trending/stock/",
    "social.trend_setters.stock_code": "/api/v1/sentiment/trend-setters/stock/",
    "sentiment_analysis.tweeter.stock_code": "/api/v1/sentiment/tweet/stock/"}


@cached
def path_to_resource() -> dict[str, str]:
    """
        reverses the resource to path dictionary
        into a path to resource
    :return:
    """
    _dict = dict()

    for key, value in resource_paths.items():
        _dict.update({value: key})
    return _dict


@cached
async def get_resource_name(path: str) -> str:
    return path_to_resource[path]


if __name__ == "__main__":
    print(path_to_resource())
