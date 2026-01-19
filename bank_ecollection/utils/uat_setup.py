# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import os
from bank_ecollection.api.encryption import generate_key_pair


@frappe.whitelist()
def setup_uat_environment():
	"""Setup UAT environment for ICICI testing"""
	try:
		# Get or create ICICI Settings
		settings = frappe.get_single("ICICI Settings")
		
		# Configure UAT environment
		settings.environment = "UAT"
		settings.enable_integration = 1
		settings.enable_customer_integration = 1
		settings.enable_supplier_integration = 1
		settings.auto_create_payment_entry = 1
		settings.auto_submit_payment_entry = 0  # Keep draft for testing
		
		# Set UAT URLs (will be auto-populated by validation)
		settings.bene_upload_url = ""
		settings.enquiry_url = ""
		
		# Set UAT webhook IPs (will be auto-populated by validation)
		settings.webhook_ip_whitelist = ""
		
		# Set webhook credentials for testing
		if not settings.webhook_username:
			settings.webhook_username = "icici_webhook_user"
		if not settings.get_password("webhook_password"):
			settings.set("webhook_password", "icici_webhook_pass_123")
		
		# Set default company if available
		if not settings.default_company:
			companies = frappe.get_all("Company", limit=1)
			if companies:
				settings.default_company = companies[0].name
		
		# Generate encryption keys if not exists
		key_result = setup_encryption_keys()
		if key_result.get("success"):
			settings.public_key_path = key_result["public_key_path"]
			settings.private_key_path = key_result["private_key_path"]
		
		# Save settings (this will trigger validation and set default URLs/IPs)
		settings.save(ignore_permissions=True)
		
		return {
			"success": True,
			"message": "UAT environment setup completed successfully",
			"settings": {
				"environment": settings.environment,
				"bene_upload_url": settings.bene_upload_url,
				"enquiry_url": settings.enquiry_url,
				"webhook_ips": settings.webhook_ip_whitelist,
				"encryption_keys": key_result.get("success", False)
			}
		}
		
	except Exception as e:
		frappe.log_error(f"UAT Setup Error: {str(e)}")
		return {"success": False, "message": str(e)}


def setup_encryption_keys():
	"""Generate RSA encryption keys for ICICI integration"""
	try:
		# Create keys directory if not exists
		keys_dir = os.path.join(frappe.get_site_path(), "private", "files", "icici_keys")
		os.makedirs(keys_dir, exist_ok=True)
		
		public_key_path = os.path.join(keys_dir, "icici_public_key.pem")
		private_key_path = os.path.join(keys_dir, "icici_private_key.pem")
		
		# Generate keys if they don't exist
		if not os.path.exists(public_key_path) or not os.path.exists(private_key_path):
			result = generate_key_pair()
			
			if result.get("success"):
				# Save keys to files
				with open(public_key_path, 'w') as f:
					f.write(result["public_key"])
				
				with open(private_key_path, 'w') as f:
					f.write(result["private_key"])
				
				# Set proper permissions
				os.chmod(public_key_path, 0o644)
				os.chmod(private_key_path, 0o600)
				
				frappe.logger().info(f"Generated ICICI encryption keys at {keys_dir}")
		
		return {
			"success": True,
			"public_key_path": public_key_path,
			"private_key_path": private_key_path
		}
		
	except Exception as e:
		frappe.log_error(f"Encryption Key Setup Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def create_test_customer():
	"""Create a test customer for virtual account testing"""
	try:
		# Check if test customer already exists
		if frappe.db.exists("Customer", "TEST-CUSTOMER-001"):
			return {
				"success": True,
				"message": "Test customer already exists",
				"customer": "TEST-CUSTOMER-001"
			}
		
		# Get default company
		settings = frappe.get_single("ICICI Settings")
		company = settings.default_company or frappe.get_all("Company", limit=1)[0].name
		
		# Create test customer
		customer = frappe.new_doc("Customer")
		customer.customer_name = "Test Customer for ICICI Integration"
		customer.customer_type = "Individual"
		customer.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
		customer.territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
		customer.company = company
		
		# Add contact details
		customer.email_id = "test.customer@example.com"
		customer.mobile_no = "9876543210"
		
		customer.insert(ignore_permissions=True)
		
		frappe.logger().info(f"Created test customer: {customer.name}")
		
		return {
			"success": True,
			"message": f"Test customer created: {customer.name}",
			"customer": customer.name
		}
		
	except Exception as e:
		frappe.log_error(f"Test Customer Creation Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def test_virtual_account_creation():
	"""Test virtual account creation for test customer"""
	try:
		# Create test customer if not exists
		customer_result = create_test_customer()
		if not customer_result.get("success"):
			return customer_result
		
		customer_name = customer_result["customer"]
		
		# Test virtual account creation
		from bank_ecollection.api.bene_upload import create_virtual_account
		
		# Get customer document
		customer = frappe.get_doc("Customer", customer_name)
		
		# Call virtual account creation
		result = create_virtual_account(customer, "after_insert")
		
		return {
			"success": True,
			"message": "Virtual account creation test completed",
			"customer": customer_name,
			"va_result": result
		}
		
	except Exception as e:
		frappe.log_error(f"Virtual Account Test Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def test_webhook_endpoint():
	"""Test webhook endpoint with sample data"""
	try:
		from bank_ecollection.api.intimation_webhook import test_webhook_endpoint
		
		result = test_webhook_endpoint()
		
		return {
			"success": True,
			"message": "Webhook endpoint test completed",
			"test_result": result
		}
		
	except Exception as e:
		frappe.log_error(f"Webhook Test Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_uat_status():
	"""Get current UAT setup status"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		# Check encryption keys
		keys_exist = (
			settings.public_key_path and os.path.exists(settings.public_key_path) and
			settings.private_key_path and os.path.exists(settings.private_key_path)
		)
		
		# Check virtual accounts
		va_count = frappe.db.count("ICICI Virtual Account")
		
		# Check payment intimations
		pi_count = frappe.db.count("ICICI Payment Intimation")
		
		return {
			"success": True,
			"status": {
				"environment": settings.environment,
				"integration_enabled": settings.enable_integration,
				"bene_upload_url": settings.bene_upload_url,
				"enquiry_url": settings.enquiry_url,
				"webhook_ips": settings.webhook_ip_whitelist,
				"encryption_keys_exist": keys_exist,
				"virtual_accounts_count": va_count,
				"payment_intimations_count": pi_count,
				"default_company": settings.default_company
			}
		}
		
	except Exception as e:
		frappe.log_error(f"UAT Status Check Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def run_complete_uat_test():
	"""Run complete UAT test suite"""
	try:
		results = {}
		
		# 1. Setup UAT environment
		results["setup"] = setup_uat_environment()
		
		# 2. Test encryption
		from bank_ecollection.api.encryption import test_encryption
		results["encryption"] = test_encryption()
		
		# 3. Test virtual account creation
		results["virtual_account"] = test_virtual_account_creation()
		
		# 4. Test webhook endpoint
		results["webhook"] = test_webhook_endpoint()
		
		# 5. Get final status
		results["final_status"] = get_uat_status()
		
		# Count successes
		success_count = sum(1 for result in results.values() if result.get("success"))
		total_tests = len(results)
		
		return {
			"success": success_count == total_tests,
			"message": f"UAT Test Suite: {success_count}/{total_tests} tests passed",
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Complete UAT Test Error: {str(e)}")
		return {"success": False, "message": str(e)}
