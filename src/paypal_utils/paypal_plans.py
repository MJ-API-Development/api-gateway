

import paypalrestsdk
from paypalrestsdk.openid_connect import client_secret

from src.config import config_instance
from src.database.database_sessions import sessions, sessionType
from src.database.plans.plans import Plans, Subscriptions

paypal_config = dict( client_id=config_instance().PAYPAL_SERVICE.CLIENT_ID,
                      client_secret=config_instance().PAYPAL_SERVICE.CLIENT_ID,
                      mode= config_instance().PAYPAL_SERVICE.MODE)

class PayPalService:
    def __init__(self):
        self.paypal_api = paypalrestsdk.configure(paypal_config).Api()
        self.client_plans = self.load_plans()

    @staticmethod
    def load_plans() -> list[Plans]:
        with next(sessions) as session:
            plans_list = Plans.fetch_all(session=session)
        return plans_list

    def create_paypal_billing_plans(self):
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
                                    "value": f"{plan.charge_amount / 100}"
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
                _billing_plan = self.paypal_api.BillingPlan(plan_attr)
                if _billing_plan.create():
                    plan.paypal_id =_billing_plan.id
                    _billing_plan.activate()
                    # TODO you may need to save billing plans on own database
                    session.merge(plan)
                    session.commit()
            session.flush()


    def use_paypal_subscriptions(self, plan: Plans, subscription: Subscriptions):
        """

        :param plan_id: plan_id to subscribe to in paypal
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
            _subscription = self.paypal_api.Subscription(sub_attrs)
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
