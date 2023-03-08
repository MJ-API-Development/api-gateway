from starlette.requests import Request

from src.config import config_instance
from CloudFlare import CloudFlare
import ipaddress
import hashlib
import re
from src.make_request import send_request
from src.cache.cache import redis_cache, redis_cached_ttl

EMAIL = config_instance().CLOUDFLARE_SETTINGS.EMAIL
TOKEN = config_instance().CLOUDFLARE_SETTINGS.TOKEN

# Create a middleware function that checks the IP address of incoming requests and only allows requests from the
# Cloudflare IP ranges. Here's an example of how you could do this:
DEFAULT_IPV4 = ['173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22', '103.31.4.0/22', '141.101.64.0/18',
                '108.162.192.0/18', '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22',
                '198.41.128.0/17',
                '162.158.0.0/15', '104.16.0.0/13', '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22']

route_regexes = {
                "all_general_fundamentals": "^/api/v1/fundamental/general$",
                 "annual_or_quarterly_statements_by_stock_code": "^/api/v1/fundamentals/financial-statements/by-term/(20[1-9][0-9]|203[0-3])-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])\.(20[1-9][0-9]|203[0-3])-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])/[a-zA-Z0-9_-]{1,16}/\b(?:annual|quarterly)\b(?<!/)$",
                 "company_financial_statements_by_year": "^/api/v1/fundamentals/financial-statements/exchange-year/[a-zA-Z0-9]{16}/\\d{4}$",
                 "company_fundamental_data_complete": "^/api/v1/fundamental/company/[a-zA-Z0-9]{128}(?<!/)$",
                 "complete_stock_list": "^/api/v1/stocks$",
                 "create_exchange": "^/api/v1/exchange$",
                 "create_stocks_bulk": "^/api/v1/stocks$",
                 "fetch_exchange_list": "^/api/v1/exchanges$",
                 "fetch_listed_companies": "^/api/v1/exchange/listed-companies/[a-zA-Z0-9]{128}(?<!/)$",
                 "fetch_listed_stocks": "^/api/v1/exchange/listed-stocks/[a-zA-Z0-9]{1,16}(?<!/)$",
                 "fetch_listed_stocks_by_exchange_code": "^/api/v1/stocks/exchange/code/[a-zA-Z0-9]{1,16}(?<!/)$",
                 "fetch_listed_stocks_by_exchange_id": "^/api/v1/stocks/exchange/id/[a-zA-Z0-9]{16}(?<!/)$",
                 "fetch_stocks_listed_by_currency": "^/api/v1/stocks/currency/[a-zA-Z0-9]{1,16}(?<!/)$",
                 "fetch_stocks_listed_in_country": "^/api/v1/stocks/country/[a-zA-Z]{1,4}(?<!/)$",
                 "get_annual_balance_sheet": "^/api/v1/fundamentals/quarterly-balance-sheet/(20[1-2][0-9]|203[0-3])-(0[1-9]|1[0-2])-\d{2}/[a-zA-Z0-9]{1,16}(?<!/)$",
                 "get_quarterly_balance_sheet": "^/api/v1/fundamentals/quarterly-balance-sheet/[2-9]\\d{3}-(0[1-9]|1[0-2])-\\d{2}/[a-zA-Z0-9]{1,16}(?<!/)$",
                 "get_all_technical_indicators_in_an_exchange": "^/api/v1/fundamentals/tech-indicators-by-exchange/exchange-code/[a-zA-Z0-9]{1,16}/(20[1-9][0-9]|203[0-3])(?<!/)$",
                 "get_bulk_eod_from_exchange_for_date_range": "^/api/v1/eod/(20[1-9][0-9]|203[0-3])-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])\.(20[1-9][0-9]|203[0-3])-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])/(?=[-_\w]{1,16}$)[-_\w]{1,16}$",
                 "get_companies_analyst_ranks_by_exchange_an_year": "^/api/v1/fundamentals/exchange-analyst-rankings/exchange-code/[a-zA-Z0-9_-]{1,16}/\\d{4}$",
                 "get_company_financial_statements_api": "^/api/v1/fundamentals/financial-statements/company-statement/[a-zA-Z0-9-_]{1,16}/\\d{4}$",
                 "get_company_insider_transaction": "^/api/v1/fundamentals/company-insider-transactions/stock-code/[a-zA-Z0-9-_]{1,16}/\\d{4}$",
                 "get_company_technical_indicators_for_a_year_given_stock_code": "^/api/v1/fundamentals/tech-indicators-by-company/stock-code/[a-zA-Z0-9-_]{1,16}/\\d{4}$",
                 "get_company_valuation_data_for_a_year": "^/api/v1/fundamentals/company-valuations/stock-code/[a-zA-Z0-9]{1,16}/\\d{4}$",
                 "get_contract": "^/api/v1/stocks/contract/[a-zA-Z0-9]{16}(?<!/)$",
                 "get_eod_data_multi_stock": "^/api/v1/eod/\\d{4}-\\d{2}-\\d{2}/[a-zA-Z0-9]{16}(?<!/)$",
                 "get_eod_data_single_stock": "^/api/v1/eod/\\d{4}-\\d{2}-\\d{2}/[a-zA-Z0-9]{16}\\.[a-zA-Z0-9]{16}(?<!/)$",
                 "get_eod_from_to_date_for_stock": "^/api/v1/eod/\\d{4}-\\d{2}-\\d{2}\\.\\d{4}-\\d{2}-\\d{2}/[a-zA-Z0-9]{16}(?<!/)$",
                 "get_exchange_by_code": "^/api/v1/exchange/code/[a-zA-Z0-9]{2,16}(?<!/)$",
                 "get_exchange_by_id": "^/api/v1/exchange/id/[a-zA-Z0-9]{16}(?<!/)$",
                 "get_exchange_with_tickers_by_code": "^/api/v1/exchange/exchange-with-tickers/code/[a-zA-Z0-9]{2,16}(?<!/)$",
                 "get_insider_transactions_from_exchange": "^/api/v1/fundamentals/ex-technical-indicators/exchange-code/[a-zA-Z0-9]{2,16}/\\d{4}(?<!/)$",
                 "get_news": "^/api/v1/news/article/[a-zA-Z0-9]{1,64}(?<!/)$",
                 "get_news_articles_bounded": "^/api/v1/news/articles-bounded/\d{1,2}+$",
                 "get_news_articles_by_date": "^/api/v1/news/articles-by-date/\d{4}-\d{2}-\d{2}(?<!/)$",
                 "get_news_articles_by_publisher": "^/api/v1/news/articles-by-publisher/[a-zA-Z0-9_-]{2,128}(?<!/)$",
                 "get_news_articles_by_ticker": "^/api/v1/news/articles-by-ticker/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "get_stock_by_code": "^/api/v1/stock/code/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "get_stock_option": "^/api/v1/stocks/options/stock/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "get_update_delete_by_fundamental_id_company_details": "^/api/v1/fundamentals/company-details/id/[a-zA-Z0-9_-]{16}(?<!/)$",
                 "get_update_delete_by_id_highlights": "^/api/v1/fundamentals/highlights/id/[a-zA-Z0-9_-]{16}(?<!/)$",
                 "get_update_delete_by_id_postal_address": "^/api/v1/fundamentals/company-address/id/[a-zA-Z0-9_-]{16}(?<!/)$",
                 "get_update_delete_by_stock_code_company_details": "^/api/v1/fundamentals/company-details/stock/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "get_update_delete_by_stock_highlights": "^/api/v1/fundamentals/highlights/stock/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "get_update_delete_by_stock_postal_address": "^/api/v1/fundamentals/company-address/stock/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "get_valuations_for_companies_listed_in_exchange": "^/api/v1/fundamentals/exchange-valuations/exchange-code/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "income_statement_by_filing_date_and_stock_code": "^/api/v1/fundamentals/financial-statements/filing-date-ticker/\d{2}-\d{2}-\d{4}/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "income_statement_by_statement_id": "^/api/v1/fundamentals/financials/income-statements/[a-zA-Z0-9_-]{16}(?<!/)$",
                 "income_statements_by_ticker_and_date_range": "^/api/v1/fundamentals/financial-statements/ticker-date-range/\d{2}-\d{2}-\d{4}.\d{2}-\d{2}-\d{4}/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "most_trending_sentiment_by_stock": "^/api/v1/sentiment/trending/stock/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "stock_trend_setters": "^/api/v1/sentiment/trend-setters/stock/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "stock_tweet_sentiments": "^/api/v1/sentiment/tweet/stock/[a-zA-Z0-9_-]{1,16}(?<!/)$",
                 "open_api": "^/open-api$"
}


class CloudFlareFirewall:
    """
        TODO add more functionality to further enhance the security of our gateway
    """

    def __init__(self):
        self.cloud_flare = CloudFlare(email=EMAIL, token=TOKEN)
        self.cloud_flare.api_from_openapi(url="https://www.eod-stock-api.site/open-api")
        self.ip_ranges = []
        self.bad_addresses = set()
        self.compiled_patterns = [re.compile(_regex) for route, _regex in route_regexes.items()]

    @staticmethod
    async def get_ip_ranges() -> tuple[list[str], list[str]]:
        """
            obtains a list of ip addresses from cloudflare edge servers
        :return:
        """
        _uri = 'https://api.cloudflare.com/client/v4/ips'
        _headers = {'Accept': 'application/json', 'X-Auth-Email': EMAIL}
        response = await send_request(api_url=_uri, headers=_headers)
        ipv4_cidrs = response.get('result', {}).get('ipv4_cidrs', DEFAULT_IPV4)
        ipv6_cidrs = response.get('result', {}).get('ipv6_cidrs', [])

        return ipv4_cidrs, ipv6_cidrs

    @redis_cached_ttl(ttl=60 * 30)
    async def path_matches_known_route(self, request: Request):
        """helps to filter out malicious paths based on regex matching"""
        # NOTE: that at this stage if this request is not a get then its invalid
        path = request.url.path
        return any(pattern.match(path) for pattern in self.compiled_patterns) if request.method.lower() == "get" else False

    @redis_cached_ttl(ttl=60 * 30)
    async def check_ip_range(self, ip):
        """
            This IP Range check only prevents direct server access from an Actual IP Address thereby
            bypassing some of the security measures.

            checks if an ip address falls within range of those found in cloudflare edge servers
        :param ip:
        :return:
        """
        if ip in self.bad_addresses:
            return False
        for ip_range in self.ip_ranges:
            if ipaddress.ip_address(ip) in ipaddress.ip_network(ip_range):
                return True
        self.bad_addresses.add(ip)
        return False

    async def save_bad_addresses_to_redis(self) -> int:
        """
            take a list of bad addresses and save to redis
        :return:
        """
        # This will store the list_of_bad_addresses for 3 hours
        if self.bad_addresses:
            THIRTY_DAYS = 60 * 60 * 24 * 30
            await redis_cache.set(key="list_of_bad_addresses", value=list(self.bad_addresses), ttl=THIRTY_DAYS)
        return len(self.bad_addresses)

    async def restore_bad_addresses_from_redis(self):
        bad_addresses = await redis_cache.get(key="list_of_bad_addresses") or []
        for bad_address in bad_addresses:
            self.bad_addresses.add(bad_address)

    @staticmethod
    async def confirm_signature(signature, request, secret):
        url = request.url
        method = request.method.upper()
        headers = request.headers
        expected_signature = hashlib.sha256(f"{method}{url}{headers}{secret}".encode('UTF-8'))
        return signature == expected_signature

    @staticmethod
    async def sha256(message):
        data = message.encode('utf-8')
        hash_bytes = hashlib.sha256(data).digest()
        hash_hex = hash_bytes.hex()
        return hash_hex

    @staticmethod
    async def create_signature(response, url, secret):
        method = response.method.upper()
        headers = response.headers

        message = f"{method}{url}{headers}{secret}"
        signature = hashlib.sha256(message)

        return signature
