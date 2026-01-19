# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
	"""Get context for ICICI API connection test page"""
	context.title = _("Test ICICI API Connection")
	context.show_sidebar = True
	
	# Check if user has permission
	if not frappe.has_permission("ICICI Settings", "read"):
		frappe.throw(_("You don't have permission to access this page"))
	
	return context


@frappe.whitelist()
def test_connection():
	"""Test ICICI API connection"""
	try:
		from bank_ecollection.bank_e_collection.doctype.icici_settings.icici_settings import test_api_connection
		result = test_api_connection()
		return result
	except Exception as e:
		frappe.log_error(f"ICICI Connection Test Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def test_encryption():
	"""Test encryption functionality"""
	try:
		from bank_ecollection.api.encryption import test_encryption
		result = test_encryption()
		return result
	except Exception as e:
		frappe.log_error(f"ICICI Encryption Test Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def test_virtual_account_creation():
	"""Test virtual account creation"""
	try:
		from bank_ecollection.api.bene_upload import create_virtual_account
		
		# Get a test customer
		test_customer = frappe.get_all("Customer", limit=1)
		if not test_customer:
			return {"success": False, "message": "No customers found for testing"}
		
		customer = frappe.get_doc("Customer", test_customer[0].name)
		result = create_virtual_account(customer, "test")
		return result
	except Exception as e:
		frappe.log_error(f"Virtual Account Test Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def test_webhook_endpoint():
	"""Test webhook endpoint with sample data"""
	try:
		from bank_ecollection.api.intimation_webhook import test_webhook_endpoint
		result = test_webhook_endpoint()
		return result
	except Exception as e:
		frappe.log_error(f"Webhook Test Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_settings_status():
	"""Get ICICI settings status"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		status = {
			"environment": settings.environment,
			"integration_enabled": settings.enable_integration,
			"client_code": bool(settings.client_code),
			"api_key": bool(settings.get_password("api_key")),
			"public_key": bool(settings.public_key_path),
			"private_key": bool(settings.private_key_path),
			"webhook_configured": bool(settings.webhook_username and settings.get_password("webhook_password")),
			"default_company": bool(settings.default_company),
			"default_bank_account": bool(settings.default_bank_account),
			"bene_upload_url": settings.bene_upload_url,
			"enquiry_url": settings.enquiry_url,
			"webhook_ips": settings.webhook_ip_whitelist
		}
		
		return {"success": True, "status": status}
		
	except Exception as e:
		frappe.log_error(f"ICICI Settings Status Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_integration_summary():
	"""Get integration summary for debugging"""
	try:
		# Get counts
		va_count = frappe.db.count("ICICI Virtual Account")
		pi_count = frappe.db.count("ICICI Payment Intimation")
		bt_count = frappe.db.count("Bank Transaction", {"description": ["like", "%ICICI%"]})
		pe_count = frappe.db.count("Payment Entry", {"reference_no": ["like", "%ICICI%"]})
		
		# Get recent activity
		recent_vas = frappe.get_all("ICICI Virtual Account", 
			fields=["name", "virtual_account_number", "party", "status", "creation"],
			order_by="creation desc", limit=5)
		
		recent_pis = frappe.get_all("ICICI Payment Intimation",
			fields=["name", "utr_number", "transaction_amount", "status", "creation"],
			order_by="creation desc", limit=5)
		
		return {
			"success": True,
			"summary": {
				"counts": {
					"virtual_accounts": va_count,
					"payment_intimations": pi_count,
					"bank_transactions": bt_count,
					"payment_entries": pe_count
				},
				"recent_activity": {
					"virtual_accounts": recent_vas,
					"payment_intimations": recent_pis
				}
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Integration Summary Error: {str(e)}")
		return {"success": False, "message": str(e)}
