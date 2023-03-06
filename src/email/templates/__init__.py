from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('.'))


class EmailTemplate:
    """
        Used to create email templates based on Jinja2 for use in the gateway
    """

    def __init__(self, template=None):
        self.template = env.get_template(template)

    def render(self, **kwargs):
        return self.template.render(**kwargs)

    @staticmethod
    def subscription_welcome(client_name, plan_name):
        template = "subscription_welcome.html"
        return EmailTemplate(template).render(client_name=client_name, plan_name=plan_name)

    @staticmethod
    def payment_confirmation(client_name, plan_name, amount):
        template = "payment_confirmation.html"
        return EmailTemplate(template).render(client_name=client_name, plan_name=plan_name, amount=amount)

    @staticmethod
    def account_confirmation(client_name: str, verification_link: str):
        template = "account_confirmation.html"
        return EmailTemplate(template).render(client_name=client_name, verification_link=verification_link)
