

def create_tables():
    from src.database.apikeys.keys import ApiKeyModel, Account
    from src.database.plans.plans import Subscriptions, Plans, Payments, Invoices
    ApiKeyModel.create_if_not_exists()
    Account.create_if_not_exists()
    Subscriptions.create_if_not_exists()
    Plans.create_if_not_exists()
    Payments.create_if_not_exists()
    Invoices.create_if_not_exists()
