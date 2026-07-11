"""
Email notification utility module

Provides async email sending with HTML templating for notifications.
"""
import os
from typing import Optional
import logging
from email.message import EmailMessage

import aiosmtplib
from jinja2 import Template

logger = logging.getLogger(__name__)

# HTML template for notification emails
EMAIL_TEMPLATE = """
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background-color: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 30px; }
        .message { margin-bottom: 20px; line-height: 1.6; color: #333; }
        .action-btn { display: inline-block; background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
        </div>
        <div class="content">
            <div class="message">{{ message }}</div>
            {% if action_url %}
            <p>
                <a href="{{ action_url }}" class="action-btn">
                    {{ action_label or 'View Details' }}
                </a>
            </p>
            {% endif %}
        </div>
        <div class="footer">
            <p>This is an automated notification from Perseus.</p>
        </div>
    </div>
</body>
</html>
"""


def build_notification_html(
    title: str,
    message: str,
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
) -> str:
    """
    Build HTML content for a notification email.
    
    Args:
        title: Email title/subject
        message: Notification message content
        action_url: Optional URL for action button
        action_label: Optional label for action button (defaults to 'View Details')
    
    Returns:
        str: Rendered HTML string
    """
    template = Template(EMAIL_TEMPLATE)
    return template.render(
        title=title,
        message=message,
        action_url=action_url,
        action_label=action_label,
    )


async def send_notification_email(
    to_email: str,
    subject: str,
    title: str,
    message: str,
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
) -> bool:
    """
    Send a notification email asynchronously.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        title: Title for the email template
        message: Message content
        action_url: Optional URL for action button
        action_label: Optional label for action button
    
    Returns:
        bool: True if sent successfully, False on failure
    """
    try:
        html_content = build_notification_html(
            title=title,
            message=message,
            action_url=action_url,
            action_label=action_label,
        )
        
        # Get SMTP configuration from environment variables
        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@perseus.local")
        
        msg = EmailMessage()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(html_content, subtype="html")
        
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_username if smtp_username else None,
            password=smtp_password if smtp_password else None,
            use_tls=smtp_use_tls,
        )
        
        logger.info(f"Notification email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send notification email to {to_email}: {str(e)}")
        return False