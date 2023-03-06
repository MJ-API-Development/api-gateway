from src.email.templates import EmailTemplate
from src.config.config import config_instance
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class Emailer:
    """
        Emailing Class, used to create email servers and manage sending emails
    """
    def __init__(self):
        self.server = SendGridAPIClient(config_instance().EMAIL_SETTINGS.SENDGRID_API_KEY)

    @staticmethod
    def create_message(sender_email: str, recipient_email: str,
                       subject: str, html: str) -> Mail:
        """Create the message with plain-text and HTML versions."""
        return Mail(
            from_email=sender_email,
            to_emails=recipient_email,
            subject=subject,
            html_content=html)

    def send_email(self, message: Mail) -> bool:
        """Send the email via the SMTP server."""
        response = self.server.send(message)
        if response.status_code in [200, 201]:
            return True
        return False

    def send_subscription_welcome_email(self, sender_email: str,
                                        recipient_email: str,
                                        client_name: str,
                                        plan_name: str, templates: EmailTemplate = EmailTemplate):
        """Send the subscription welcome email."""
        subject = f"Welcome to our {plan_name} subscription!"
        text = f"Dear {client_name},\n\nThank you for signing up for our {plan_name} subscription!"
        html = templates.subscription_welcome(client_name=client_name, plan_name=plan_name)

        message_dict = dict(sender_email=sender_email, recipient_email=recipient_email,
                            subject=subject, html=html)
        self.send_email(self.create_message(**message_dict))

    def send_payment_confirmation_email(self,
                                        sender_email: str,
                                        recipient_email: str,
                                        client_name: str,
                                        plan_name: str,
                                        amount: float, templates: EmailTemplate = EmailTemplate):
        """Send the payment confirmation email."""
        subject = f"Payment confirmation for your {plan_name} subscription"
        html = templates.payment_confirmation(client_name=client_name, plan_name=plan_name, amount=amount)

        message_dict = dict(sender_email=sender_email, recipient_email=recipient_email,
                            subject=subject, html=html)
        self.send_email(self.create_message(**message_dict))


email_process = Emailer()


async def process_send_subscription_welcome_email():
    """

    :return:
    """
    pass


async def process_send_payment_confirmation_email():
    pass
