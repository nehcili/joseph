import smtplib
from email.mime.text import MIMEText
from typing import Union

def send_email(
    subject: str,
    from_addr: str,
    to_addrs: list[str],
    content: Union[str, MIMEText],
    password: str = None,
    html: bool = False,
    smtp_server: str = 'smtp.gmail.com',
    smtp_port: int = 465
):
    """
    Send an email with the given subject, from, to, and content.

    Args:
        subject (str): Email subject.
        from_addr (str): Sender email address.
        to_addrs (list[str]): List of recipient email addresses.
        content (str): Email content (plain text or HTML).
        html (bool): If True, send as HTML. Otherwise, send as plain text.
        smtp_server (str): SMTP server address.
        smtp_port (int): SMTP server port.
    """
    if html:
        msg = MIMEText(content, 'html')
    else:
        msg = MIMEText(content)

    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(from_addr, password)
        server.sendmail(from_addr, to_addrs, msg.as_string())
