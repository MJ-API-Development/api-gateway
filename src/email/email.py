import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.email.templates import EmailTemplate


class Emailer:

    def __init__(self, smtp_server: str, port: int):
        self.server = smtplib.SMTP(smtp_server, port)
        self.server.starttls()

    def create_server(self, smtp_server: str, port: int) -> None:
        """Create a secure SSL/TLS connection to the SMTP server."""
        self.server = smtplib.SMTP(smtp_server, port)
        self.server.starttls()

    def login(self, sender_email: str, password: str):
        """Login to the SMTP server."""
        self.server.login(sender_email, password)

    @staticmethod
    def create_message(sender_email: str, recipient_email: str,
                       subject: str, text: str, html: str) -> MIMEMultipart:
        """Create the message with plain-text and HTML versions."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        msg.attach(part1)
        msg.attach(part2)

        return msg

    def send_email(self, sender_email: str, recipient_email: str, message: MIMEMultipart):
        """Send the email via the SMTP server."""
        self.server.sendmail(sender_email, recipient_email, message.as_string())

    def send_subscription_welcome_email(self, sender_email: str,
                                        recipient_email: str,
                                        client_name: str,
                                        plan_name: str, templates: EmailTemplate = EmailTemplate):
        """Send the subscription welcome email."""
        subject = f"Welcome to our {plan_name} subscription!"
        text = f"Dear {client_name},\n\nThank you for signing up for our {plan_name} subscription!"
        html = templates.subscription_welcome(client_name=client_name, plan_name=plan_name)

        message = self.create_message(sender_email, recipient_email, subject, text, html)
        self.send_email(sender_email, recipient_email, message)

    def send_payment_confirmation_email(self, server: smtplib.SMTP,
                                        sender_email: str,
                                        recipient_email: str,
                                        client_name: str,
                                        plan_name: str,
                                        amount: float, templates: EmailTemplate = EmailTemplate):

        """Send the payment confirmation email."""
        subject = f"Payment confirmation for your {plan_name} subscription"
        text = f"Dear {client_name},\n\nThank you for your payment of {amount} for our {plan_name} subscription."
        html = templates.payment_confirmation(client_name=client_name, plan_name=plan_name, amount=amount)

        message = self.create_message(sender_email, recipient_email, subject, text, html)
        self.send_email(sender_email, recipient_email, message)
