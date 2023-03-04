ONE_DAY = 60 * 60 * 24

resource_paths: dict[str, str] = {

    "stocks.complete": "/api/v1/stocks",
    "stocks.code": "/api/v1/stock/code/",
    "stocks.options": "/api/v1/stocks/options/stock/",
    "stocks.currency": "/api/v1/stocks/currency/",
    "stocks.country": "/api/v1/stocks/country/",
    "options.contracts": "/api/v1/stocks/contract/",

    "eod.all": "/api/v1/eod/",

    "exchange.complete": "/api/v1/exchanges",
    "exchange.companies": "/api/v1/exchange/listed-companies/",
    "exchange.stocks": "/api/v1/exchange/listed-stocks/",
    "exchange.stocks.code": "/api/v1/stocks/exchange/code/",
    "exchange.stocks.id": "/api/v1/stocks/exchange/id/",
    "exchange.code": "/api/v1/exchange/code/",
    "exchange.id": "/api/v1/exchange/id/",
    "exchange.with_tickers.code": "/api/v1/exchange/exchange-with-tickers/code/",

    "financial_statements.balance_sheet.annual": "/api/v1/fundamentals/annual-balance-sheet/",
    "financial_statements.balance_sheet.quarterly": "/api/v1/fundamentals/quarterly-balance-sheet/",
    "financial_statements.company": "/api/v1/fundamentals/financial-statements/company-statement/",
    "financial_statements.stock_code.date": "/api/v1/fundamentals/financial-statements/filing-date-ticker/",
    "financial_statements.income_statement.id": "/api/v1/fundamentals/financials/income-statements/",
    "financial_statements.stock_code.date_range": "/api/v1/fundamentals/financial-statements/ticker-date-range/",
    "financial_statements.term": "/api/v1/fundamentals/financial-statements/by-term",
    "financial_statements.year": "/api/v1/fundamentals/financial-statements/exchange-year/",

    "fundamentals.complete": "/api/v1/fundamental/company/",
    "fundamentals.general": "/api/v1/fundamental/general",
    "fundamentals.analyst_ranks.exchange": "/api/v1/fundamentals/exchange-analyst-rankings/exchange-code/",
    "fundamentals.insider.stock_code": "/api/v1/fundamentals/company-insider-transactions/stock-code/",
    "fundamentals.tech_indicators.stock_code": "/api/v1/fundamentals/tech-indicators-by-company/stock-code/",
    "fundamentals.tech_indicators.exchange_code": "/api/v1/fundamentals/tech-indicators-by-exchange/exchange-code/",
    "fundamentals.valuations.stock_code": "/api/v1/fundamentals/company-valuations/stock-code/",
    "fundamentals.valuations.exchange": "/api/v1/fundamentals/exchange-valuations/exchange-code/",
    "fundamentals.company_details.id": "/api/v1/fundamentals/company-details/id/",
    "fundamentals.company_details.stock_code": "/api/v1/fundamentals/company-details/stock/",
    "fundamentals.highlights.id": "/api/v1/fundamentals/highlights/id/",
    "fundamentals.company_address.id": "/api/v1/fundamentals/company-address/id/",
    "fundamentals.highlights.stock_code": "/api/v1/fundamentals/highlights/stock/",
    "fundamentals.company_address.stock_code": "/api/v1/fundamentals/company-address/stock/",

    "news.article": "/api/v1/news/article/",
    "news.articles.bound": "/api/v1/news/articles-bounded/",
    "news.articles.date": "/api/v1/news/articles-by-date/",
    "news.articles.publisher": "/api/v1/news/articles-by-publisher/",
    "news.articles.stock_code": "/api/v1/news/articles-by-ticker/",

    "social.trend_setters.stock_code": "/api/v1/sentiment/trend-setters/stock/",

    "sentiment_analysis.stock_code": "/api/v1/sentiment/trending/stock/",
    "sentiment_analysis.tweeter.stock_code": "/api/v1/sentiment/tweet/stock/"}


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


async def get_resource_name(path: str) -> str:
    _path = path
    path_dict = path_to_resource()
    while True:
        try:
            resource = path_dict[_path]
            return resource
        except KeyError:
            _path = "/".join(_path.split("/")[:-1])
            if not _path:
                raise KeyError(f"No Resource found for path: {path}")
            _path = f"{_path}/"


resource_name_request_size: dict[str, int] = {

    "stocks.code": 1,
    "stocks.options": 1,
    "stocks.complete": 25,
    "stocks.currency": 25,
    "stocks.country": 25,

    "exchange.code": 1,
    "exchange.id": 1,
    "options.contracts": 5,
    "exchange.with_tickers.code": 15,
    "exchange.complete": 2,
    "exchange.companies": 3,
    "exchange.stocks": 10,
    "exchange.stocks.code": 10,
    "exchange.stocks.id": 10,

    "eod.all": 15,

    "financial_statements.balance_sheet.annual": 15,
    "financial_statements.balance_sheet.quarterly": 15,
    "financial_statements.tech_indicators.exchange_code": 25,
    "financial_statements.term": 25,
    "financial_statements.year": 25,
    "financial_statements.stock_code.date": 25,
    "financial_statements.income_statement.id": 5,
    "financial_statements.stock_code.date_range": 15,  # X result size
    "financial_statements.company": 12,

    "fundamentals.general": 10,
    "fundamentals.complete": 15,
    "fundamentals.analyst_ranks": 25,
    "fundamentals.insider.stock_code": 3,
    "fundamentals.tech_indicators.stock_code": 3,
    "fundamentals.valuations.stock_code": 3,
    "fundamentals.tech-indicators.exchange": 25,
    "fundamentals.company": 12,
    "fundamentals.highlights.id": 3,
    "fundamentals.company_address.id": 1,
    "fundamentals.company_details": 5,
    "fundamentals.highlights.stock_code": 2,
    "fundamentals.company_address.stock_code": 1,
    "fundamentals.valuations.exchange": 25,

    "news.article": 1,
    "news.articles.bound": 1,  # 1 x bound size
    "news.articles.date": 3,
    "news.articles.publisher": 5,
    "news.articles.stock_code": 5,

    "sentiment_analysis.stock_code": 3,  # X result size
    "sentiment_analysis.tweeter.stock_code": 3,  # x result size
    "social.trend_setters.stock_code": 3,  # X result size,
}

# TODO need to create a passive method which will automatically substract the credit
# from plan limit

if __name__ == "__main__":
    print(path_to_resource())
