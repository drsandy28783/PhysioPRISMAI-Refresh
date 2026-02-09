"""
Email Service Module using Resend

Handles all transactional emails for the application.
Replaces n8n webhook integration with direct Resend API calls.
"""

import os
import logging
import resend
from typing import Dict, Any, Optional

logger = logging.getLogger("app.email")

# Configure Resend API
resend.api_key = os.environ.get('RESEND_API_KEY', '')

# Email configuration
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@physiologicprism.com')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@physiologicprism.com')
SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL', 'drsandeep@physiologicprism.com')
SUPER_ADMIN_NAME = os.environ.get('SUPER_ADMIN_NAME', 'Dr Sandeep Rao')
APP_NAME = os.environ.get('APP_NAME', 'PhysiologicPRISM')
APP_URL = os.environ.get('APP_URL', 'https://physiologicprism.com')


def send_email(to: str, subject: str, html: str, max_retries: int = 3) -> bool:
    """
    Base function to send email via Resend API with retry logic.

    Args:
        to: Recipient email address
        subject: Email subject
        html: HTML content of the email
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not resend.api_key:
        logger.error("CRITICAL: RESEND_API_KEY not configured - email service disabled!")
        logger.error(f"Attempted to send: TO={to}, SUBJECT={subject}")
        return False

    for attempt in range(max_retries):
        try:
            params = {
                "from": FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html,
            }

            logger.info(f"Attempting to send email (attempt {attempt + 1}/{max_retries}): TO={to}, SUBJECT={subject}")
            response = resend.Emails.send(params)
            logger.info(f"✅ Email sent successfully to {to}: {subject} (Response: {response})")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email (attempt {attempt + 1}/{max_retries}) to {to}: {type(e).__name__}: {str(e)}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
            else:
                logger.error(f"CRITICAL: All {max_retries} email send attempts failed for {to}", exc_info=True)
                return False

    return False


def send_registration_notification(user_data: Dict[str, Any]) -> bool:
    """
    Send new user registration notification to super admin.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
            - phone: str
            - institute: str
            - created_at: timestamp
            - user_type: str (optional: 'individual', 'institute_staff')

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    logger.info(f"🔔 send_registration_notification called for: {user_data.get('name')} ({user_data.get('email')})")
    logger.info(f"Email config: FROM={FROM_EMAIL}, TO={SUPER_ADMIN_EMAIL}, RESEND_KEY={'SET' if resend.api_key else 'NOT SET'}")

    try:
        user_type = user_data.get('user_type', 'individual')

        # Determine user type display
        type_badge = ""
        type_description = ""
        header_color = "#667eea"

        if user_type == 'institute_staff':
            type_badge = '<div style="background: #3498db; color: white; padding: 10px 20px; border-radius: 5px; text-align: center; margin: 15px 0;"><strong>👥 INSTITUTE STAFF MEMBER</strong></div>'
            type_description = "This user is registering as a staff member under an existing institute."
            header_color = "#3498db"
        else:
            type_badge = '<div style="background: #667eea; color: white; padding: 10px 20px; border-radius: 5px; text-align: center; margin: 15px 0;"><strong>👤 INDIVIDUAL PHYSIOTHERAPIST</strong></div>'
            type_description = "This user is registering as an individual practitioner."
            header_color = "#667eea"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, {header_color} 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {header_color}; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: {header_color}; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: {header_color}; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 New User Registration</h1>
                </div>
                <div class="content">
                    <p>Dear {SUPER_ADMIN_NAME},</p>
                    <p>A new user has registered on {APP_NAME} and is awaiting your approval.</p>

                    {type_badge}
                    <p style="color: #666; font-size: 14px; text-align: center;">{type_description}</p>

                    <div class="info-box">
                        <div class="info-row"><span class="label">Name:</span> {user_data.get('name', 'N/A')}</div>
                        <div class="info-row"><span class="label">Email:</span> {user_data.get('email', 'N/A')}</div>
                        <div class="info-row"><span class="label">Phone:</span> {user_data.get('phone', 'N/A')}</div>
                        <div class="info-row"><span class="label">Institute:</span> {user_data.get('institute', 'N/A')}</div>
                        <div class="info-row"><span class="label">Registration Time:</span> {user_data.get('created_at', 'N/A')}</div>
                    </div>

                    <p>Please review and approve this registration from your admin dashboard.</p>

                    <a href="{APP_URL}/super_admin_dashboard" class="button">Go to Admin Dashboard</a>

                    <div class="footer">
                        <p>This is an automated notification from {APP_NAME}</p>
                        <p>Support: {SUPPORT_EMAIL}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        # Update subject line to indicate user type
        subject_prefix = ""
        if user_type == 'institute_staff':
            subject_prefix = "👥 Staff - "
        else:
            subject_prefix = "👤 Individual - "

        return send_email(
            to=SUPER_ADMIN_EMAIL,
            subject=f"{subject_prefix}New Registration: {user_data.get('name')} - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_registration_notification: {str(e)}")
        return False


def send_approval_notification(user_data: Dict[str, Any], temp_password: Optional[str] = None) -> bool:
    """
    Send user approval notification to user.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
            - institute: str
        temp_password: Optional temporary password for Firebase account

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        password_section = ""
        if temp_password:
            password_section = f"""
            <div class="info-box" style="background: #fff3cd; border-left-color: #ffc107;">
                <h3 style="color: #856404; margin-top: 0;">🔐 Your Login Credentials</h3>
                <div class="info-row"><span class="label">Email:</span> {user_data.get('email')}</div>
                <div class="info-row"><span class="label">Temporary Password:</span> <code style="background: #f8f9fa; padding: 5px 10px; border-radius: 4px; font-size: 14px;">{temp_password}</code></div>
                <p style="margin-top: 15px; color: #856404;"><strong>⚠️ Important:</strong> Please change your password immediately after your first login.</p>
            </div>
            """
        else:
            password_section = """
            <p>You can now log in using your existing credentials.</p>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #11998e; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #11998e; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #11998e; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Account Approved!</h1>
                </div>
                <div class="content">
                    <p>Dear {user_data.get('name')},</p>
                    <p>Congratulations! Your account on {APP_NAME} has been approved and is now active.</p>

                    {password_section}

                    <div class="info-box">
                        <h3 style="color: #11998e; margin-top: 0;">📋 Account Details</h3>
                        <div class="info-row"><span class="label">Institute:</span> {user_data.get('institute', 'N/A')}</div>
                        <div class="info-row"><span class="label">Email:</span> {user_data.get('email')}</div>
                    </div>

                    <p>You can now access all features of {APP_NAME} to enhance your physiotherapy practice with AI-powered clinical reasoning tools.</p>

                    <a href="{APP_URL}/login" class="button">Login Now</a>

                    <div class="footer">
                        <p>Need help? Contact us at {SUPPORT_EMAIL}</p>
                        <p>© 2025 {APP_NAME}. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=user_data.get('email'),
            subject=f"Welcome to {APP_NAME} - Account Approved!",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_approval_notification: {str(e)}")
        return False


def send_rejection_notification(user_data: Dict[str, Any], reason: Optional[str] = None) -> bool:
    """
    Send user rejection notification to user.

    Args:
        user_data: Dictionary containing user information
            - name: str
            - email: str
            - institute: str
        reason: Optional reason for rejection

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        reason_section = ""
        if reason:
            reason_section = f"""
            <div class="info-box" style="border-left-color: #e74c3c;">
                <h3 style="color: #e74c3c; margin-top: 0;">Reason</h3>
                <p>{reason}</p>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #e74c3c; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Registration Status Update</h1>
                </div>
                <div class="content">
                    <p>Dear {user_data.get('name', 'User')},</p>
                    <p>Thank you for your interest in {APP_NAME}.</p>
                    <p>We regret to inform you that your registration request for {user_data.get('institute', 'the institute')} has not been approved at this time.</p>

                    {reason_section}

                    <p>If you believe this was an error or would like to discuss this decision, please contact us at {SUPPORT_EMAIL}.</p>

                    <p>We appreciate your understanding.</p>

                    <div class="footer">
                        <p>Best regards,</p>
                        <p>{APP_NAME} Team</p>
                        <p>Support: {SUPPORT_EMAIL}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=user_data.get('email'),
            subject=f"Registration Update - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_rejection_notification: {str(e)}")
        return False


def send_institute_admin_registration_notification(user_data: Dict[str, Any]) -> bool:
    """
    Send institute admin registration notification to super admin.
    CRITICAL: This user will have admin privileges - requires approval!

    Args:
        user_data: Dictionary containing user information

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    logger.info(f"🏥 send_institute_admin_registration_notification called for: {user_data.get('name')} ({user_data.get('email')})")
    logger.info(f"Email config: FROM={FROM_EMAIL}, TO={SUPER_ADMIN_EMAIL}, RESEND_KEY={'SET' if resend.api_key else 'NOT SET'}")

    try:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #e74c3c; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #e74c3c; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #e74c3c; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .warning-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .admin-badge {{ background: #e74c3c; color: white; padding: 15px 25px; border-radius: 8px; text-align: center; margin: 20px 0; font-size: 18px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 ADMIN REGISTRATION - REQUIRES APPROVAL</h1>
                </div>
                <div class="content">
                    <p>Dear {SUPER_ADMIN_NAME},</p>

                    <div class="admin-badge">
                        🔐 INSTITUTE ADMINISTRATOR REGISTRATION
                    </div>

                    <p><strong>IMPORTANT:</strong> A new user has requested <strong>administrative privileges</strong> for their institute on {APP_NAME}.</p>

                    <div class="warning-box">
                        <p style="margin: 0; color: #856404;"><strong>⚠️ Security Notice:</strong> This user will have institute admin permissions if approved. Please verify their identity and authorization before approval.</p>
                    </div>

                    <div class="info-box">
                        <h3 style="color: #e74c3c; margin-top: 0;">Applicant Information</h3>
                        <div class="info-row"><span class="label">Name:</span> {user_data.get('name', 'N/A')}</div>
                        <div class="info-row"><span class="label">Email:</span> {user_data.get('email', 'N/A')}</div>
                        <div class="info-row"><span class="label">Phone:</span> {user_data.get('phone', 'N/A')}</div>
                        <div class="info-row"><span class="label">Institute:</span> {user_data.get('institute', 'N/A')}</div>
                        <div class="info-row"><span class="label">Registration Time:</span> {user_data.get('created_at', 'N/A')}</div>
                    </div>

                    <div style="background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Admin Privileges Include:</strong></p>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li>Approve/manage staff members for their institute</li>
                            <li>Access to institute-level data and reports</li>
                            <li>Full control over institute settings</li>
                        </ul>
                    </div>

                    <p style="text-align: center; margin-top: 30px;">
                        <a href="{APP_URL}/super_admin_dashboard" class="button">REVIEW & APPROVE/REJECT</a>
                    </p>

                    <div class="footer">
                        <p>This is an automated notification from {APP_NAME}</p>
                        <p>Support: {SUPPORT_EMAIL}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=SUPER_ADMIN_EMAIL,
            subject=f"🔐 ADMIN APPROVAL REQUIRED: {user_data.get('name')} - {user_data.get('institute')} - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_institute_admin_registration_notification: {str(e)}")
        return False


def send_institute_staff_registration_notification(user_data: Dict[str, Any], institute_admin_email: str) -> bool:
    """
    Send institute staff registration notification to institute admin.

    Args:
        user_data: Dictionary containing user information
        institute_admin_email: Email of the institute admin to notify

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4facfe; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #4facfe; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #4facfe; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👥 New Staff Registration</h1>
                </div>
                <div class="content">
                    <p>Dear Institute Administrator,</p>
                    <p>A new staff member has registered for your institute on {APP_NAME} and is awaiting your approval.</p>

                    <div class="info-box">
                        <div class="info-row"><span class="label">Name:</span> {user_data.get('name', 'N/A')}</div>
                        <div class="info-row"><span class="label">Email:</span> {user_data.get('email', 'N/A')}</div>
                        <div class="info-row"><span class="label">Phone:</span> {user_data.get('phone', 'N/A')}</div>
                        <div class="info-row"><span class="label">Institute:</span> {user_data.get('institute', 'N/A')}</div>
                        <div class="info-row"><span class="label">Registration Time:</span> {user_data.get('created_at', 'N/A')}</div>
                    </div>

                    <p>Please review and approve this staff member from your admin dashboard.</p>

                    <a href="{APP_URL}/dashboard" class="button">Review Application</a>

                    <div class="footer">
                        <p>This is an automated notification from {APP_NAME}</p>
                        <p>Support: {SUPPORT_EMAIL}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=institute_admin_email,
            subject=f"New Staff Registration: {user_data.get('name')} - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_institute_staff_registration_notification: {str(e)}")
        return False


def send_super_admin_staff_registration_notification(user_data: Dict[str, Any], institute_name: str, institute_admin_email: str, current_users: int, max_users: int) -> bool:
    """
    Send institute staff registration notification to SUPER ADMIN for tier 2 approval.
    This is sent AFTER institute admin has approved (tier 1).

    Args:
        user_data: Dictionary containing user information
        institute_name: Name of the institute
        institute_admin_email: Email of the institute admin who will do tier 1 approval
        current_users: Current number of users in the institute
        max_users: Maximum users allowed based on plan

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Calculate usage percentage
        usage_percentage = (current_users / max_users * 100) if max_users > 0 else 0

        # Determine warning level
        warning_badge = ""
        if usage_percentage >= 90:
            warning_badge = '<div style="background: #e74c3c; color: white; padding: 10px 20px; border-radius: 5px; text-align: center; margin: 15px 0;"><strong>⚠️ PLAN LIMIT NEARLY REACHED: {}/{} users ({}%)</strong></div>'.format(current_users, max_users, int(usage_percentage))
        elif usage_percentage >= 80:
            warning_badge = '<div style="background: #f39c12; color: white; padding: 10px 20px; border-radius: 5px; text-align: center; margin: 15px 0;"><strong>⚡ PLAN USAGE HIGH: {}/{} users ({}%)</strong></div>'.format(current_users, max_users, int(usage_percentage))
        else:
            warning_badge = '<div style="background: #27ae60; color: white; padding: 10px 20px; border-radius: 5px; text-align: center; margin: 15px 0;"><strong>✓ PLAN USAGE: {}/{} users ({}%)</strong></div>'.format(current_users, max_users, int(usage_percentage))

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4facfe; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #4facfe; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #4facfe; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .tier-badge {{ background: #667eea; color: white; padding: 15px 25px; border-radius: 8px; text-align: center; margin: 20px 0; font-size: 16px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👥 Staff Registration - Tier 2 Approval Needed</h1>
                </div>
                <div class="content">
                    <p>Dear {SUPER_ADMIN_NAME},</p>

                    <div class="tier-badge">
                        🔄 TWO-TIER APPROVAL: Institute Admin Review Required First
                    </div>

                    <p>A new staff member has registered for <strong>{institute_name}</strong> and needs approval from BOTH the institute admin and you.</p>

                    <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60;">
                        <h4 style="color: #27ae60; margin-top: 0;">📋 Approval Process</h4>
                        <ol style="margin: 10px 0; padding-left: 20px; color: #2c3e50;">
                            <li><strong>Tier 1:</strong> Institute Admin ({institute_admin_email}) reviews and approves</li>
                            <li><strong>Tier 2:</strong> You receive notification and give final approval</li>
                            <li><strong>Result:</strong> User receives access credentials</li>
                        </ol>
                    </div>

                    {warning_badge}

                    <div class="info-box">
                        <h3 style="color: #4facfe; margin-top: 0;">Staff Member Details</h3>
                        <div class="info-row"><span class="label">Name:</span> {user_data.get('name', 'N/A')}</div>
                        <div class="info-row"><span class="label">Email:</span> {user_data.get('email', 'N/A')}</div>
                        <div class="info-row"><span class="label">Phone:</span> {user_data.get('phone', 'N/A')}</div>
                        <div class="info-row"><span class="label">Institute:</span> {institute_name}</div>
                        <div class="info-row"><span class="label">Registration Time:</span> {user_data.get('created_at', 'N/A')}</div>
                    </div>

                    <div class="info-box">
                        <h3 style="color: #4facfe; margin-top: 0;">Institute Plan Status</h3>
                        <div class="info-row"><span class="label">Institute:</span> {institute_name}</div>
                        <div class="info-row"><span class="label">Institute Admin:</span> {institute_admin_email}</div>
                        <div class="info-row"><span class="label">Current Users:</span> {current_users}/{max_users} ({int(usage_percentage)}% used)</div>
                    </div>

                    <p><strong>Note:</strong> This staff member will first be reviewed by the institute admin. You'll receive another notification when the institute admin approves, at which point you can give final approval.</p>

                    <a href="{APP_URL}/super_admin_dashboard" class="button">View All Pending Approvals</a>

                    <div class="footer">
                        <p>This is an automated notification from {APP_NAME}</p>
                        <p>Two-Tier Approval System</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=SUPER_ADMIN_EMAIL,
            subject=f"👥 Staff Registration (Tier 1 Pending): {user_data.get('name')} at {institute_name} - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_super_admin_staff_registration_notification: {str(e)}")
        return False


def send_super_admin_tier2_approval_notification(user_data: Dict[str, Any], institute_name: str, institute_admin_email: str, approved_by: str) -> bool:
    """
    Send notification to super admin when institute admin approves staff (tier 1 complete).
    Super admin can now give final approval (tier 2).

    Args:
        user_data: Dictionary containing user information
        institute_name: Name of the institute
        institute_admin_email: Email of the institute admin who approved
        approved_by: Name of the person who approved at tier 1

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #27ae60 0%, #38ef7d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #27ae60; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #27ae60; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .tier-badge {{ background: #27ae60; color: white; padding: 15px 25px; border-radius: 8px; text-align: center; margin: 20px 0; font-size: 16px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Tier 1 Approved - Your Approval Needed</h1>
                </div>
                <div class="content">
                    <p>Dear {SUPER_ADMIN_NAME},</p>

                    <div class="tier-badge">
                        ✓ TIER 1 COMPLETE → TIER 2 APPROVAL NEEDED
                    </div>

                    <p>Good news! The institute admin has approved this staff member. Now it's your turn to give final approval.</p>

                    <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60;">
                        <p style="margin: 0; color: #27ae60;"><strong>✓ Tier 1 Approved By:</strong> {approved_by} ({institute_admin_email})</p>
                        <p style="margin: 10px 0 0 0; color: #27ae60;"><strong>⏳ Awaiting:</strong> Your final approval (Tier 2)</p>
                    </div>

                    <div class="info-box">
                        <h3 style="color: #27ae60; margin-top: 0;">Staff Member Details</h3>
                        <div class="info-row"><span class="label">Name:</span> {user_data.get('name', 'N/A')}</div>
                        <div class="info-row"><span class="label">Email:</span> {user_data.get('email', 'N/A')}</div>
                        <div class="info-row"><span class="label">Phone:</span> {user_data.get('phone', 'N/A')}</div>
                        <div class="info-row"><span class="label">Institute:</span> {institute_name}</div>
                        <div class="info-row"><span class="label">Approved By (Tier 1):</span> {approved_by}</div>
                    </div>

                    <p style="text-align: center; margin-top: 30px;">
                        <a href="{APP_URL}/super_admin_dashboard" class="button">Approve Now (Final Step)</a>
                    </p>

                    <div class="footer">
                        <p>This is an automated notification from {APP_NAME}</p>
                        <p>Two-Tier Approval System - Tier 2 Pending</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=SUPER_ADMIN_EMAIL,
            subject=f"✅ Tier 1 Approved - Final Approval Needed: {user_data.get('name')} at {institute_name} - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_super_admin_tier2_approval_notification: {str(e)}")
        return False


def send_institute_staff_approval_notification(user_data: Dict[str, Any], institute_name: str, temp_password: Optional[str] = None) -> bool:
    """
    Send staff approval notification to institute staff member.

    Args:
        user_data: Dictionary containing user information
        institute_name: Name of the institute
        temp_password: Optional temporary password

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        password_section = ""
        if temp_password:
            password_section = f"""
            <div class="info-box" style="background: #fff3cd; border-left-color: #ffc107;">
                <h3 style="color: #856404; margin-top: 0;">🔐 Your Login Credentials</h3>
                <div class="info-row"><span class="label">Email:</span> {user_data.get('email')}</div>
                <div class="info-row"><span class="label">Temporary Password:</span> <code style="background: #f8f9fa; padding: 5px 10px; border-radius: 4px; font-size: 14px;">{temp_password}</code></div>
                <p style="margin-top: 15px; color: #856404;"><strong>⚠️ Important:</strong> Please change your password immediately after your first login.</p>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #11998e; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #11998e; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #11998e; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Approved by {institute_name}</h1>
                </div>
                <div class="content">
                    <p>Dear {user_data.get('name')},</p>
                    <p>Great news! Your account has been approved by your institute administrator and is now active.</p>

                    {password_section}

                    <p>You can now access {APP_NAME} to enhance your physiotherapy practice.</p>

                    <a href="{APP_URL}/login" class="button">Login Now</a>

                    <div class="footer">
                        <p>Need help? Contact us at {SUPPORT_EMAIL}</p>
                        <p>© 2025 {APP_NAME}. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=user_data.get('email'),
            subject=f"Account Approved - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_institute_staff_approval_notification: {str(e)}")
        return False


def send_password_reset_notification(user_data: Dict[str, Any], reset_token: str, reset_url: str) -> bool:
    """
    Send password reset link notification to user.

    Args:
        user_data: Dictionary containing user information
        reset_token: Secure password reset token
        reset_url: Full URL for password reset

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #fa709a; }}
                .warning-box {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #fa709a; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔒 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Dear {user_data.get('name')},</p>
                    <p>We received a request to reset your password for your {APP_NAME} account.</p>

                    <div class="info-box">
                        <p>Click the button below to reset your password:</p>
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </div>

                    <div class="warning-box">
                        <p style="margin: 0; color: #856404;"><strong>⏰ This link expires in 30 minutes.</strong></p>
                        <p style="margin: 10px 0 0 0; color: #856404;">If you didn't request this reset, please ignore this email and your password will remain unchanged.</p>
                    </div>

                    <p style="font-size: 12px; color: #666;">If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{reset_url}" style="color: #fa709a; word-break: break-all;">{reset_url}</a></p>

                    <div class="footer">
                        <p>Need help? Contact us at {SUPPORT_EMAIL}</p>
                        <p>© 2025 {APP_NAME}. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=user_data.get('email'),
            subject=f"Password Reset Request - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_password_reset_notification: {str(e)}")
        return False


def send_email_verification(user_data: Dict[str, Any], verification_token: str, app_url: str) -> bool:
    """
    Send email verification link to user.

    Args:
        user_data: Dictionary containing user information
        verification_token: str - The verification token
        app_url: str - Base URL of the application

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        verification_link = f"{app_url}/verify-email?email={user_data.get('email')}&token={verification_token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📧 Verify Your Email</h1>
                </div>
                <div class="content">
                    <p>Dear {user_data.get('name')},</p>
                    <p>Welcome to {APP_NAME}! Please verify your email address to complete your registration.</p>

                    <div class="info-box">
                        <p>Click the button below to verify your email:</p>
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </div>

                    <p style="margin-top: 20px; color: #666;">This link expires in 24 hours.</p>

                    <p style="font-size: 12px; color: #666;">If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{verification_link}" style="color: #667eea; word-break: break-all;">{verification_link}</a></p>

                    <div class="footer">
                        <p>If you didn't create an account, please ignore this email.</p>
                        <p>© 2025 {APP_NAME}. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=user_data.get('email'),
            subject=f"Verify Your Email - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_email_verification: {str(e)}")
        return False


def send_early_access_notification(admin_email: str, full_name: str, email: str, role: str,
                                   organisation: str, country: str, use_case: str,
                                   pilot_interest: bool) -> bool:
    """
    Send notification to admin when someone requests early access.

    Args:
        admin_email: Email address to send notification to
        full_name: Applicant's full name
        email: Applicant's email
        role: Selected role
        organisation: Organisation name
        country: Country
        use_case: How they plan to use PhysiologicPRISM
        pilot_interest: Boolean - interested in pilot program

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        pilot_badge = ""
        if pilot_interest:
            pilot_badge = """
            <div style="background: #667eea; color: white; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center;">
                <h3 style="margin: 0; font-size: 18px;">🎯 PILOT PROGRAM INTEREST</h3>
                <p style="margin: 5px 0 0 0;">This applicant is interested in a structured pilot program!</p>
            </div>
            """

        # Map role codes to readable names
        role_names = {
            'clinician': 'Clinician / Physiotherapist',
            'owner': 'Clinic / Hospital Owner',
            'educator': 'University / Educator',
            'student': 'Student / New Graduate',
            'researcher': 'Researcher',
            'other': 'Other'
        }
        role_display = role_names.get(role, role)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 650px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1a5f5a 0%, #4a7c7a 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 25px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1a5f5a; }}
                .info-row {{ margin: 12px 0; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }}
                .info-row:last-child {{ border-bottom: none; }}
                .label {{ font-weight: bold; color: #1a5f5a; display: inline-block; min-width: 120px; }}
                .use-case-box {{ background: #f8fffe; padding: 15px; border-radius: 6px; margin: 15px 0; border-left: 3px solid #1a5f5a; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #1a5f5a; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .quick-reply {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 New Early Access Request</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Someone wants to try PhysiologicPRISM!</p>
                </div>
                <div class="content">
                    <p>Hi there,</p>
                    <p>You've received a new early access request for PhysiologicPRISM. Here are the details:</p>

                    {pilot_badge}

                    <div class="info-box">
                        <h3 style="color: #1a5f5a; margin-top: 0;">📋 Applicant Information</h3>
                        <div class="info-row">
                            <span class="label">Name:</span>
                            <span>{full_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Email:</span>
                            <span><a href="mailto:{email}" style="color: #1a5f5a;">{email}</a></span>
                        </div>
                        <div class="info-row">
                            <span class="label">Role:</span>
                            <span>{role_display}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Organisation:</span>
                            <span>{organisation}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Country:</span>
                            <span>{country}</span>
                        </div>
                    </div>

                    <div class="use-case-box">
                        <h4 style="color: #1a5f5a; margin-top: 0;">💡 How they plan to use PhysiologicPRISM:</h4>
                        <p style="margin: 0; white-space: pre-wrap;">{use_case}</p>
                    </div>

                    <div class="quick-reply">
                        <h4 style="color: #27ae60; margin-top: 0;">✉️ Quick Reply Template</h4>
                        <p style="font-size: 13px; line-height: 1.5; margin: 0;">
                            Click the button below to reply to <strong>{full_name}</strong> directly:
                        </p>
                        <a href="mailto:{email}?subject=Re: PhysiologicPRISM Early Access Request&body=Hi {full_name.split()[0]},\n\nThank you for your interest in PhysiologicPRISM!\n\n" class="button">Reply to Applicant</a>
                    </div>

                    <div class="footer">
                        <p>This is an automated notification from PhysiologicPRISM Early Access System</p>
                        <p>To view all requests, check your Firestore 'access_requests' collection</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=admin_email,
            subject=f"🚀 Early Access Request from {full_name} ({organisation})",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_early_access_notification: {str(e)}")
        return False


def send_early_access_confirmation(full_name: str, email: str, role: str, pilot_interest: bool) -> bool:
    """
    Send confirmation email to user who submitted early access request.

    Args:
        full_name: Applicant's full name
        email: Applicant's email
        role: Selected role
        pilot_interest: Boolean - interested in pilot program

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Map role codes to readable names
        role_names = {
            'clinician': 'Clinician / Physiotherapist',
            'owner': 'Clinic / Hospital Owner',
            'educator': 'University / Educator',
            'student': 'Student / New Graduate',
            'researcher': 'Researcher',
            'other': 'Other'
        }
        role_display = role_names.get(role, role)

        pilot_section = ""
        if pilot_interest:
            pilot_section = """
            <div style="background: #e6f7f5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1a5f5a;">
                <h3 style="color: #1a5f5a; margin-top: 0;">🎯 Pilot Program Interest Noted</h3>
                <p style="margin: 0;">We've noted your interest in our 30-day structured pilot program. We'll include pilot program details in our follow-up email.</p>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1a5f5a 0%, #4a7c7a 100%); color: white; padding: 35px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1a5f5a; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .checkmark {{ font-size: 48px; color: #27ae60; text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Request Received</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.95; font-size: 18px;">Thank you for your interest in PhysiologicPRISM!</p>
                </div>
                <div class="content">
                    <div class="checkmark">✓</div>

                    <p>Dear {full_name},</p>

                    <p>We've successfully received your early access request for PhysiologicPRISM. Thank you for your interest in our AI-guided clinical reasoning platform!</p>

                    <div class="info-box">
                        <h3 style="color: #1a5f5a; margin-top: 0;">📋 Your Request Details</h3>
                        <p style="margin: 8px 0;"><strong>Role:</strong> {role_display}</p>
                        <p style="margin: 8px 0;"><strong>Email:</strong> {email}</p>
                    </div>

                    {pilot_section}

                    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f39c12;">
                        <h3 style="color: #856404; margin-top: 0;">⏰ What happens next?</h3>
                        <ol style="margin: 10px 0; padding-left: 20px; color: #856404;">
                            <li style="margin: 8px 0;">We'll review your request (usually within 2-3 business days)</li>
                            <li style="margin: 8px 0;">You'll receive a personal email from our team with next steps</li>
                            <li style="margin: 8px 0;">If approved, we'll provide access credentials and onboarding materials</li>
                        </ol>
                    </div>

                    <p>In the meantime, you can learn more about PhysiologicPRISM:</p>
                    <ul style="line-height: 2;">
                        <li>📚 <a href="{APP_URL}/pilot-program" style="color: #1a5f5a;">Learn about our Pilot Program</a></li>
                        <li>🔒 <a href="{APP_URL}/homepage#security" style="color: #1a5f5a;">Security & Compliance</a></li>
                        <li>📖 <a href="{APP_URL}/blog" style="color: #1a5f5a;">Read our Blog</a></li>
                    </ul>

                    <p style="margin-top: 30px;">If you have any questions, feel free to reply to this email.</p>

                    <p style="margin-top: 20px;">Best regards,<br>
                    <strong>The PhysiologicPRISM Team</strong></p>

                    <div class="footer">
                        <p>This email was sent because you requested early access to PhysiologicPRISM</p>
                        <p>Support: {SUPPORT_EMAIL}</p>
                        <p>© 2025 {APP_NAME}. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=email,
            subject=f"Early Access Request Received - PhysiologicPRISM",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_early_access_confirmation: {str(e)}")
        return False


def send_invoice_email(invoice_data: Dict[str, Any], pdf_base64: Optional[str] = None) -> bool:
    """
    Send invoice email to user.

    Args:
        invoice_data: Dictionary containing invoice information
        pdf_base64: Optional base64 encoded PDF content

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Format invoice date
        invoice_date = invoice_data.get('invoice_date', '')
        if hasattr(invoice_date, 'strftime'):
            invoice_date = invoice_date.strftime('%d-%b-%Y')
        elif invoice_date:
            invoice_date = str(invoice_date)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #0575e6 0%, #021b79 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .invoice-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #0575e6; }}
                .info-row {{ margin: 10px 0; padding: 10px 0; border-bottom: 1px solid #eee; }}
                .label {{ font-weight: bold; color: #0575e6; display: inline-block; width: 150px; }}
                .amount {{ font-size: 24px; font-weight: bold; color: #0575e6; text-align: center; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧾 Invoice from {APP_NAME}</h1>
                </div>
                <div class="content">
                    <p>Dear {invoice_data.get('customer_name')},</p>
                    <p>Thank you for your payment! Please find your invoice details below.</p>

                    <div class="invoice-box">
                        <div class="info-row">
                            <span class="label">Invoice Number:</span>
                            <span>{invoice_data.get('invoice_number')}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Date:</span>
                            <span>{invoice_date}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Description:</span>
                            <span>{invoice_data.get('description')}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Payment ID:</span>
                            <span>{invoice_data.get('payment_id')}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Base Amount:</span>
                            <span>₹{invoice_data.get('base_amount', 0):.2f}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">GST ({invoice_data.get('gst_rate', 18)}%):</span>
                            <span>₹{(invoice_data.get('cgst', 0) + invoice_data.get('sgst', 0) + invoice_data.get('igst', 0)):.2f}</span>
                        </div>

                        <div class="amount">
                            Total: ₹{invoice_data.get('total_amount', 0):.2f}
                        </div>
                    </div>

                    <p>The invoice PDF is attached to this email for your records.</p>

                    <div class="footer">
                        <p>{invoice_data.get('business_name', 'PhysiologicPRISM')}</p>
                        <p>GSTIN: {invoice_data.get('business_gstin', 'N/A')} | PAN: {invoice_data.get('business_pan', 'N/A')}</p>
                        <p>Questions? Contact us at {SUPPORT_EMAIL}</p>
                        <p>© 2025 {APP_NAME}. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        # Prepare email parameters
        params = {
            "from": FROM_EMAIL,
            "to": [invoice_data.get('customer_email', invoice_data.get('user_id'))],
            "subject": f"Invoice {invoice_data.get('invoice_number')} - {APP_NAME}",
            "html": html,
        }

        # Add PDF attachment if provided
        if pdf_base64:
            params["attachments"] = [{
                "filename": f"{invoice_data.get('invoice_number', 'invoice')}.pdf",
                "content": pdf_base64,
            }]

        response = resend.Emails.send(params)
        logger.info(f"Invoice email sent for {invoice_data.get('invoice_number')} to {invoice_data.get('customer_email', invoice_data.get('user_id'))}")
        return True

    except Exception as e:
        logger.error(f"Error in send_invoice_email: {str(e)}")
        return False


def send_blog_lead_notification(lead_data: Dict[str, Any]) -> bool:
    """
    Send notification to super admin when new blog lead is captured.

    Args:
        lead_data: Dictionary containing lead information
            - email: str
            - name: str (optional)
            - source: str (blog_newsletter, coming_soon_page, etc.)
            - post_slug: str
            - created_at: timestamp

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Determine source label and icon
        source = lead_data.get('source', 'unknown')
        source_labels = {
            'blog_newsletter': ('📧 Newsletter Signup', '#667eea'),
            'coming_soon_page': ('🚀 Waitlist Signup', '#f093fb'),
            'blog_download': ('📥 Lead Magnet', '#27ae60'),
            'blog_trial_cta': ('⚡ Trial CTA Click', '#e74c3c')
        }
        source_label, source_color = source_labels.get(source, ('📝 Blog Lead', '#667eea'))

        # Format post title
        post_slug = lead_data.get('post_slug', 'unknown')
        post_display = post_slug.replace('-', ' ').title() if post_slug != 'waitlist' else 'Waitlist Page'

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, {source_color} 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .source-badge {{ background: rgba(255, 255, 255, 0.2); color: white; padding: 8px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; margin-bottom: 15px; display: inline-block; }}
                .info-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {source_color}; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: {source_color}; }}
                .stats-box {{ background: #e8f5e9; border-left: 4px solid #27ae60; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: {source_color}; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="source-badge">{source_label}</div>
                    <h1>New Blog Lead Captured!</h1>
                </div>
                <div class="content">
                    <p>Dear {SUPER_ADMIN_NAME},</p>
                    <p>Great news! A new lead has been captured from your blog.</p>

                    <div class="info-box">
                        <h3 style="color: {source_color}; margin-top: 0;">Lead Information</h3>
                        <div class="info-row"><span class="label">Email:</span> {lead_data.get('email', 'N/A')}</div>
                        <div class="info-row"><span class="label">Name:</span> {lead_data.get('name') or 'Not provided'}</div>
                        <div class="info-row"><span class="label">Source:</span> {source_label}</div>
                        <div class="info-row"><span class="label">First Seen:</span> {post_display}</div>
                        <div class="info-row"><span class="label">Captured At:</span> {lead_data.get('created_at', 'N/A')}</div>
                    </div>

                    <div class="stats-box">
                        <p style="margin: 0; color: #27ae60;"><strong>💡 Quick Tip:</strong></p>
                        <p style="margin: 5px 0 0 0; color: #2c3e50;">This lead is interested in your content. Follow up within 24 hours for best conversion rates!</p>
                    </div>

                    <p style="text-align: center;">
                        <a href="{APP_URL}/super_admin_dashboard/blog-leads" class="button">View All Leads</a>
                    </p>

                    <div class="footer">
                        <p>This is an automated notification from {APP_NAME}</p>
                        <p>Blog Lead Capture System</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return send_email(
            to=SUPER_ADMIN_EMAIL,
            subject=f"{source_label}: {lead_data.get('email')} - {APP_NAME}",
            html=html
        )

    except Exception as e:
        logger.error(f"Error in send_blog_lead_notification: {str(e)}")
        return False
