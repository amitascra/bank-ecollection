# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import hashlib
import time


def generate_virtual_account_number(party_doc, settings):
	"""Generate unique virtual account number for party"""
	try:
		# Get client code from settings
		client_code = settings.client_code
		
		# Create unique identifier based on party details
		party_identifier = f"{party_doc.doctype}_{party_doc.name}_{settings.default_company}"
		
		# Generate hash for uniqueness
		hash_object = hashlib.md5(party_identifier.encode())
		hash_hex = hash_object.hexdigest()
		
		# Take first 8 characters of hash
		unique_suffix = hash_hex[:8].upper()
		
		# Format: CLIENT_CODE + UNIQUE_SUFFIX (max 16 chars for ICICI)
		va_number = f"{client_code}{unique_suffix}"
		
		# Ensure it's within ICICI limits (typically 16 characters)
		if len(va_number) > 16:
			va_number = va_number[:16]
		
		# Check if this VA number already exists
		existing = frappe.db.exists("ICICI Virtual Account", {"virtual_account_number": va_number})
		
		if existing:
			# Add timestamp suffix if duplicate
			timestamp_suffix = str(int(time.time()))[-4:]
			va_number = f"{client_code}{unique_suffix[:-4]}{timestamp_suffix}"
		
		return va_number
		
	except Exception as e:
		frappe.log_error(f"Virtual Account Number Generation Error: {str(e)}")
		# Fallback to simple format
		timestamp = str(int(time.time()))[-8:]
		return f"{settings.client_code}{timestamp}"


def validate_virtual_account_number(va_number):
	"""Validate virtual account number format"""
	if not va_number:
		return False, "Virtual account number is required"
	
	if len(va_number) < 8 or len(va_number) > 16:
		return False, "Virtual account number must be between 8-16 characters"
	
	if not va_number.isalnum():
		return False, "Virtual account number must be alphanumeric"
	
	return True, "Valid"


def get_virtual_account_by_party(party_type, party, company=None):
	"""Get virtual account for a specific party"""
	try:
		filters = {
			"party_type": party_type,
			"party": party
		}
		
		if company:
			filters["company"] = company
		
		va = frappe.get_doc("ICICI Virtual Account", filters)
		return va
		
	except frappe.DoesNotExistError:
		return None
	except Exception as e:
		frappe.log_error(f"Virtual Account Retrieval Error: {str(e)}")
		return None


def get_party_from_virtual_account(va_number):
	"""Get party details from virtual account number"""
	try:
		va = frappe.get_doc("ICICI Virtual Account", {"virtual_account_number": va_number})
		return {
			"party_type": va.party_type,
			"party": va.party,
			"company": va.company,
			"status": va.status
		}
	except frappe.DoesNotExistError:
		return None
	except Exception as e:
		frappe.log_error(f"Party Retrieval from VA Error: {str(e)}")
		return None


def sync_virtual_account_status(va_number):
	"""Sync virtual account status with ICICI Bank"""
	try:
		from bank_ecollection.api.enquiry import query_virtual_account_status
		
		va = frappe.get_doc("ICICI Virtual Account", {"virtual_account_number": va_number})
		
		# Query ICICI for current status
		response = query_virtual_account_status(va_number)
		
		if response.get("successFlag") == "1":
			# Update local record
			va.bank_response = response
			va.last_sync_date = frappe.utils.now()
			
			# Update status based on response
			bank_status = response.get("vaStatus", "1")
			if bank_status == "1":
				va.status = "Active"
			elif bank_status == "0":
				va.status = "Inactive"
			else:
				va.status = "Suspended"
			
			va.save(ignore_permissions=True)
			return True, "Sync successful"
		else:
			error_msg = response.get("errMsg", "Unknown error")
			va.update_status("Error", error_msg)
			return False, error_msg
			
	except Exception as e:
		frappe.log_error(f"Virtual Account Sync Error: {str(e)}")
		return False, str(e)


def get_virtual_account_summary():
	"""Get summary of virtual accounts"""
	try:
		summary = frappe.db.sql("""
			SELECT 
				status,
				COUNT(*) as count,
				party_type
			FROM `tabICICI Virtual Account`
			GROUP BY status, party_type
			ORDER BY party_type, status
		""", as_dict=True)
		
		# Format summary
		result = {
			"total": 0,
			"by_status": {},
			"by_party_type": {}
		}
		
		for row in summary:
			result["total"] += row.count
			
			# By status
			if row.status not in result["by_status"]:
				result["by_status"][row.status] = 0
			result["by_status"][row.status] += row.count
			
			# By party type
			if row.party_type not in result["by_party_type"]:
				result["by_party_type"][row.party_type] = {}
			result["by_party_type"][row.party_type][row.status] = row.count
		
		return result
		
	except Exception as e:
		frappe.log_error(f"Virtual Account Summary Error: {str(e)}")
		return {"total": 0, "by_status": {}, "by_party_type": {}}


def cleanup_inactive_virtual_accounts(days=30):
	"""Cleanup virtual accounts that have been inactive for specified days"""
	try:
		cutoff_date = frappe.utils.add_days(frappe.utils.today(), -days)
		
		inactive_vas = frappe.get_all(
			"ICICI Virtual Account",
			filters={
				"status": "Inactive",
				"last_sync_date": ("<", cutoff_date)
			},
			fields=["name", "virtual_account_number", "party", "party_type"]
		)
		
		cleaned_count = 0
		for va in inactive_vas:
			try:
				# Check if there are any recent payment intimations
				recent_payments = frappe.db.count(
					"ICICI Payment Intimation",
					{
						"virtual_account_number": va.virtual_account_number,
						"transaction_date": (">", cutoff_date)
					}
				)
				
				if recent_payments == 0:
					frappe.delete_doc("ICICI Virtual Account", va.name)
					cleaned_count += 1
					
			except Exception as e:
				frappe.log_error(f"Error cleaning up VA {va.name}: {str(e)}")
		
		return {
			"success": True,
			"message": f"Cleaned up {cleaned_count} inactive virtual accounts",
			"cleaned_count": cleaned_count
		}
		
	except Exception as e:
		frappe.log_error(f"Virtual Account Cleanup Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_virtual_account_dashboard_data():
	"""Get dashboard data for virtual accounts"""
	try:
		# Get summary
		summary = get_virtual_account_summary()
		
		# Get recent activity
		recent_vas = frappe.get_all(
			"ICICI Virtual Account",
			fields=["name", "virtual_account_number", "party", "party_type", "status", "creation"],
			order_by="creation desc",
			limit=10
		)
		
		# Get payment activity
		recent_payments = frappe.db.sql("""
			SELECT 
				COUNT(*) as count,
				SUM(transaction_amount) as total_amount,
				DATE(transaction_date) as date
			FROM `tabICICI Payment Intimation`
			WHERE transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
			GROUP BY DATE(transaction_date)
			ORDER BY date DESC
			LIMIT 30
		""", as_dict=True)
		
		return {
			"success": True,
			"summary": summary,
			"recent_virtual_accounts": recent_vas,
			"payment_activity": recent_payments
		}
		
	except Exception as e:
		frappe.log_error(f"Virtual Account Dashboard Error: {str(e)}")
		return {"success": False, "message": str(e)}
