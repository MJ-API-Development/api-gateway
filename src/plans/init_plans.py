"""

"""
from enum import Enum

from src.apikeys.keys import get_session
from src.const import UUID_LEN
from src.plans.plans import Plans, PlanType
from src.utils.utils import create_id


class PlanNames(Enum):
    BASIC: str = "BASIC"
    PROFESSIONAL: str = "PROFESSIONAL"
    BUSINESS: str = "BUSINESS"
    ENTERPRISE: str = "ENTERPRISE"


class ChargeAmounts(Enum):
    BASIC: int = 0
    PROFESSIONAL: int = 1999
    BUSINESS: int = 4999
    ENTERPRISE: int = 9999


class PlanDescriptions(Enum):
    BASIC: str = "Entry Level plan for development purposes"
    PROFESSIONAL: str = "For a Professional project with modest traffic you can use our professional plan"
    BUSINESS: str = "Preferred plan for a business solutions"
    ENTERPRISE: str = "Enterprise level solution intended for high availability and very low latency"


class PlanResources(Enum):
    BASIC: set[str] = {
        "stocks.code",
        "stocks.options",
        "exchange.complete",
        "exchange.stocks.code",
        "exchange.stocks.id",
        "fundamentals.company_details.stock_code",
        "eod.all",
        "news.articles.stock_code"
    }

    PROFESSIONAL: set[str] = {
        "stocks.code",
        "stocks.options",
        "stocks.currency",
        "stocks.country",

        "options.contracts",

        "eod.all",

        "exchange.complete",
        "exchange.companies",
        "exchange.stocks",
        "exchange.stocks.code",
        "exchange.stocks.id",
        "exchange.code",
        "exchange.id",
        "exchange.with_tickers.code",

        "financial_statements.balance_sheet.annual",
        "financial_statements.balance_sheet.quarterly",
        "financial_statements.stock_code.date",

        "fundamentals.general",
        "fundamentals.company_details.stock_code",
        "fundamentals.company_details.id",
        "fundamentals.analyst_ranks.stock_code",
        "fundamentals.tech_indicators.stock_code",
        "fundamentals.valuations.stock_code",
        "fundamentals.highlights.stock_code",
        "fundamentals.company_address.stock_code",
        "fundamentals.highlights.stock_code",

        "news.article",
        "news.articles.stock_code",

        "sentiment_analysis.stock_code"
    }

    BUSINESS: set[str] = {
        "stocks.complete",
        "stocks.code",
        "stocks.options",
        "stocks.currency",
        "stocks.country",
        "options.contracts",

        "eod.all",

        "exchange.complete",
        "exchange.companies",
        "exchange.stocks",
        "exchange.stocks.code",
        "exchange.stocks.id",
        "exchange.code",
        "exchange.id",
        "exchange.with_tickers.code",

        "financial_statements.balance_sheet.annual",
        "financial_statements.balance_sheet.quarterly",
        "financial_statements.company",
        "financial_statements.stock_code.date",
        "financial_statements.income_statement.id",
        "financial_statements.stock_code.date_range",
        "financial_statements.term",
        "financial_statements.year",

        "fundamentals.complete",
        "fundamentals.general",
        "fundamentals.analyst_ranks.exchange",
        "fundamentals.insider.stock_code",
        "fundamentals.tech_indicators.stock_code",
        "fundamentals.tech_indicators.exchange_code",
        "fundamentals.valuations.stock_code",
        "fundamentals.valuations.exchange",
        "fundamentals.company_details.id",
        "fundamentals.company_details.stock_code",
        "fundamentals.highlights.id",
        "fundamentals.company_address.id",
        "fundamentals.highlights.stock_code",
        "fundamentals.company_address.stock_code",

        "news.article",
        "news.articles.bound",
        "news.articles.date",
        "news.articles.publisher",
        "news.articles.stock_code",

        "social.trend_setters.stock_code",

        "sentiment_analysis.stock_code",
        "sentiment_analysis.tweeter.stock_code"
    }

    ENTERPRISE: set[str] = {
        "stocks.complete",
        "stocks.code",
        "stocks.options",
        "stocks.currency",
        "stocks.country",
        "options.contracts",

        "eod.all",

        "exchange.complete",
        "exchange.companies",
        "exchange.stocks",
        "exchange.stocks.code",
        "exchange.stocks.id",
        "exchange.code",
        "exchange.id",
        "exchange.with_tickers.code",

        "financial_statements.balance_sheet.annual",
        "financial_statements.balance_sheet.quarterly",
        "financial_statements.company",
        "financial_statements.stock_code.date",
        "financial_statements.income_statement.id",
        "financial_statements.stock_code.date_range",
        "financial_statements.term",
        "financial_statements.year",

        "fundamentals.complete",
        "fundamentals.general",
        "fundamentals.analyst_ranks.exchange",
        "fundamentals.insider.stock_code",
        "fundamentals.tech_indicators.stock_code",
        "fundamentals.tech_indicators.exchange_code",
        "fundamentals.valuations.stock_code",
        "fundamentals.valuations.exchange",
        "fundamentals.company_details.id",
        "fundamentals.company_details.stock_code",
        "fundamentals.highlights.id",
        "fundamentals.company_address.id",
        "fundamentals.highlights.stock_code",
        "fundamentals.company_address.stock_code",

        "news.article",
        "news.articles.bound",
        "news.articles.date",
        "news.articles.publisher",
        "news.articles.stock_code",

        "social.trend_setters.stock_code",

        "sentiment_analysis.stock_code",
        "sentiment_analysis.tweeter.stock_code"
    }


class RateLimits(Enum):
    BASIC: tuple[int, int, int] = (60, 500, 0)
    PROFESSIONAL: tuple[int, int, int] = (250, 10_000, 1)
    BUSINESS: tuple[int, int, int] = (500, 25_000, 1)
    ENTERPRISE: tuple[int, int, int] = (750, 50_000, 1)


def create_plans() -> None:
    """
        run once on setup
    :return:
    """

    with get_session()() as session:
        session.add(create_basic())
        session.add(create_professional())
        session.add(create_business())
        session.add(create_enterprise())
        session.commit()

    return None


def create_enterprise() -> Plans:
    return Plans(plan_id=create_id(size=UUID_LEN),
                 plan_name=PlanNames.ENTERPRISE,
                 charge_amount=ChargeAmounts.ENTERPRISE,
                 description=PlanDescriptions.ENTERPRISE,
                 resource_set=PlanResources.ENTERPRISE,
                 rate_limit=RateLimits.ENTERPRISE[0],
                 plan_limit=RateLimits.ENTERPRISE[1],
                 plan_limit_type=PlanType.soft_limit,
                 rate_per_request=RateLimits.ENTERPRISE[2])


def create_business() -> Plans:
    return Plans(plan_id=create_id(size=UUID_LEN),
                 plan_name=PlanNames.BUSINESS,
                 charge_amount=ChargeAmounts.BUSINESS,
                 description=PlanDescriptions.BUSINESS,
                 resource_set=PlanResources.BUSINESS,
                 rate_limit=RateLimits.BUSINESS[0],
                 plan_limit=RateLimits.BUSINESS[1],
                 plan_limit_type=PlanType.soft_limit,
                 rate_per_request=RateLimits.BUSINESS[2])


def create_professional() -> Plans:
    return Plans(plan_id=create_id(size=UUID_LEN),
                 plan_name=PlanNames.PROFESSIONAL,
                 charge_amount=ChargeAmounts.PROFESSIONAL,
                 description=PlanDescriptions.PROFESSIONAL,
                 resource_set=PlanResources.PROFESSIONAL,
                 rate_limit=RateLimits.PROFESSIONAL[0],
                 plan_limit=RateLimits.PROFESSIONAL[1],
                 plan_limit_type=PlanType.soft_limit,
                 rate_per_request=RateLimits.PROFESSIONAL[2])


def create_basic() -> Plans:
    return Plans(plan_id=create_id(size=UUID_LEN),
                 plan_name=PlanNames.BASIC,
                 charge_amount=ChargeAmounts.BASIC,
                 description=PlanDescriptions.BASIC,
                 resource_set=PlanResources.BASIC,
                 rate_limit=RateLimits.BASIC[0],
                 plan_limit=RateLimits.BASIC[1],
                 plan_limit_type=PlanType.hard_limit,
                 rate_per_request=RateLimits.BASIC[2])
