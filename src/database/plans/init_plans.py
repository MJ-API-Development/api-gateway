"""

"""
from dataclasses import field

from numba import jit
from pydantic.dataclasses import dataclass

from src.const import UUID_LEN
from src.database.database_sessions import sessions
from src.database.plans.plans import Plans, PlanType
from src.utils.utils import create_id


@dataclass(frozen=True)
class PlanNames:
    BASIC: str = "BASIC"
    PROFESSIONAL: str = "PROFESSIONAL"
    BUSINESS: str = "BUSINESS"
    ENTERPRISE: str = "ENTERPRISE"


@dataclass(frozen=True)
class ChargeAmounts:
    """
        load this from database in future
    """
    BASIC: int = 0
    PROFESSIONAL: int = 1999
    BUSINESS: int = 4999
    ENTERPRISE: int = 9999


@dataclass(frozen=True)
class PlanDescriptions:
    BASIC: str = "Entry Level plan for development purposes"
    PROFESSIONAL: str = "For a Professional project with modest traffic you can use our professional plan"
    BUSINESS: str = "Preferred plan for a business solutions"
    ENTERPRISE: str = "Enterprise level solution intended for high availability and very low latency"


def get_basic_resources() -> set[str]:
    """
        should have an options of looking into the database to determine if overriding resource parameters
        are not stored
    :return:
    """
    return {
        "stocks.code",
        "stocks.options",
        "exchange.complete",
        "exchange.stocks.code",
        "exchange.stocks.id",
        "fundamentals.company_details.stock_code",
        "eod.all",
        "news.articles.stock_code"
    }


@jit
def get_professional_resources() -> set[str]:
    """
        should add an ability to retrieve professional resources from
        the database
    :return:
    """
    return {
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


@jit
def get_business_resources():
    return {
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


@jit
def get_enterprise_resources():
    return {
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


@dataclass(frozen=True)
class PlanResources:
    BASIC: set[str] = field(default_factory=lambda: get_basic_resources())
    PROFESSIONAL: set[str] = field(default_factory=lambda: get_professional_resources())
    BUSINESS: set[str] = field(default_factory=lambda: get_business_resources())
    ENTERPRISE: set[str] = field(default_factory=lambda: get_enterprise_resources())


@dataclass(frozen=True)
class RateLimits:
    # TODO Propagate the plan limits to the APIModel & Subscriptions
    BASIC: tuple[int, int, int] = (10, 1_500, 0)
    PROFESSIONAL: tuple[int, int, int] = (50, 10_000, 1)
    BUSINESS: tuple[int, int, int] = (75, 25_000, 1)
    ENTERPRISE: tuple[int, int, int] = (125, 50_000, 1)


async def create_plans() -> None:
    """
        run once on setup
    :return:
    """

    with next(sessions) as session:
        session.add(create_basic())
        session.add(create_professional())
        session.add(create_business())
        session.add(create_enterprise())
        session.commit()
        session.flush()

    return None


def create_enterprise() -> Plans:
    rate_limit, plan_limit, rate_per_request = RateLimits().ENTERPRISE
    return Plans(plan_id=create_id(size=UUID_LEN),
                 plan_name=PlanNames().ENTERPRISE,
                 charge_amount=ChargeAmounts().ENTERPRISE,
                 description=PlanDescriptions().ENTERPRISE,
                 resource_set=PlanResources().ENTERPRISE,
                 rate_limit=rate_limit,
                 plan_limit=plan_limit,
                 plan_limit_type=PlanType.soft_limit,
                 rate_per_request=rate_per_request)


def create_business() -> Plans:
    rate_limit, plan_limit, rate_per_request = RateLimits().BUSINESS
    return Plans(plan_id=create_id(size=UUID_LEN),
                 plan_name=PlanNames().BUSINESS,
                 charge_amount=ChargeAmounts().BUSINESS,
                 description=PlanDescriptions().BUSINESS,
                 resource_set=PlanResources().BUSINESS,
                 rate_limit=rate_limit,
                 plan_limit=plan_limit,
                 plan_limit_type=PlanType.soft_limit,
                 rate_per_request=rate_per_request)


def create_professional() -> Plans:
    rate_limit, plan_limit, rate_per_request = RateLimits().PROFESSIONAL
    return Plans(plan_id=create_id(size=UUID_LEN),
                 plan_name=PlanNames().PROFESSIONAL,
                 charge_amount=ChargeAmounts().PROFESSIONAL,
                 description=PlanDescriptions().PROFESSIONAL,
                 resource_set=PlanResources().PROFESSIONAL,
                 rate_limit=rate_limit,
                 plan_limit=plan_limit,
                 plan_limit_type=PlanType.soft_limit,
                 rate_per_request=rate_per_request)


def create_basic() -> Plans:
    rate_limit, plan_limit, rate_per_request = RateLimits().BASIC
    return Plans(plan_id=create_id(size=UUID_LEN),
                 plan_name=PlanNames().BASIC,
                 charge_amount=ChargeAmounts().BASIC,
                 description=PlanDescriptions().BASIC,
                 resource_set=PlanResources().BASIC,
                 rate_limit=rate_limit,
                 plan_limit=plan_limit,
                 rate_per_request=rate_per_request,
                 plan_limit_type=PlanType.hard_limit)
