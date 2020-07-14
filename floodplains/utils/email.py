import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(sender: str, password: str, recipients: list, subject: str,
               body: str, *attachments):
    """Send and email through a Microsoft Office 365 account.

    Parameters
    ----------
    sender : str
        The email address sending the email
    password : str
        The email password
    recipients : list
        A list of recipients
    subject : str
        Email subject
    body : str
        The main body of the email, written in HTML
    """

    # message
    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = "; ".join(recipients)
    msg['Subject'] = subject

    if attachments:
        for item in attachments:
            a = open(item, 'rb')
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(a.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment',
                            filename=item.split(os.sep).pop())
            msg.attach(part)

    msg.attach(MIMEText(body, 'html'))

    # create SMTP object
    server = smtplib.SMTP(host='smtp.office365.com', port=587)
    server.ehlo()
    server.starttls()
    server.ehlo()

    # log in
    server.login(sender, password)

    # send email
    server.sendmail(sender, recipients, msg.as_string())
    server.quit()
