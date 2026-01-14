"""
n8n Webhook Integration Module

Handles all webhook calls to n8n workflows for automation.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("app.n8n")

# n8n Webhook URLs from environment
N8N_REGISTRATION_WEBHOOK = os.environ.get('N8N_REGISTRATION_WEBHOOK', '')
N8N_APPROVAL_WEBHOOK = os.environ.get('N8N_APPROVAL_WEBHOOK', '')
N8N_AI_REVIEW_WEBHOOK = os.environ.get('N8N_AI_REVIEW_WEBHOOK', '')
N8N_INSTITUTE_ADMIN_REGISTRATION_WEBHOOK = os.environ.get('N8N_INSTITUTE_ADMIN_REGISTRATION_WEBHOOK', '')
N8N_INSTITUTE_STAFF_REGISTRATION_WEBHOOK = os.environ.get('N8N_INSTITUTE_STAFF_REGISTRATION_WEBHOOK', '')
N8N_INSTITUTE_STAFF_APPROVAL_WEBHOOK = os.environ.get('N8N_INSTITUTE_STAFF_APPROVAL_WEBHOOK', '')
N8N_PASSWORD_RESET_WEBHOOK = os.environ.get('N8N_PASSWORD_RESET_WEBHOOK', '')
N8N_EMAIL_VERIFICATION_WEBHOOK = os.environ.get('N8N_EMAIL_VERIFICATION_WEBHOOK', '')
N8N_INVOICE_WEBHOOK = os.environ.get('N8N_INVOICE_WEBHOOK', '')

# Timeout for webhook requests (in seconds)
WEBHOOK_TIMEOUT = 10


def send_registration_notification(user_data: Dict[str, Any]) -> bool:
    """
    Send new user registration notification to n8n workflow.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
            - phone: str
            - institute: str
            - created_at: timestamp

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_REGISTRATION_WEBHOOK:
        logger.warning("N8N_REGISTRATION_WEBHOOK not configured - skipping notification")
        return False

    try:
        payload = {
            'event': 'new_registration',
            'user': {
                'name': user_data.get('name', ''),
                'email': user_data.get('email', ''),
                'phone': user_data.get('phone', ''),
                'institute': user_data.get('institute', ''),
                'created_at': str(user_data.get('created_at', ''))
            },
            'super_admin': {
                'email': os.environ.get('SUPER_ADMIN_EMAIL', 'drsandeep@physiologicprism.com'),
                'name': os.environ.get('SUPER_ADMIN_NAME', 'Dr Sandeep Rao')
            }
        }

        response = requests.post(
            N8N_REGISTRATION_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"Registration notification sent for {user_data.get('email')}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending registration notification for {user_data.get('email')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send registration notification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_registration_notification: {str(e)}")
        return False


def send_approval_notification(user_data: Dict[str, Any], temp_password: Optional[str] = None) -> bool:
    """
    Send user approval notification to n8n workflow.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
            - institute: str
        temp_password: Optional temporary password for Firebase account

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_APPROVAL_WEBHOOK:
        logger.warning("N8N_APPROVAL_WEBHOOK not configured - skipping notification")
        return False

    try:
        payload = {
            'event': 'user_approved',
            'user': {
                'name': user_data.get('name', ''),
                'email': user_data.get('email', ''),
                'institute': user_data.get('institute', ''),
            },
            'credentials': {
                'temp_password': temp_password,
                'has_password': temp_password is not None
            },
            'app_info': {
                'support_email': os.environ.get('SUPPORT_EMAIL', 'support@physiologicprism.com')
            }
        }

        response = requests.post(
            N8N_APPROVAL_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"Approval notification sent for {user_data.get('email')}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending approval notification for {user_data.get('email')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send approval notification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_approval_notification: {str(e)}")
        return False


def send_ai_review_request(user_data: Dict[str, Any], ai_response: Dict[str, Any]) -> bool:
    """
    Send AI review request to n8n workflow.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
        ai_response: Dictionary containing AI response data
            - patient_info: str
            - ai_analysis: str
            - timestamp: str
            - session_id: str (optional)

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_AI_REVIEW_WEBHOOK:
        logger.warning("N8N_AI_REVIEW_WEBHOOK not configured - skipping review request")
        return False

    try:
        payload = {
            'event': 'ai_review_request',
            'user': {
                'name': user_data.get('name', ''),
                'email': user_data.get('email', ''),
            },
            'ai_response': ai_response
        }

        response = requests.post(
            N8N_AI_REVIEW_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"AI review request sent for {user_data.get('email')}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending AI review request for {user_data.get('email')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send AI review request: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_ai_review_request: {str(e)}")
        return False


def send_institute_admin_registration_notification(user_data: Dict[str, Any]) -> bool:
    """
    Send institute admin registration notification to super admin.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
            - phone: str
            - institute: str
            - created_at: timestamp

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_INSTITUTE_ADMIN_REGISTRATION_WEBHOOK:
        logger.warning("N8N_INSTITUTE_ADMIN_REGISTRATION_WEBHOOK not configured - skipping notification")
        return False

    try:
        payload = {
            'event': 'institute_admin_registration',
            'user': {
                'name': user_data.get('name', ''),
                'email': user_data.get('email', ''),
                'phone': user_data.get('phone', ''),
                'institute': user_data.get('institute', ''),
                'created_at': str(user_data.get('created_at', ''))
            },
            'super_admin': {
                'email': os.environ.get('SUPER_ADMIN_EMAIL', 'drsandeep@physiologicprism.com'),
                'name': os.environ.get('SUPER_ADMIN_NAME', 'Dr Sandeep Rao')
            }
        }

        response = requests.post(
            N8N_INSTITUTE_ADMIN_REGISTRATION_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"Institute admin registration notification sent for {user_data.get('email')}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending institute admin notification for {user_data.get('email')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send institute admin notification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_institute_admin_registration_notification: {str(e)}")
        return False


def send_institute_staff_registration_notification(user_data: Dict[str, Any], institute_admin_email: str) -> bool:
    """
    Send institute staff registration notification to institute admin.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
            - phone: str
            - institute: str
            - created_at: timestamp
        institute_admin_email: Email of the institute admin to notify

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_INSTITUTE_STAFF_REGISTRATION_WEBHOOK:
        logger.warning("N8N_INSTITUTE_STAFF_REGISTRATION_WEBHOOK not configured - skipping notification")
        return False

    try:
        payload = {
            'event': 'institute_staff_registration',
            'user': {
                'name': user_data.get('name', ''),
                'email': user_data.get('email', ''),
                'phone': user_data.get('phone', ''),
                'institute': user_data.get('institute', ''),
                'created_at': str(user_data.get('created_at', ''))
            },
            'institute_admin': {
                'email': institute_admin_email,
                'name': user_data.get('institute', '')  # Using institute name as placeholder
            }
        }

        response = requests.post(
            N8N_INSTITUTE_STAFF_REGISTRATION_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"Institute staff registration notification sent for {user_data.get('email')}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending institute staff notification for {user_data.get('email')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send institute staff notification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_institute_staff_registration_notification: {str(e)}")
        return False


def send_institute_staff_approval_notification(user_data: Dict[str, Any], institute_name: str, temp_password: Optional[str] = None) -> bool:
    """
    Send staff approval notification to institute staff member.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
        institute_name: Name of the institute
        temp_password: Optional temporary password for Firebase account

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_INSTITUTE_STAFF_APPROVAL_WEBHOOK:
        logger.warning("N8N_INSTITUTE_STAFF_APPROVAL_WEBHOOK not configured - skipping notification")
        return False

    try:
        payload = {
            'event': 'institute_staff_approved',
            'user': {
                'name': user_data.get('name', ''),
                'email': user_data.get('email', '')
            },
            'institute_admin': {
                'institute': institute_name
            },
            'credentials': {
                'temp_password': temp_password,
                'has_password': temp_password is not None
            },
            'app_info': {
                'support_email': os.environ.get('SUPPORT_EMAIL', 'support@physiologicprism.com')
            }
        }

        response = requests.post(
            N8N_INSTITUTE_STAFF_APPROVAL_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"Institute staff approval notification sent for {user_data.get('email')}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending staff approval notification for {user_data.get('email')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send staff approval notification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_institute_staff_approval_notification: {str(e)}")
        return False


def send_password_reset_notification(user_data: Dict[str, Any], reset_token: str, reset_url: str) -> bool:
    """
    Send password reset link notification to user via n8n workflow.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
        reset_token: Secure password reset token
        reset_url: Full URL for password reset (including token)

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_PASSWORD_RESET_WEBHOOK:
        logger.warning("N8N_PASSWORD_RESET_WEBHOOK not configured - skipping notification")
        return False

    try:
        payload = {
            'event': 'password_reset_request',
            'user': {
                'name': user_data.get('name', ''),
                'email': user_data.get('email', '')
            },
            'reset': {
                'token': reset_token,
                'url': reset_url,
                'expires_in_minutes': 30
            },
            'app_info': {
                'support_email': os.environ.get('SUPPORT_EMAIL', 'support@physiologicprism.com')
            }
        }

        response = requests.post(
            N8N_PASSWORD_RESET_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"Password reset notification sent for {user_data.get('email')}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending password reset notification for {user_data.get('email')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send password reset notification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_password_reset_notification: {str(e)}")
        return False


def send_email_verification(user_data: Dict[str, Any], verification_token: str, app_url: str) -> bool:
    """
    Send email verification link to user via n8n workflow.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
        verification_token: str - The verification token
        app_url: str - Base URL of the application

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_EMAIL_VERIFICATION_WEBHOOK:
        logger.warning("N8N_EMAIL_VERIFICATION_WEBHOOK not configured - skipping notification")
        return False

    try:
        verification_link = f"{app_url}/verify-email?email={user_data.get('email')}&token={verification_token}"

        payload = {
            'event': 'email_verification',
            'user': {
                'name': user_data.get('name', ''),
                'email': user_data.get('email', '')
            },
            'verification_link': verification_link,
            'expires_in_hours': 24
        }

        response = requests.post(
            N8N_EMAIL_VERIFICATION_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"Email verification sent to {user_data.get('email')}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending email verification to {user_data.get('email')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send email verification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_email_verification: {str(e)}")
        return False


def send_invoice_email(invoice_data: Dict[str, Any], pdf_base64: Optional[str] = None) -> bool:
    """
    Send invoice email to user via n8n workflow.

    The n8n workflow will generate and send the email with PDF attachment.

    Args:
        invoice_data: Dictionary containing invoice information
            - invoice_number: str
            - invoice_date: timestamp
            - customer_name: str
            - customer_email: str
            - description: str
            - base_amount: float
            - cgst: float
            - sgst: float
            - igst: float
            - total_amount: float
            - payment_id: str
            - transaction_type: str ('subscription' or 'token_purchase')
        pdf_base64: Optional base64 encoded PDF content

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_INVOICE_WEBHOOK:
        logger.warning("N8N_INVOICE_WEBHOOK not configured - skipping invoice email")
        return False

    try:
        # Format invoice date if it's a timestamp
        invoice_date = invoice_data.get('invoice_date', '')
        if hasattr(invoice_date, 'strftime'):
            invoice_date = invoice_date.strftime('%d-%b-%Y')
        elif invoice_date:
            invoice_date = str(invoice_date)

        payload = {
            'event': 'invoice_generated',
            'invoice': {
                'invoice_number': invoice_data.get('invoice_number', ''),
                'invoice_date': invoice_date,
                'description': invoice_data.get('description', ''),
                'base_amount': invoice_data.get('base_amount', 0),
                'cgst': invoice_data.get('cgst', 0),
                'sgst': invoice_data.get('sgst', 0),
                'igst': invoice_data.get('igst', 0),
                'gst_rate': invoice_data.get('gst_rate', 18),
                'total_amount': invoice_data.get('total_amount', 0),
                'currency': invoice_data.get('currency', 'INR'),
                'payment_id': invoice_data.get('payment_id', ''),
                'payment_method': invoice_data.get('payment_method', 'Razorpay'),
                'transaction_type': invoice_data.get('transaction_type', 'subscription'),
                'sac_code': invoice_data.get('sac_code', '998314')
            },
            'customer': {
                'name': invoice_data.get('customer_name', ''),
                'email': invoice_data.get('customer_email', invoice_data.get('user_id', '')),
                'phone': invoice_data.get('customer_phone', ''),
                'institute': invoice_data.get('customer_institute', '')
            },
            'business': {
                'name': invoice_data.get('business_name', 'PhysiologicPRISM'),
                'address': invoice_data.get('business_address', 'India'),
                'gstin': invoice_data.get('business_gstin', 'N/A'),
                'pan': invoice_data.get('business_pan', 'N/A'),
                'email': invoice_data.get('business_email', 'support@physiologicprism.com'),
                'phone': invoice_data.get('business_phone', '')
            },
            'support_email': os.environ.get('SUPPORT_EMAIL', 'support@physiologicprism.com')
        }

        # Add PDF attachment if provided
        if pdf_base64:
            payload['pdf_attachment'] = {
                'filename': f"{invoice_data.get('invoice_number', 'invoice')}.pdf",
                'content': pdf_base64,
                'content_type': 'application/pdf'
            }

        response = requests.post(
            N8N_INVOICE_WEBHOOK,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        response.raise_for_status()
        logger.info(f"Invoice email sent for {invoice_data.get('invoice_number')} to {invoice_data.get('customer_email', invoice_data.get('user_id'))}")
        return True

    except requests.exceptions.Timeout:
        logger.error(f"Timeout sending invoice email for {invoice_data.get('invoice_number')}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send invoice email: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_invoice_email: {str(e)}")
        return False
