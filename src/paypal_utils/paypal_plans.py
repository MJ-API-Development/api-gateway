import paypalrestsdk
from paypalrestsdk import BillingPlan, BillingAgreement
from src.config import config_instance
from src.database.database_sessions import sessions
from src.database.plans.plans import Plans, Subscriptions

paypal_config = dict(client_id=config_instance().PAYPAL_SETTINGS.CLIENT_ID,
                     client_secret=config_instance().PAYPAL_SETTINGS.CLIENT_SECRET,
                     mode=config_instance().PAYPAL_SETTINGS.MODE)


class PayPalService:
    """
        PayPal Service
    """
    def __init__(self):
        self.paypal_api = paypalrestsdk.configure(paypal_config)
        self.client_plans = self.load_plans()

    @staticmethod
    def load_plans() -> list[Plans]:
        with next(sessions) as session:
            plans_list = Plans.fetch_all(session=session)
        return plans_list

    @staticmethod
    async def create_paypal_billing_plans():
        # Run Once to create PayPal Service - Billing Plans
        with next(sessions) as session:
            plans_list = Plans.fetch_all(session=session)
            for plan in plans_list:
                plan_attr = {
                    "name": plan.plan_name,
                    "description": plan.description,
                    "type": "INFINITE",
                    "payment_definitions": [
                        {
                            "name": "Monthly Payment",
                            "type": "REGULAR",
                            "frequency": "MONTH",
                            "frequency_interval": "1",
                            "amount": {
                                "currency": "USD",
                                "value": f"{plan.charge_amount}"
                            },
                            "cycles": "0",
                            "charge_models": [
                                {
                                    "type": "SHIPPING",
                                    "amount": {
                                        "currency": "USD",
                                        "value": "0.00"
                                    }
                                }
                            ]
                        }
                    ],
                    "merchant_preferences": {
                        "setup_fee": {
                            "currency": "USD",
                            "value": "1.00"
                        },
                        "cancel_url": "https://gateway.eod-stock-api.site/_ipn/paypal/cancel",
                        "return_url": "https://gateway.eod-stock-api.site/_ipn/paypal/success",
                        "auto_bill_amount": "YES",
                        "initial_fail_amount_action": "CONTINUE",
                        "max_fail_attempts": "3"
                    }
                }
                _billing_plan = BillingPlan(plan_attr)
                if _billing_plan.create():
                    plan.paypal_id = _billing_plan.id
                    _billing_plan.activate()
                    # TODO you may need to save billing plans on own database
                    session.merge(plan)
                    session.commit()
            session.flush()

    @staticmethod
    async def create_paypal_billing(plan: Plans, subscription: Subscriptions) -> Subscriptions:
        """
            create user subscription upon user selection on the client website and then send
            the client to the approval url in order to approve the billing
        :param subscription:
        :param plan:
        :return:
        """
        sub_attrs = {
            "name": f"{plan.name} Subscription",
            "description": f"{plan.description}",
            "start_date": f"{subscription.start_date}",
            "payer": {
                "payment_method": "paypal"
            },
            "plan": {
                "id": f"{plan.paypal_id}"
            }
        }
        with next(sessions) as session:
            _subscription = BillingAgreement(sub_attrs)
            if _subscription.create():
                subscription.paypal_id = _subscription.id
                for link in _subscription.links:
                    if link.rel == "approval_url":
                        approval_url = str(link.href)
                subscription.approval_link = approval_url
                session.merge(subscription)
                session.commit()
                session.flush()
        return subscription

        # TODO Redirect client to  approval url


paypal_service = PayPalService()
