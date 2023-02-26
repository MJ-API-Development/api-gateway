# Prefetch endpoints
PREFETCH_ENDPOINTS = [
    '/api/v1/exchanges',
    '/api/v1/stocks',
    '/api/v1/fundamental/general']


def build_dynamic_urls():
    """

    :return:
    """
    endpoints_urls = [
        '/api/v1/exchange/listed-stocks/{exchange_code}',
        '/api/v1/stocks/exchange/code/{exchange_code}',
        '/api/v1/stocks/exchange/id/{exchange_id}',
        '/api/v1/stocks/currency/{currency}',
        '/api/v1/stocks/country/{country}']

    expanded_urls = []
    return PREFETCH_ENDPOINTS
