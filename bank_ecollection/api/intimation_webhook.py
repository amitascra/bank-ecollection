# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import json
from bank_ecollection.api.encryption import decrypt_response


@frappe.whitelist(allow_guest=True)
def handle_payment_notification():
	"""
	ICICI Bank webhook endpoint for payment notifications
	This endpoint receives real-time payment notifications from ICICI Bank
	"""
	try:
		# Validate request
		if not validate_webhook_request():
			frappe.throw("Unauthorized access", frappe.AuthenticationError)
		
		# Get payment data from request
		payment_data = get_payment_data_from_request()
		
		if not payment_data:
			return {"Status": "Reject", "Remarks": "Invalid payment data"}
		
		# Create Payment Intimation record
		intimation = create_payment_intimation_record(payment_data)
		
		# Process payment if auto-processing is enabled
		settings = frappe.get_single("ICICI Settings")
		if settings.auto_create_payment_entry:
			try:
				success = intimation.process_payment()
				if success:
					frappe.logger().info(f"Payment processed successfully for UTR: {intimation.utr_number}")
				else:
					frappe.logger().warning(f"Payment processing failed for UTR: {intimation.utr_number}")
			except Exception as e:
				frappe.log_error(f"Auto-processing failed for UTR {intimation.utr_number}: {str(e)}")
		
		return {"Status": "Accept", "Remarks": "Payment notification processed successfully"}
		
	except frappe.AuthenticationError:
		frappe.logger().warning(f"Unauthorized webhook access from IP: {frappe.local.request_ip}")
		return {"Status": "Reject", "Remarks": "Unauthorized access"}
	except Exception as e:
		frappe.log_error(f"Payment Notification Processing Error: {str(e)}")
		return {"Status": "Reject", "Remarks": "Processing failed"}


def validate_webhook_request():
	"""Validate incoming webhook request"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		# Check if integration is enabled
		if not settings.enable_integration:
			return False
		
		# Validate IP address if whitelist is configured
		client_ip = frappe.local.request_ip
		if not settings.validate_webhook_ip(client_ip):
			frappe.logger().warning(f"Webhook request from non-whitelisted IP: {client_ip}")
			return False
		
		# Validate authentication if configured
		if settings.webhook_username and settings.webhook_password:
			auth_header = frappe.get_request_header("Authorization")
			if not validate_basic_auth(auth_header, settings):
				return False
		
		return True
		
	except Exception as e:
		frappe.log_error(f"Webhook Validation Error: {str(e)}")
		return False


def validate_basic_auth(auth_header, settings):
	"""Validate basic authentication"""
	try:
		if not auth_header or not auth_header.startswith("Basic "):
			return False
		
		import base64
		encoded_credentials = auth_header[6:]  # Remove "Basic " prefix
		decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
		username, password = decoded_credentials.split(':', 1)
		
		webhook_creds = settings.get_webhook_credentials()
		return (username == webhook_creds["username"] and 
				password == webhook_creds["password"])
		
	except Exception:
		return False


def get_payment_data_from_request():
	"""Extract payment data from webhook request"""
	try:
		# Get raw data from request
		if frappe.request.method == "POST":
			if frappe.request.content_type and "application/json" in frappe.request.content_type:
				raw_data = frappe.request.get_json()
			else:
				raw_data = frappe.local.form_dict
		else:
			raw_data = frappe.local.form_dict
		
		if not raw_data:
			return None
		
		# Decrypt if encrypted
		settings = frappe.get_single("ICICI Settings")
		payment_data = decrypt_response(raw_data, settings)
		
		# Validate required fields
		required_fields = ["VirtualID", "UTRNumber", "TransactionAmount", "TransactionDateandTime"]
		for field in required_fields:
			if field not in payment_data:
				frappe.logger().warning(f"Missing required field in payment notification: {field}")
				return None
		
		return payment_data
		
	except Exception as e:
		frappe.log_error(f"Payment Data Extraction Error: {str(e)}")
		return None


def create_payment_intimation_record(payment_data):
	"""Create ICICI Payment Intimation record"""
	try:
		# Check for duplicate UTR
		existing = frappe.db.exists("ICICI Payment Intimation", {"utr_number": payment_data.get("UTRNumber")})
		if existing:
			frappe.logger().warning(f"Duplicate payment notification for UTR: {payment_data.get('UTRNumber')}")
			return frappe.get_doc("ICICI Payment Intimation", existing)
		
		# Create new intimation record
		intimation = frappe.new_doc("ICICI Payment Intimation")
		intimation.virtual_account_number = payment_data.get("VirtualID")
		intimation.utr_number = payment_data.get("UTRNumber")
		intimation.transaction_amount = float(payment_data.get("TransactionAmount", 0))
		intimation.payment_mode = payment_data.get("PaymentMode", "")
		intimation.transaction_date = parse_transaction_date(payment_data.get("TransactionDateandTime"))
		intimation.remitter_name = payment_data.get("RemitterName", "")[:100]
		intimation.remitter_account = payment_data.get("RemitterAccountNo", "")
		intimation.remitter_ifsc = payment_data.get("RemitterIFSC", "")
		intimation.remitter_bank = payment_data.get("RemitterBankName", "")
		intimation.bank_response = payment_data
		intimation.status = "Received"
		
		intimation.insert(ignore_permissions=True)
		frappe.db.commit()
		
		frappe.logger().info(f"Payment intimation created: {intimation.name} for UTR: {intimation.utr_number}")
		return intimation
		
	except Exception as e:
		frappe.log_error(f"Payment Intimation Creation Error: {str(e)}")
		raise


def parse_transaction_date(date_string):
	"""Parse transaction date from ICICI format"""
	try:
		if not date_string:
			return frappe.utils.now()
		
		# ICICI typically sends date in format: "DD-MM-YYYY HH:MM:SS" or "YYYY-MM-DD HH:MM:SS"
		import datetime
		
		# Try different date formats
		formats = [
			"%d-%m-%Y %H:%M:%S",
			"%Y-%m-%d %H:%M:%S",
			"%d/%m/%Y %H:%M:%S",
			"%Y/%m/%d %H:%M:%S",
			"%d-%m-%Y",
			"%Y-%m-%d"
		]
		
		for fmt in formats:
			try:
				parsed_date = datetime.datetime.strptime(date_string, fmt)
				return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
			except ValueError:
				continue
		
		# If all formats fail, use current time
		frappe.logger().warning(f"Could not parse transaction date: {date_string}")
		return frappe.utils.now()
		
	except Exception as e:
		frappe.log_error(f"Date Parsing Error: {str(e)}")
		return frappe.utils.now()


@frappe.whitelist()
def test_webhook_endpoint():
	"""Test webhook endpoint with sample data"""
	try:
		# Sample ICICI payment notification data
		test_data = {
			"VirtualID": "TEST123456789",
			"UTRNumber": f"TEST{frappe.utils.random_string(10)}",
			"TransactionAmount": "1000.00",
			"PaymentMode": "NEFT",
			"TransactionDateandTime": frappe.utils.now(),
			"RemitterName": "Test Remitter",
			"RemitterAccountNo": "1234567890",
			"RemitterIFSC": "ICIC0001234",
			"RemitterBankName": "ICICI Bank"
		}
		
		# Simulate webhook call
		frappe.local.form_dict = test_data
		frappe.local.request_ip = "127.0.0.1"
		
		# Process notification
		result = handle_payment_notification()
		
		return {
			"success": True,
			"message": "Webhook test completed",
			"result": result,
			"test_data": test_data
		}
		
	except Exception as e:
		frappe.log_error(f"Webhook Test Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_webhook_logs(limit=50):
	"""Get recent webhook processing logs"""
	try:
		# Get recent payment intimations
		intimations = frappe.get_all(
			"ICICI Payment Intimation",
			fields=[
				"name", "utr_number", "virtual_account_number", 
				"transaction_amount", "status", "creation", "error_message"
			],
			order_by="creation desc",
			limit=limit
		)
		
		# Get error logs
		error_logs = frappe.get_all(
			"Error Log",
			filters={
				"method": ["like", "%intimation_webhook%"]
			},
			fields=["name", "creation", "error"],
			order_by="creation desc",
			limit=20
		)
		
		return {
			"success": True,
			"intimations": intimations,
			"error_logs": error_logs
		}
		
	except Exception as e:
		frappe.log_error(f"Webhook Logs Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def reprocess_failed_intimations():
	"""Reprocess failed payment intimations"""
	try:
		failed_intimations = frappe.get_all(
			"ICICI Payment Intimation",
			filters={"status": "Failed"},
			fields=["name"]
		)
		
		processed = 0
		still_failed = 0
		
		for intimation_data in failed_intimations:
			try:
				intimation = frappe.get_doc("ICICI Payment Intimation", intimation_data.name)
				if intimation.retry_processing():
					processed += 1
				else:
					still_failed += 1
			except Exception as e:
				frappe.log_error(f"Reprocessing error for {intimation_data.name}: {str(e)}")
				still_failed += 1
		
		return {
			"success": True,
			"message": f"Reprocessed {processed} intimations, {still_failed} still failed",
			"processed": processed,
			"still_failed": still_failed
		}
		
	except Exception as e:
		frappe.log_error(f"Reprocessing Error: {str(e)}")
		return {"success": False, "message": str(e)}
