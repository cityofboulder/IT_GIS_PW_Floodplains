import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def create_html_table(data: list) -> str:
    """Creates table encoded in HTML, where columns are sorted based on
    the column names of each dict key.

    Parameters
    ----------
    data : list
        A list of dicts, where each dict has "col_name": value pairs

    Returns
    -------
    str
        An HTML table
    """

    # Encode headers into HTML
    sorted_headers = sorted(data[0])
    headers = "".join([f"<th>{x}</th>" for x in sorted_headers])
    header_row = f"<tr>{headers}</tr>"

    # Encode table data
    table_data = ""
    for dict_row in data:
        sorted_data = [dict_row[x] for x in sorted_headers]
        row_data = "".join([f"<td>{x}</td>" for x in sorted_data])
        table_row = f"<tr>{row_data}</tr>"
        table_data += table_row

    # Combine into a single table
    table = f"<table>{header_row}{table_data}</table>"

    return table


def email_body(body: str) -> str:
    """Places the body parameter into an HTML template for the email.

    Parameters
    ----------
    insert : str
        The main text of the email

    Returns
    -------
    str
        HTML email body
    """
    insert = f"""\
                <html>
                    <head>
                        <style>
                        table {{
                            border-collapse: collapse;
                            border: 1px solid;
                        }}

                        td, th {{
                            border: 1px solid rgb(190,190,190);
                            padding: 10px 10px;
                            letter-spacing: 0.7px;
                        }}

                        td {{
                            text-align: center;
                        }}
                        </style>
                    </head>
                    <body>
                        <p>
                        Dear Human,<br><br>
                        {body}
                        </p>
                        <p>
                        Beep Boop Beep,<br><br>
                        End Transmission
                        </p>
                    </body>
                </html>
                """
    return insert


def send_email(sender: str, password: str, recipients: list, body: str,
               *attachments):
    """Send and email through a Microsoft Office 365 account.

    Parameters
    ----------
    sender : str
        The email address sending the email
    password : str
        The email password
    recipients : list
        A list of recipients
    body : str
        The main body of the email, written in HTML
    """

    # message
    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = "; ".join(recipients)
    msg['Subject'] = "\N{Water Wave} Floodplain Update \N{Water Wave}"

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
