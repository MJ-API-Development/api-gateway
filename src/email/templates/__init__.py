from jinja2 import Template


class EmailTemplate:
    def __init__(self, template=None):
        self.template = Template(template)

    def render(self, **kwargs):
        return self.template.render(**kwargs)

    @staticmethod
    def subscription_welcome(client_name, plan_name):
        template = """
        <html>
          <head></head>
          <body>
            <p>Dear {{ client_name }},<br><br>
               Thank you for signing up for our {{ plan_name }} subscription!<br><br>
               We're excited to have you on board and can't wait to provide you with our top-notch services.<br><br>
               If you have any questions or concerns, please don't hesitate to contact us at support@eod-stock-api.site.<br><br>
               Best regards,<br>
               https://eod-stock-api.site
            </p>
          </body>
        </html>
        """
        return EmailTemplate(template).render(client_name=client_name, plan_name=plan_name)

    @staticmethod
    def payment_confirmation(client_name, plan_name, amount):
        template = """
        <html>
          <head></head>
          <body>
            <p>Dear {{ client_name }},<br><br>
               Thank you for your payment of {{ amount }} for our {{ plan_name }} subscription.<br><br>
               Your payment has been successfully processed and your subscription is now active.<br><br> 
               If you have any questions or concerns, please don't hesitate to contact us at support@eod-stock-api.site .<br><br> 
               Best regards,<br>
               https://eod-stock-api.site
            </p>
          </body>
        </html>
        """

        return EmailTemplate(template).render(client_name=client_name, plan_name=plan_name, amount=amount)


# Usage
subscription_welcome = EmailTemplate.subscription_welcome('John', 'Premium')
payment_confirmation = EmailTemplate.payment_confirmation('John', 'Premium', 99.99)
