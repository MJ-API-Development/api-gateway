import asyncio
from asyncio import Queue
from src.management_api.email.templates import EmailTemplate
from src.config.config import config_instance
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.utils.my_logger import init_logger
from src.utils.utils import camel_to_snake


class Emailer:
    """
        NOTE The Message Queue will send out messages every 5 minutes
        Emailing Class, used to create email servers and manage sending emails
    """
    # TODO create your Own SMTP server to handle emails
    def __init__(self):
        self.email_queues = Queue(maxsize=1024)
        self._dev_messages_queue = Queue(maxsize=100)
        self.server = SendGridAPIClient(config_instance().EMAIL_SETTINGS.SENDGRID_API_KEY)
        self._queue_interval_seconds: int = 60*5
        self._logger = init_logger(camel_to_snake(self.__class__.__name__))

    @staticmethod
    async def create_message(sender_email: str, recipient_email: str,
                             subject: str, html: str) -> Mail:
        """Create the message with plain-text and HTML versions."""
        return Mail(
            from_email=sender_email,
            to_emails=recipient_email,
            subject=subject,
            html_content=html)

    async def send_email(self, message: Mail) -> bool:
        """Send the email via the SMTP server."""
        response = self.server.send(message)
        if response.status_code in [200, 201]:
            self._logger.info(f"Email sent successfully : {message.subject}")
            return True
        return False

    async def put_message_on_queue(self, message: Mail):
        """
            this will put the message to be sent later on a Queue
        :return:
        """
        await self.email_queues.put(message)

    async def process_message_queues(self):
        while True:
            if not self.email_queues.empty():
                message: Mail = await self.email_queues.get()
                self._logger.info(f"Sending Message: Subject {message.subject} , TO : {message.to}")
                await email_process.send_email(message)
            else:
                self._logger.info(f"Email Queue is empty")
            await asyncio.sleep(self._queue_interval_seconds)

    async def send_subscription_welcome_email(self, sender_email: str,
                                              recipient_email: str,
                                              client_name: str,
                                              plan_name: str, templates: EmailTemplate = EmailTemplate):
        """Send the subscription welcome email."""
        subject = f"Welcome to our {plan_name} subscription!"
        html = await templates.subscription_welcome(client_name=client_name, plan_name=plan_name)

        message_dict = dict(sender_email=sender_email, recipient_email=recipient_email,
                            subject=subject, html=html)

        await self.put_message_on_queue(await self.create_message(**message_dict))

    async def send_payment_confirmation_email(self,
                                              sender_email: str,
                                              recipient_email: str,
                                              client_name: str,
                                              plan_name: str,
                                              amount: float, templates: EmailTemplate = EmailTemplate):
        """Send the payment confirmation email."""
        subject = f"Payment confirmation for your {plan_name} subscription"
        html = await templates.payment_confirmation(client_name=client_name, plan_name=plan_name, amount=amount)

        message_dict = dict(sender_email=sender_email, recipient_email=recipient_email,
                            subject=subject, html=html)

        await self.put_message_on_queue(message=await self.create_message(**message_dict))

    async def send_account_confirmation_email(self,
                                              sender_email: str,
                                              recipient_email: str,
                                              client_name: str,
                                              verification_link: str,
                                              templates: EmailTemplate = EmailTemplate):
        subject = f"Account confirmation from EOD-STOCK-API.SITE"
        html = await templates.account_confirmation(client_name=client_name, verification_link=verification_link)
        message_dict = dict(sender_email=sender_email, recipient_email=recipient_email, subject=subject, html=html)
        await self.put_message_on_queue(message=await self.create_message(**message_dict))

    # noinspection PyUnusedLocal
    async def send_message_to_devs(self, message_type: str, request, api_key: str, priority: int = 1,
                                   templates: EmailTemplate = EmailTemplate):
        """

        :param templates:
        :param priority:
        :param request:
        :param message_type:
        :param api_key:
        :return:
        """
        subject = f"Logs from EOD-STOCK-API.SITE : {message_type}"
        _request = dict(url=request.url, headers=request.headers, method=request.method)
        html = await templates.devs_message(**_request)

        message_dict = dict(sender_email="noreply@eod-stock-api.site", recipient_email="support@eod-stock-api.site",
                            subject=subject, html=html)

        await self.put_message_on_queue(message=await self.create_message(**message_dict))

    # noinspection PyUnusedLocal
    async def send_two_factor_code_email(self, email: str, code: str, templates: EmailTemplate = EmailTemplate):
        """
        Send an email with the two-factor code to the specified email address.
        """
        # Use an email library to send email
        # The email should include the code and a message informing the user that they have requested a login
        # You may need to configure your email service provider credentials and settings
        subject: str = f"EOD Stock API - Two Factor Authentication Code"
        message: str = f"""
        
        Hi
            You have recently tried to login to https://eod-stock-api.site 
            here is your two-factor authentication code : {code}
            if you did not try to login please ignore this message
            and nothing will happen.
            
        Thank you
        https://eod-stock-api.site
        Team
        """
        message_dict = dict(sender_email="noreply@eod-stock-api.site", recipient_email=email, subject=subject,
                            html=message)

        await self.put_message_on_queue(message=await self.create_message(**message_dict))


email_process = Emailer()
