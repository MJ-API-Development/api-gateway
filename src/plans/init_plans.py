"""

"""
from enum import Enum

from src.const import UUID_LEN
from src.plans.plans import Plans
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


def create_plans(plan_name: str):
    """

    :param plan_name:
    :return:
    """
    base_plan = Plans(plan_id=create_id(size=UUID_LEN),
                      plan_name=PlanNames.BASIC,
                      charge_amount=ChargeAmounts.BASIC,
                      description=PlanDescriptions.BASIC,
                      resource_set=PlanResources.BASIC)
