"""
Invoice Generator for Physio-Assist
====================================

GST-compliant invoice generation for Indian tax compliance.
Automatically generates invoices for all successful payments.

Indian GST Requirements:
- GSTIN number
- Invoice numbering (sequential)
- Tax breakdown (CGST + SGST or IGST)
- HSN/SAC code for services
- Customer details
- Payment method and date
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional
from io import BytesIO
from xhtml2pdf import pisa
# Firebase removed - using Azure Cosmos DB
from azure_cosmos_db import SERVER_TIMESTAMP

logger = logging.getLogger("app.invoice")

# Get Cosmos DB client
db = get_cosmos_db()

# Business details for invoice (get from environment or config)
BUSINESS_NAME = os.environ.get('BUSINESS_NAME', 'PhysiologicPRISM')
BUSINESS_ADDRESS = os.environ.get('BUSINESS_ADDRESS', 'India')
BUSINESS_GSTIN = os.environ.get('BUSINESS_GSTIN', 'N/A')  # Must be configured for production
BUSINESS_PAN = os.environ.get('BUSINESS_PAN', 'N/A')
BUSINESS_EMAIL = os.environ.get('BUSINESS_EMAIL', 'support@physiologicprism.com')
BUSINESS_PHONE = os.environ.get('BUSINESS_PHONE', '+91-XXXXXXXXXX')

# SAC Code for Software as a Service
SAC_CODE = '998314'  # Information technology software services


def generate_invoice_number() -> str:
    """
    Generate sequential invoice number.
    Format: INV-YYYY-NNNN

    Returns:
        str: Invoice number (e.g., INV-2025-0001)
    """
    try:
        # Get current year
        year = datetime.now().year

        # Get latest invoice for this year
        invoices_ref = db.collection('invoices')
        latest_invoices = (invoices_ref
                          .where('invoice_year', '==', year)
                          .order_by('invoice_sequence', direction='DESCENDING')
                          .limit(1)
                          .get())

        if latest_invoices:
            latest_invoice = list(latest_invoices)[0].to_dict()
            next_sequence = latest_invoice.get('invoice_sequence', 0) + 1
        else:
            next_sequence = 1

        # Format: INV-2025-0001
        invoice_number = f"INV-{year}-{next_sequence:04d}"
        return invoice_number

    except Exception as e:
        logger.error(f"Error generating invoice number: {e}")
        # Fallback to timestamp-based number
        timestamp = int(datetime.now().timestamp())
        return f"INV-{year}-{timestamp}"


def calculate_gst(amount: float, is_interstate: bool = False) -> Dict:
    """
    Calculate GST breakdown.

    Args:
        amount: Base amount in INR
        is_interstate: If True, use IGST (18%), else CGST+SGST (9%+9%)

    Returns:
        dict: GST breakdown with base_amount, cgst, sgst, igst, total_amount
    """
    gst_rate = 0.18  # 18% GST for IT services

    if is_interstate:
        # Interstate: IGST only
        igst = round(amount * gst_rate, 2)
        total = round(amount + igst, 2)
        return {
            'base_amount': amount,
            'cgst': 0,
            'sgst': 0,
            'igst': igst,
            'gst_rate': 18,
            'total_amount': total
        }
    else:
        # Intrastate: CGST + SGST
        cgst = round(amount * (gst_rate / 2), 2)
        sgst = round(amount * (gst_rate / 2), 2)
        total = round(amount + cgst + sgst, 2)
        return {
            'base_amount': amount,
            'cgst': cgst,
            'sgst': sgst,
            'igst': 0,
            'gst_rate': 18,
            'total_amount': total
        }


def create_invoice(
    user_id: str,
    payment_id: str,
    amount: float,
    plan_type: str,
    payment_method: str = 'Razorpay',
    transaction_type: str = 'subscription'
) -> Optional[Dict]:
    """
    Create and store invoice in Cosmos DB.

    Args:
        user_id: User's email
        payment_id: Razorpay payment ID
        amount: Payment amount in INR
        plan_type: Plan type (starter, professional, clinic, etc.)
        payment_method: Payment method used
        transaction_type: 'subscription' or 'token_purchase'

    Returns:
        dict: Invoice data or None if error
    """
    try:
        # Get user details
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            logger.error(f"User not found: {user_id}")
            return None

        user_data = user_doc.to_dict()

        # Generate invoice number
        invoice_number = generate_invoice_number()
        invoice_year = datetime.now().year

        # Extract sequence number from invoice_number (e.g., INV-2025-0042 -> 42)
        try:
            invoice_sequence = int(invoice_number.split('-')[-1])
        except:
            invoice_sequence = 0

        # Calculate GST (assuming intrastate for now - can be enhanced later)
        gst_breakdown = calculate_gst(amount, is_interstate=False)

        # Create invoice data
        invoice_data = {
            'invoice_number': invoice_number,
            'invoice_year': invoice_year,
            'invoice_sequence': invoice_sequence,
            'invoice_date': SERVER_TIMESTAMP,
            'user_id': user_id,
            'payment_id': payment_id,
            'transaction_type': transaction_type,

            # Customer details
            'customer_name': user_data.get('name', 'N/A'),
            'customer_email': user_data.get('email', user_id),
            'customer_phone': user_data.get('phone', 'N/A'),
            'customer_institute': user_data.get('institute', 'N/A'),

            # Business details
            'business_name': BUSINESS_NAME,
            'business_address': BUSINESS_ADDRESS,
            'business_gstin': BUSINESS_GSTIN,
            'business_pan': BUSINESS_PAN,
            'business_email': BUSINESS_EMAIL,
            'business_phone': BUSINESS_PHONE,

            # Payment details
            'plan_type': plan_type,
            'description': f"{plan_type.title()} Plan Subscription" if transaction_type == 'subscription' else f"{plan_type.title()} Token Purchase",
            'base_amount': gst_breakdown['base_amount'],
            'cgst': gst_breakdown['cgst'],
            'sgst': gst_breakdown['sgst'],
            'igst': gst_breakdown['igst'],
            'gst_rate': gst_breakdown['gst_rate'],
            'total_amount': gst_breakdown['total_amount'],
            'currency': 'INR',
            'payment_method': payment_method,
            'sac_code': SAC_CODE,

            # Status
            'status': 'paid',
            'created_at': SERVER_TIMESTAMP
        }

        # Store invoice in Cosmos DB
        invoice_ref = db.collection('invoices').document()
        invoice_ref.set(invoice_data)

        # Add invoice_id to data
        invoice_data['invoice_id'] = invoice_ref.id

        logger.info(f"Created invoice {invoice_number} for {user_id}: ₹{gst_breakdown['total_amount']}")

        return invoice_data

    except Exception as e:
        logger.error(f"Error creating invoice: {e}", exc_info=True)
        return None


def generate_invoice_html(invoice_data: Dict) -> str:
    """
    Generate HTML for invoice.

    Args:
        invoice_data: Invoice data dictionary

    Returns:
        str: HTML content
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 1cm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 12px;
                line-height: 1.6;
                color: #333;
            }}
            .invoice-container {{
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #3498db;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                color: #3498db;
                margin: 0;
                font-size: 28px;
            }}
            .header p {{
                margin: 5px 0;
                color: #7f8c8d;
            }}
            .invoice-details {{
                display: table;
                width: 100%;
                margin-bottom: 20px;
            }}
            .invoice-details .left,
            .invoice-details .right {{
                display: table-cell;
                width: 50%;
                vertical-align: top;
            }}
            .section-title {{
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
                font-size: 14px;
            }}
            .info-block {{
                margin-bottom: 20px;
            }}
            .info-block p {{
                margin: 3px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }}
            th {{
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }}
            .text-right {{
                text-align: right;
            }}
            .total-row {{
                background-color: #ecf0f1;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                text-align: center;
                color: #7f8c8d;
                font-size: 11px;
            }}
            .stamp {{
                margin-top: 40px;
                text-align: right;
            }}
        </style>
    </head>
    <body>
        <div class="invoice-container">
            <!-- Header -->
            <div class="header">
                <h1>TAX INVOICE</h1>
                <p>{invoice_data.get('business_name', 'PhysiologicPRISM')}</p>
                <p>{invoice_data.get('business_address', 'India')}</p>
                <p>GSTIN: {invoice_data.get('business_gstin', 'N/A')} | PAN: {invoice_data.get('business_pan', 'N/A')}</p>
                <p>Email: {invoice_data.get('business_email', 'support@physiologicprism.com')} | Phone: {invoice_data.get('business_phone', 'N/A')}</p>
            </div>

            <!-- Invoice Details -->
            <div class="invoice-details">
                <div class="left">
                    <div class="info-block">
                        <div class="section-title">Bill To:</div>
                        <p><strong>{invoice_data.get('customer_name', 'N/A')}</strong></p>
                        <p>{invoice_data.get('customer_institute', 'N/A')}</p>
                        <p>Email: {invoice_data.get('customer_email', 'N/A')}</p>
                        <p>Phone: {invoice_data.get('customer_phone', 'N/A')}</p>
                    </div>
                </div>
                <div class="right" style="text-align: right;">
                    <div class="info-block">
                        <p><strong>Invoice Number:</strong> {invoice_data.get('invoice_number', 'N/A')}</p>
                        <p><strong>Invoice Date:</strong> {datetime.now().strftime('%d-%b-%Y')}</p>
                        <p><strong>Payment ID:</strong> {invoice_data.get('payment_id', 'N/A')}</p>
                        <p><strong>Payment Method:</strong> {invoice_data.get('payment_method', 'Razorpay')}</p>
                    </div>
                </div>
            </div>

            <!-- Items Table -->
            <table>
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>SAC Code</th>
                        <th>Qty</th>
                        <th class="text-right">Rate (₹)</th>
                        <th class="text-right">Amount (₹)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{invoice_data.get('description', 'Subscription')}</td>
                        <td>{invoice_data.get('sac_code', '998314')}</td>
                        <td>1</td>
                        <td class="text-right">{invoice_data.get('base_amount', 0):.2f}</td>
                        <td class="text-right">{invoice_data.get('base_amount', 0):.2f}</td>
                    </tr>
                    <tr>
                        <td colspan="4" class="text-right"><strong>Subtotal:</strong></td>
                        <td class="text-right">₹{invoice_data.get('base_amount', 0):.2f}</td>
                    </tr>
    """

    # Add GST breakdown
    if invoice_data.get('igst', 0) > 0:
        html += f"""
                    <tr>
                        <td colspan="4" class="text-right">IGST ({invoice_data.get('gst_rate', 18)}%):</td>
                        <td class="text-right">₹{invoice_data.get('igst', 0):.2f}</td>
                    </tr>
        """
    else:
        html += f"""
                    <tr>
                        <td colspan="4" class="text-right">CGST ({invoice_data.get('gst_rate', 18)/2:.0f}%):</td>
                        <td class="text-right">₹{invoice_data.get('cgst', 0):.2f}</td>
                    </tr>
                    <tr>
                        <td colspan="4" class="text-right">SGST ({invoice_data.get('gst_rate', 18)/2:.0f}%):</td>
                        <td class="text-right">₹{invoice_data.get('sgst', 0):.2f}</td>
                    </tr>
        """

    html += f"""
                    <tr class="total-row">
                        <td colspan="4" class="text-right"><strong>Total Amount:</strong></td>
                        <td class="text-right"><strong>₹{invoice_data.get('total_amount', 0):.2f}</strong></td>
                    </tr>
                </tbody>
            </table>

            <!-- Amount in Words -->
            <p><strong>Amount in Words:</strong> {number_to_words(invoice_data.get('total_amount', 0))} Rupees Only</p>

            <!-- Terms & Conditions -->
            <div class="info-block">
                <div class="section-title">Terms & Conditions:</div>
                <p>1. This is a computer-generated invoice and does not require a physical signature.</p>
                <p>2. Payment is non-refundable except as per our refund policy.</p>
                <p>3. For any queries, please contact {invoice_data.get('business_email', 'support@physiologicprism.com')}</p>
            </div>

            <!-- Digital Stamp -->
            <div class="stamp">
                <p><strong>For {invoice_data.get('business_name', 'PhysiologicPRISM')}</strong></p>
                <p style="margin-top: 30px;">___________________</p>
                <p>Authorized Signatory</p>
            </div>

            <!-- Footer -->
            <div class="footer">
                <p>This is a computer-generated invoice. No signature required.</p>
                <p>Generated on {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def number_to_words(num: float) -> str:
    """Convert number to words (Indian numbering system)."""
    # Simplified version - can be enhanced with a proper library
    num = int(num)

    if num == 0:
        return "Zero"

    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]

    def convert_below_thousand(n):
        if n == 0:
            return ""
        elif n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        else:
            return ones[n // 100] + " Hundred" + (" " + convert_below_thousand(n % 100) if n % 100 != 0 else "")

    if num < 1000:
        return convert_below_thousand(num)
    elif num < 100000:  # Thousands
        return convert_below_thousand(num // 1000) + " Thousand" + (" " + convert_below_thousand(num % 1000) if num % 1000 != 0 else "")
    elif num < 10000000:  # Lakhs
        return convert_below_thousand(num // 100000) + " Lakh" + (" " + number_to_words(num % 100000) if num % 100000 != 0 else "")
    else:  # Crores
        return convert_below_thousand(num // 10000000) + " Crore" + (" " + number_to_words(num % 10000000) if num % 10000000 != 0 else "")


def generate_invoice_pdf(invoice_data: Dict) -> Optional[bytes]:
    """
    Generate PDF from invoice data.

    Args:
        invoice_data: Invoice data dictionary

    Returns:
        bytes: PDF file content or None if error
    """
    try:
        # Generate HTML
        html = generate_invoice_html(invoice_data)

        # Convert HTML to PDF
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)

        if pisa_status.err:
            logger.error(f"Error generating PDF: {pisa_status.err}")
            return None

        # Get PDF content
        pdf_content = pdf_buffer.getvalue()
        pdf_buffer.close()

        return pdf_content

    except Exception as e:
        logger.error(f"Error generating invoice PDF: {e}", exc_info=True)
        return None


def create_and_send_invoice(
    user_id: str,
    payment_id: str,
    amount: float,
    plan_type: str,
    payment_method: str = 'Razorpay',
    transaction_type: str = 'subscription'
) -> Optional[Dict]:
    """
    Create invoice, generate PDF, and send email notification.

    This is a convenience function that:
    1. Creates the invoice in Cosmos DB
    2. Generates the PDF
    3. Sends the invoice email via Resend

    Args:
        user_id: User's email
        payment_id: Razorpay payment ID
        amount: Payment amount in INR
        plan_type: Plan type (starter, professional, clinic, etc.)
        payment_method: Payment method used
        transaction_type: 'subscription' or 'token_purchase'

    Returns:
        dict: Invoice data or None if error
    """
    import base64

    try:
        # Step 1: Create the invoice
        invoice_data = create_invoice(
            user_id=user_id,
            payment_id=payment_id,
            amount=amount,
            plan_type=plan_type,
            payment_method=payment_method,
            transaction_type=transaction_type
        )

        if not invoice_data:
            logger.error(f"Failed to create invoice for {user_id}")
            return None

        # Step 2: Generate PDF
        pdf_content = generate_invoice_pdf(invoice_data)
        pdf_base64 = None

        if pdf_content:
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        else:
            logger.warning(f"Failed to generate PDF for invoice {invoice_data.get('invoice_number')}")

        # Step 3: Send email notification
        try:
            from email_service import send_invoice_email
            email_sent = send_invoice_email(invoice_data, pdf_base64)

            if email_sent:
                logger.info(f"Invoice email sent for {invoice_data.get('invoice_number')}")
            else:
                logger.warning(f"Failed to send invoice email for {invoice_data.get('invoice_number')}")
        except Exception as email_error:
            logger.warning(f"Error sending invoice email: {email_error}")

        return invoice_data

    except Exception as e:
        logger.error(f"Error in create_and_send_invoice: {e}", exc_info=True)
        return None
