# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from bank_ecollection.api.encryption import encrypt_request, decrypt_response
from bank_ecollection.utils.virtual_account import generate_virtual_account_number


@frappe.whitelist()
def create_virtual_account(doc, method=None):
	"""
	ERPNext Customer/Supplier integration hook
	Creates virtual account when Customer/Supplier is created
	"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		if not settings.is_integration_enabled(doc.doctype):
			return
		
		# Generate virtual account number
		va_number = generate_virtual_account_number(doc, settings)
		
		# Check if virtual account already exists
		existing_va = frappe.db.get_value(
			"ICICI Virtual Account",
			{
				"party_type": doc.doctype,
				"party": doc.name,
				"company": settings.default_company
			},
			"name"
		)
		
		if existing_va:
			frappe.logger().info(f"Virtual Account already exists for {doc.doctype} {doc.name}: {existing_va}")
			return
		
		# Prepare API payload
		payload = prepare_bene_upload_payload(doc, va_number, settings)
		
		# Call ICICI API
		response = call_bene_upload_api(payload, settings)
		
		if response.get("successFlag") == "1":
			# Create Virtual Account record
			create_virtual_account_record(doc, va_number, response, settings)
			frappe.msgprint(f"Virtual Account {va_number} created for {doc.name}")
		else:
			frappe.log_error(f"ICICI Bene Upload Failed for {doc.name}: {response.get('errMsg')}")
			
	except Exception as e:
		frappe.log_error(f"Virtual Account Creation Error for {doc.name}: {str(e)}")


@frappe.whitelist()
def update_virtual_account(doc, method=None):
	"""
	ERPNext Customer/Supplier update hook
	Updates virtual account when Customer/Supplier is updated
	"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		if not settings.is_integration_enabled(doc.doctype):
			return
		
		# Find existing virtual account
		va = frappe.db.get_value(
			"ICICI Virtual Account",
			{
				"party_type": doc.doctype,
				"party": doc.name,
				"company": settings.default_company
			},
			["name", "virtual_account_number"],
			as_dict=True
		)
		
		if not va:
			# Create new virtual account if doesn't exist
			create_virtual_account(doc, method)
			return
		
		# Update existing virtual account
		payload = prepare_bene_update_payload(doc, va.virtual_account_number, settings)
		response = call_bene_upload_api(payload, settings)
		
		if response.get("successFlag") == "1":
			# Update Virtual Account record
			va_doc = frappe.get_doc("ICICI Virtual Account", va.name)
			va_doc.bank_response = response
			va_doc.last_sync_date = frappe.utils.now()
			va_doc.status = "Active"
			va_doc.save(ignore_permissions=True)
		else:
			frappe.log_error(f"ICICI Bene Update Failed for {doc.name}: {response.get('errMsg')}")
			
	except Exception as e:
		frappe.log_error(f"Virtual Account Update Error for {doc.name}: {str(e)}")


def prepare_bene_upload_payload(party_doc, va_number, settings):
	"""Prepare payload for ICICI Bene Upload API"""
	
	# Get party address details
	address_details = get_party_address(party_doc)
	
	payload = {
		"vaCustomerPart": settings.client_code,
		"vaNumber": va_number,
		"vaBuyerName": party_doc.get("customer_name") or party_doc.get("supplier_name"),
		"vaBuyerAddress1": address_details.get("address_line1", "")[:50],
		"vaBuyerAddress2": address_details.get("address_line2", "")[:50],
		"vaBuyerCity": address_details.get("city", "")[:25],
		"vaBuyerState": address_details.get("state", "")[:25],
		"vaBuyerPincode": address_details.get("pincode", ""),
		"vaBuyerEmailId": party_doc.get("email_id", "")[:50],
		"vaBuyerMobileNo": party_doc.get("mobile_no", "")[:15],
		"vaStatus": "1"  # Active
	}
	
	return payload


def prepare_bene_update_payload(party_doc, va_number, settings):
	"""Prepare payload for updating existing beneficiary"""
	
	payload = prepare_bene_upload_payload(party_doc, va_number, settings)
	payload["vaStatus"] = "1"  # Keep active during update
	
	return payload


def call_bene_upload_api(payload, settings):
	"""Call ICICI Bene Upload API"""
	try:
		# Encrypt payload
		encrypted_payload = encrypt_request(payload, settings)
		
		# Prepare headers
		headers = settings.get_api_headers()
		
		# Make API call
		response = requests.post(
			settings.bene_upload_url,
			json=encrypted_payload,
			headers=headers,
			timeout=30
		)
		
		response.raise_for_status()
		
		# Decrypt and return response
		decrypted_response = decrypt_response(response.json(), settings)
		
		# Log API call
		frappe.logger().info(f"ICICI Bene Upload API Response: {decrypted_response}")
		
		return decrypted_response
		
	except requests.exceptions.RequestException as e:
		frappe.log_error(f"ICICI API Request Error: {str(e)}")
		return {"successFlag": "0", "errMsg": f"API Request Failed: {str(e)}"}
	except Exception as e:
		frappe.log_error(f"ICICI API Error: {str(e)}")
		return {"successFlag": "0", "errMsg": f"API Error: {str(e)}"}


def create_virtual_account_record(party_doc, va_number, response, settings):
	"""Create ICICI Virtual Account record in ERPNext"""
	try:
		va_doc = frappe.new_doc("ICICI Virtual Account")
		va_doc.virtual_account_number = va_number
		va_doc.party_type = party_doc.doctype
		va_doc.party = party_doc.name
		va_doc.company = settings.default_company
		va_doc.status = "Active"
		va_doc.bank_response = response
		va_doc.last_sync_date = frappe.utils.now()
		va_doc.insert(ignore_permissions=True)
		
		return va_doc
		
	except Exception as e:
		frappe.log_error(f"Virtual Account Record Creation Error: {str(e)}")
		raise


def get_party_address(party_doc):
	"""Get primary address details for party"""
	try:
		address_name = None
		
		if party_doc.doctype == "Customer":
			address_name = party_doc.get("customer_primary_address")
		elif party_doc.doctype == "Supplier":
			address_name = party_doc.get("supplier_primary_address")
		
		if address_name:
			address = frappe.get_doc("Address", address_name)
			return {
				"address_line1": address.address_line1 or "",
				"address_line2": address.address_line2 or "",
				"city": address.city or "",
				"state": address.state or "",
				"pincode": address.pincode or ""
			}
		
		return {}
		
	except Exception:
		return {}


@frappe.whitelist()
def manual_upload_beneficiary(party_type, party, company=None):
	"""Manually upload beneficiary to ICICI"""
	try:
		party_doc = frappe.get_doc(party_type, party)
		settings = frappe.get_single("ICICI Settings")
		
		if not company:
			company = settings.default_company
		
		# Check if virtual account already exists
		existing_va = frappe.db.get_value(
			"ICICI Virtual Account",
			{
				"party_type": party_type,
				"party": party,
				"company": company
			},
			"name"
		)
		
		if existing_va:
			return {"success": False, "message": f"Virtual Account already exists: {existing_va}"}
		
		# Generate virtual account number
		va_number = generate_virtual_account_number(party_doc, settings)
		
		# Prepare and call API
		payload = prepare_bene_upload_payload(party_doc, va_number, settings)
		response = call_bene_upload_api(payload, settings)
		
		if response.get("successFlag") == "1":
			# Create Virtual Account record
			va_doc = create_virtual_account_record(party_doc, va_number, response, settings)
			return {
				"success": True,
				"message": f"Virtual Account {va_number} created successfully",
				"virtual_account": va_doc.name
			}
		else:
			return {
				"success": False,
				"message": f"API Error: {response.get('errMsg', 'Unknown error')}"
			}
			
	except Exception as e:
		frappe.log_error(f"Manual Beneficiary Upload Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def bulk_upload_beneficiaries(party_type, filters=None):
	"""Bulk upload beneficiaries to ICICI"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		if not settings.is_integration_enabled(party_type):
			return {"success": False, "message": f"{party_type} integration is disabled"}
		
		# Get parties without virtual accounts
		existing_vas = frappe.get_all(
			"ICICI Virtual Account",
			filters={"party_type": party_type},
			fields=["party"]
		)
		existing_parties = [va.party for va in existing_vas]
		
		party_filters = {"name": ("not in", existing_parties)} if existing_parties else {}
		if filters:
			party_filters.update(filters)
		
		parties = frappe.get_all(party_type, filters=party_filters, fields=["name"])
		
		success_count = 0
		error_count = 0
		errors = []
		
		for party_data in parties:
			try:
				result = manual_upload_beneficiary(party_type, party_data.name)
				if result.get("success"):
					success_count += 1
				else:
					error_count += 1
					errors.append(f"{party_data.name}: {result.get('message')}")
			except Exception as e:
				error_count += 1
				errors.append(f"{party_data.name}: {str(e)}")
		
		return {
			"success": True,
			"message": f"Processed {len(parties)} parties. Success: {success_count}, Errors: {error_count}",
			"success_count": success_count,
			"error_count": error_count,
			"errors": errors[:10]  # Limit error list
		}
		
	except Exception as e:
		frappe.log_error(f"Bulk Beneficiary Upload Error: {str(e)}")
		return {"success": False, "message": str(e)}
