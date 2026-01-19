# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ICICISettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Password | None
		auto_create_payment_entry: DF.Check
		auto_submit_payment_entry: DF.Check
		bene_upload_url: DF.Data | None
		client_code: DF.Data
		default_bank_account: DF.Link | None
		default_cash_account: DF.Link | None
		default_company: DF.Link | None
		enable_customer_integration: DF.Check
		enable_integration: DF.Check
		enable_supplier_integration: DF.Check
		enquiry_url: DF.Data | None
		environment: DF.Literal["UAT", "Production"]
		intimation_callback_url: DF.Data | None
		private_key_path: DF.Data | None
		public_key_path: DF.Data | None
		webhook_ip_whitelist: DF.Text | None
		webhook_password: DF.Password | None
		webhook_username: DF.Data | None
	# end: auto-generated types

	def validate(self):
		"""Validate ICICI Settings configuration"""
		self.set_default_urls()
		self.set_default_webhook_ips()
		self.validate_encryption_keys()
		self.set_callback_url()

	def set_default_urls(self):
		"""Set default API URLs based on environment"""
		if self.environment == "UAT":
			if not self.bene_upload_url:
				self.bene_upload_url = "https://uat-onprem-dmz-hybrid.icicibank.com/apibanking/live/corpapi/ixc/v2/beneupload"
			if not self.enquiry_url:
				self.enquiry_url = "https://uat-onprem-dmz-hybrid.icicibank.com/misenquiry/status"
		else:  # Production
			if not self.bene_upload_url:
				self.bene_upload_url = "https://apigw.icicibank.com/api/Corporate/CIB/v1/BeneUpload"
			if not self.enquiry_url:
				self.enquiry_url = "https://apigw.icicibank.com/api/Corporate/CIB/v1/Enquiry"

	def set_default_webhook_ips(self):
		"""Set default webhook IP whitelist based on environment"""
		if self.environment == "UAT":
			if not self.webhook_ip_whitelist:
				# UAT webhook source IPs
				self.webhook_ip_whitelist = "103.87.42.133, 103.87.43.222, 103.87.43.226"
		else:  # Production
			if not self.webhook_ip_whitelist:
				# Production webhook source IPs (to be updated when available)
				self.webhook_ip_whitelist = ""

	def validate_encryption_keys(self):
		"""Validate encryption key paths exist"""
		import os
		
		if self.public_key_path and not os.path.exists(self.public_key_path):
			frappe.throw(f"Public key file not found at: {self.public_key_path}")
		
		if self.private_key_path and not os.path.exists(self.private_key_path):
			frappe.throw(f"Private key file not found at: {self.private_key_path}")

	def set_callback_url(self):
		"""Set the callback URL for ICICI webhooks"""
		site_url = frappe.utils.get_url()
		self.intimation_callback_url = f"{site_url}/api/icici/intimation"

	def get_api_headers(self):
		"""Get standard API headers for ICICI requests"""
		return {
			"Content-Type": "application/json",
			"Accept": "application/json",
			"apikey": self.get_password("api_key")
		}

	def is_integration_enabled(self, party_type=None):
		"""Check if integration is enabled for specific party type"""
		if not self.enable_integration:
			return False
		
		if party_type == "Customer":
			return self.enable_customer_integration
		elif party_type == "Supplier":
			return self.enable_supplier_integration
		
		return True

	def get_webhook_credentials(self):
		"""Get webhook authentication credentials"""
		return {
			"username": self.webhook_username,
			"password": self.get_password("webhook_password")
		}

	def validate_webhook_ip(self, ip_address):
		"""Validate if IP address is whitelisted for webhooks"""
		if not self.webhook_ip_whitelist:
			return True  # No IP restriction
		
		allowed_ips = [ip.strip() for ip in self.webhook_ip_whitelist.split(",")]
		return ip_address in allowed_ips


@frappe.whitelist()
def get_icici_settings():
	"""Get ICICI Settings document"""
	return frappe.get_single("ICICI Settings")


@frappe.whitelist()
def test_api_connection():
	"""Test ICICI API connection with actual API call"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		if not settings.enable_integration:
			return {"success": False, "message": "Integration is disabled"}
		
		# Check required fields
		if not settings.client_code:
			return {"success": False, "message": "Client Code is required"}
		
		if not settings.get_password("api_key"):
			return {"success": False, "message": "API Key is required"}
		
		if not settings.enquiry_url:
			return {"success": False, "message": "Enquiry URL is required"}
		
		# Make actual API test call
		import requests
		import json
		
		# Prepare test request - using enquiry endpoint with minimal data
		headers = {
			"Content-Type": "application/json",
			"Accept": "application/json",
			"apikey": settings.get_password("api_key"),
			"clientcode": settings.client_code
		}
		
		# Test payload for enquiry endpoint
		test_payload = {
			"clientCode": settings.client_code,
			"enquiryType": "STATUS_CHECK"
		}
		
		# Make API call with timeout
		response = requests.post(
			settings.enquiry_url,
			headers=headers,
			json=test_payload,
			timeout=10,
			verify=True
		)
		
		# Check response
		if response.status_code == 200:
			try:
				response_data = response.json()
				return {
					"success": True, 
					"message": f"API connection successful. Status: {response.status_code}",
					"response": response_data
				}
			except json.JSONDecodeError:
				return {
					"success": True,
					"message": f"API connection successful. Status: {response.status_code} (Non-JSON response)"
				}
		elif response.status_code == 401:
			return {
				"success": False, 
				"message": "Authentication failed. Please check your API Key and Client Code."
			}
		elif response.status_code == 403:
			return {
				"success": False, 
				"message": "Access forbidden. Please check your API permissions."
			}
		else:
			return {
				"success": False, 
				"message": f"API call failed with status {response.status_code}: {response.text[:200]}"
			}
		
	except requests.exceptions.Timeout:
		return {"success": False, "message": "API request timed out. Please check the URL and network connectivity."}
	except requests.exceptions.ConnectionError:
		return {"success": False, "message": "Connection error. Please check the API URL and network connectivity."}
	except requests.exceptions.SSLError as e:
		return {"success": False, "message": f"SSL certificate error: {str(e)}"}
	except Exception as e:
		frappe.log_error(f"ICICI API Connection Test Failed: {str(e)}")
		return {"success": False, "message": f"Connection test failed: {str(e)}"}
