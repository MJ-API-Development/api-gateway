import hashlib
import hmac
import ipaddress
import re

from CloudFlare import CloudFlare
from CloudFlare.exceptions import CloudFlareAPIError
from starlette.requests import Request

from src.cache.cache import redis_cache
from src.config import config_instance
from src.make_request import send_request
from src.utils.my_logger import init_logger
from src.utils.utils import camel_to_snake

EMAIL = config_instance().CLOUDFLARE_SETTINGS.EMAIL
TOKEN = config_instance().CLOUDFLARE_SETTINGS.TOKEN

# Create a middleware function that checks the IP address of incoming requests and only allows requests from the
# Cloudflare IP ranges. Here's an example of how you could do this:
DEFAULT_IPV4 = ['173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22', '103.31.4.0/22', '141.101.64.0/18',
                '108.162.192.0/18', '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22',
                '198.41.128.0/17',
                '162.158.0.0/15', '104.16.0.0/13', '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22']


# Patterns for known publicly acceptable routes
route_regexes = {
    "home": "^/$",
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
    "get_news_articles_bounded": "^/api/v1/news/articles-bounded/(?:(?:[1-9]|[1-8][0-9]|9[0-9])(?<!0))$",
    "get_news_articles_by_date": "^/api/v1/news/articles-by-date/\d{4}-\d{2}-\d{2}(?<!/)$",
    "get_news_articles_by_publisher": "^/api/v1/news/articles-by-publisher/[a-zA-Z0-9_-]{2,128}(?<!/)$",
    "get_news_articles_by_ticker": "^/api/v1/news/articles-by-ticker/[a-zA-Z0-9_-]{1,16}(?<!/)$",
    "get_news_articles_by_page": "^/api/v1/news/articles-by-page/[1-9][0-9]?$",
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
    "open_api": "^/open-api$",
    "redoc": "^/redoc$",
    "swagger": "^/swagger$",
}

# Define dictionary of malicious patterns
malicious_patterns = {
    "buffer_overflow": "^\?unix:A{1000,}",  # pattern for buffer overflow attack
    "SQL_injection": "'?([\w\s]+)'?\s*OR\s*'?([\w\s]+)'?\s*=\s*'?([\w\s]+)'?",  # pattern for SQL injection attack
    "SQL_injection_Commands": "\b(ALTER|CREATE|DELETE|DROP|EXEC(UTE){0,1}|INSERT( +INTO){0,1}|MERGE|REPLACE|SELECT|UPDATE)\b", # Match SQL Commands
    "SQL_injection_Comments": "(--|#|\/\*)[\w\d\s]*", # Match SQL Comments
    "SQL_Injection_syntax": "\b(AND|OR)[\s]*[^\s]*=[^\s]*", # Match SQL Injection Syntax
    "SQL_Union_select_attack": "(?i)\bselect\b.*\bfrom\b.*\bunion\b.*\bselect\b", # UNION Select Attack
    "SQL_BLIND_SQL_Injection": "(?i)\b(if|case).*\blike\b.*\bthen\b", # blind SQL Injection attack
    "SQL_TIMEBASED_Injection": "(?i)\b(select|and)\b.*\bsleep\(\d+\)\b", # Time based injection attacks
    "XSS": "<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",  # pattern for cross-site scripting (XSS) attack
    "path_traversal": "\.\.[\\\/]?|\.[\\\/]{2,}",  # pattern for path traversal attack
    # "LDAP_injection": "[()\\\/*\x00-\x1f\x80-\xff]",  # pattern for LDAP injection attack
    "command_injection": ";\s*(?:sh|bash|cmd|powershell)\b",  # pattern for command injection attack
    "file_inclusion": "(?:file|php|zip|glob|data)\s*:",  # pattern for file inclusion attack
    "RCE_attack": "^.*\b(?:eval|assert|exec|system|passthru|popen|proc_open)\b.*$",
    # pattern for remote code execution attack
    "CSRF_attack": "^.*(GET|POST)\s+.*\b(?:referer|origin)\b\s*:\s*(?!https?://(?:localhost|127\.0\.0\.1)).*$",
    # # pattern for cross-site request forgery attack
    "SSRF_attack": "^.*\b(?:curl|wget|file_get_contents|fsockopen|stream_socket_client|socket_create)\b.*$",
    # pattern for server-side request forgery attack
    "CSWSH_attack": "^.*\b(?:Sec-WebSocket-Key|Sec-WebSocket-Accept)\b.*$",
    "BRUTEFORCE_attack": "^.*\b(?:admin|root|test|user|guest)\b.*$",
    "Credential_Stuffing": "(?:\badmin\b|\broot\b|\bpassword\b|\b123456\b|\bqwerty\b|\b123456789\b|\b12345678\b|\b1234567890\b|\b12345\b|\b1234567\b|\b12345678910\b|\b123123\b|\b1234\b|\b111111\b|\babc123\b|\bmonkey\b|\bdragon\b|\bletmein\b|\bsunshine\b|\bprincess\b|\b123456789\b|\bfootball\b|\bcharlie\b|\bshadow\b|\bmichael\b|\bjennifer\b|\bcomputer\b|\bsecurity\b|\btrustno1\b)",
    # "Remote_File_Inclusion": "^.*(include|require)(_once)?\s*\(?\s*[\]\s*(https?:)?//",
    "Clickjacking": '<iframe\s*src="[^"]+"|<iframe\s*src=\'[^\']+\'|\bX-Frame-Options\b\s*:\s*\b(DENY|SAMEORIGIN)\b',
    "XML_External_Entity_Injection": "<!ENTITY[^>]*>",
    "Server_Side_Template_Injection": "\{\{\s*(?:config|app|request|session|env|get|post|server|cookie|_|\|\|)\..+?\}\}",
    "Business_Logic_Attacks": "^\b(?:price|discount|quantity|shipping|coupon|tax|refund|voucher|payment)\b",
    "Javascript_injection": "(?:<\sscript\s>\s*|\blocation\b\s*=|\bwindow\b\s*.\slocation\s=|\bdocument\b\s*.\slocation\s=)",
    "HTML_injection": "<\siframe\s|<\simg\s|<\sobject\s|<\sembed\s",
    # "HTTP_PARAMETER_POLLUTION":  '(?<=^|&)[\w-]+=[^&]*&[\w-]+=',
    "DOM_BASED_XSS": "(?:\blocation\b\s*.\s*(?:hash|search|pathname)|document\s*.\s*(?:location|referrer).hash)"
}


class EODAPIFirewall:
    """
        Attributes:
        -----------
        _max_payload_size: int
            The maximum payload size allowed by CloudFlare API.
        cloud_flare: CloudFlare
            An instance of CloudFlare class to interact with CloudFlare API.
        ip_ranges: list
            A list of IP ranges added to CloudFlare Firewall.
        bad_addresses: set
            A set of IP addresses marked as bad.
        compiled_pat:
            A compiled regex pattern to match IP addresses.
    """

    def __init__(self):
        self._max_payload_size: int = 8 * 64
        try:
            self.cloud_flare = CloudFlare(email=EMAIL, token=TOKEN)
            # self.cloud_flare.api_from_openapi(url="https://www.eod-stock-api.site/open-api")
        except CloudFlareAPIError:
            pass
        self.ip_ranges = []
        self.bad_addresses = set()
        self.compiled_patterns = [re.compile(_regex) for _regex in route_regexes.values()]
        self.compiled_bad_patterns = [re.compile(pattern) for pattern in malicious_patterns.values()]
        self._logger = init_logger(camel_to_snake(self.__class__.__name__))

    @staticmethod
    async def get_client_ip(headers, request):
        """will return the actual client ip address of the client making the request"""
        ip = headers.get('cf-connecting-ip') or headers.get('x-forwarded-for')
        return ip.split(',')[0] if ip else request.remote_addr

    @staticmethod
    async def get_edge_server_ip(headers) -> str:
        """obtains cloudflare edge server the request is being routed through"""
        return headers.get("Host") if headers.get("Host") in ["localhost", "127.0.0.1"] else headers.get("x-real-ip")

    @staticmethod
    async def get_ip_ranges() -> tuple[list[str], list[str]]:
        """
            obtains a list of ip addresses from cloudflare edge servers
        :return:
        """
        _uri = 'https://api.cloudflare.com/client/v4/ips'
        _headers = {'Accept': 'application/json', 'X-Auth-Email': EMAIL}
        try:
            response = await send_request(api_url=_uri, headers=_headers)
            ipv4_cidrs = response.get('result', {}).get('ipv4_cidrs', DEFAULT_IPV4)
            ipv6_cidrs = response.get('result', {}).get('ipv6_cidrs', [])
            return ipv4_cidrs, ipv6_cidrs

        except CloudFlareAPIError:
            return [], []

    async def path_matches_known_route(self, path: str):
        """
        **path_matches_known_route**
            helps to filter out malicious paths based on regex matching
        parameters:
            path: this is the path parameter of the request being requested

        """
        # NOTE: that at this stage if this request is not a get then it has already been rejected
        # NOTE: this will return true if there is at least one route that matches with the requested path.
        # otherwise it will return false and block the request
        return any(pattern.match(path) for pattern in self.compiled_patterns)

    async def is_request_malicious(self, headers: dict[str, str], url: Request.url, body: str | bytes):
        # Check request for malicious patterns
        if 'Content-Length' in headers and int(headers['Content-Length']) > self._max_payload_size:
            # Request payload is too large,
            self.bad_addresses.add(str(url))
            return True

        if body:
            # Set default regex pattern for string-like request bodies
            #  StackOverflow attacks
            payload_regex = "^[A-Za-z0-9+/]{1024,}={0,2}$"
            if re.match(payload_regex, body):
                self.bad_addresses.add(str(url))
                return True

        path = str(url.path)
        return any((pattern.match(path) for pattern in self.compiled_bad_patterns))

    # @redis_cached_ttl(ttl=60 * 30)
    async def check_ip_range(self, ip: str) -> bool:
        """
            This IP Range check only prevents direct server access from an Actual IP Address thereby
            bypassing some of the security measures.

            checks if an ip address falls within range of those found in cloudflare edge servers
        :param ip:
        :return:
        """
        if ip in self.bad_addresses:
            self._logger.info(f"Found in bad addresses range : {ip}")
            return False

        is_valid = any(ipaddress.ip_address(ip) in ipaddress.ip_network(ip_range) for ip_range in self.ip_ranges)
        if not is_valid:
            self.bad_addresses.add(ip)
        self._logger.info(f"is valid became : {is_valid}")
        return is_valid

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
        """
            will retrieve the list of known bad addresses
        :return:
        """
        bad_addresses = await redis_cache.get(key="list_of_bad_addresses") or []
        for bad_address in bad_addresses:
            self.bad_addresses.add(bad_address)

    async def confirm_signature(self, signature, request, secret):
        """
            signature based request authentication works to further enhance gateway secyrity
            by authenticating requests.

            requests without the correct signature will be assumed to be invalid requests and rejected. this ensures
            that by the time requests reaches this gateway they went through other security checks.

            Only our Apps and Cloudflare Edge workers can sign requests.
        """
        url = request.url
        method = request.method.upper()
        headers = request.headers
        message: str = f"{method}{url}{headers}{secret}"
        expected_signature = await self.sha256(message)
        return hmac.compare_digest(signature, expected_signature)

    @staticmethod
    async def sha256(message: str) -> str:
        """
            convert a string to byte
            convert to a digest using sha256 algo from hashlib then return a hex string
        :param message:
        :return:
        """
        return hashlib.sha256(message.encode('utf-8')).digest().hex()

    async def create_signature(self, response, url: str, secret: str) -> str:
        """
            creates a signature based request authentication
        :param response:
        :param url:
        :param secret:
        :return:
        """
        method = response.method.upper()
        headers = response.headers
        message = f"{method}{url}{headers}{secret}"
        return await self.sha256(message)
