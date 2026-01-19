# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from bank_ecollection.api.encryption import encrypt_request, decrypt_response


@frappe.whitelist()
def query_transaction_status(utr_number=None, virtual_account_number=None, from_date=None, to_date=None):
	"""Query transaction status from ICICI Bank"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		if not settings.enable_integration:
			return {"success": False, "message": "Integration is disabled"}
		
		# Prepare query payload
		payload = prepare_enquiry_payload(utr_number, virtual_account_number, from_date, to_date, settings)
		
		# Call ICICI Enquiry API
		response = call_enquiry_api(payload, settings)
		
		if response.get("successFlag") == "1":
			# Process and return transaction data
			transactions = process_enquiry_response(response)
			return {
				"success": True,
				"transactions": transactions,
				"raw_response": response
			}
		else:
			return {
				"success": False,
				"message": response.get("errMsg", "Unknown error"),
				"raw_response": response
			}
			
	except Exception as e:
		frappe.log_error(f"Transaction Status Query Error: {str(e)}")
		return {"success": False, "message": str(e)}


def prepare_enquiry_payload(utr_number, virtual_account_number, from_date, to_date, settings):
	"""Prepare payload for ICICI Enquiry API"""
	
	payload = {
		"clientCode": settings.client_code
	}
	
	# Add query parameters
	if utr_number:
		payload["utrNumber"] = utr_number
	
	if virtual_account_number:
		payload["virtualAccountNumber"] = virtual_account_number
	
	if from_date:
		payload["fromDate"] = frappe.utils.formatdate(from_date, "dd-MM-yyyy")
	
	if to_date:
		payload["toDate"] = frappe.utils.formatdate(to_date, "dd-MM-yyyy")
	
	# Default to last 7 days if no date range specified
	if not from_date and not to_date and not utr_number:
		to_date = frappe.utils.today()
		from_date = frappe.utils.add_days(to_date, -7)
		payload["fromDate"] = frappe.utils.formatdate(from_date, "dd-MM-yyyy")
		payload["toDate"] = frappe.utils.formatdate(to_date, "dd-MM-yyyy")
	
	return payload


def call_enquiry_api(payload, settings):
	"""Call ICICI Enquiry API"""
	try:
		# Encrypt payload
		encrypted_payload = encrypt_request(payload, settings)
		
		# Prepare headers
		headers = settings.get_api_headers()
		
		# Make API call
		response = requests.post(
			settings.enquiry_url,
			json=encrypted_payload,
			headers=headers,
			timeout=30
		)
		
		response.raise_for_status()
		
		# Decrypt and return response
		decrypted_response = decrypt_response(response.json(), settings)
		
		# Log API call
		frappe.logger().info(f"ICICI Enquiry API Response: {decrypted_response}")
		
		return decrypted_response
		
	except requests.exceptions.RequestException as e:
		frappe.log_error(f"ICICI Enquiry API Request Error: {str(e)}")
		return {"successFlag": "0", "errMsg": f"API Request Failed: {str(e)}"}
	except Exception as e:
		frappe.log_error(f"ICICI Enquiry API Error: {str(e)}")
		return {"successFlag": "0", "errMsg": f"API Error: {str(e)}"}


def process_enquiry_response(response):
	"""Process enquiry response and format transaction data"""
	try:
		transactions = []
		
		# ICICI typically returns transaction data in 'transactionDetails' array
		transaction_details = response.get("transactionDetails", [])
		
		if not isinstance(transaction_details, list):
			transaction_details = [transaction_details] if transaction_details else []
		
		for txn in transaction_details:
			processed_txn = {
				"virtual_account_number": txn.get("virtualAccountNumber", ""),
				"utr_number": txn.get("utrNumber", ""),
				"transaction_amount": float(txn.get("transactionAmount", 0)),
				"transaction_date": txn.get("transactionDate", ""),
				"payment_mode": txn.get("paymentMode", ""),
				"remitter_name": txn.get("remitterName", ""),
				"remitter_account": txn.get("remitterAccount", ""),
				"remitter_ifsc": txn.get("remitterIFSC", ""),
				"status": txn.get("status", ""),
				"remarks": txn.get("remarks", "")
			}
			transactions.append(processed_txn)
		
		return transactions
		
	except Exception as e:
		frappe.log_error(f"Enquiry Response Processing Error: {str(e)}")
		return []


@frappe.whitelist()
def query_virtual_account_status(virtual_account_number):
	"""Query specific virtual account status"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		payload = {
			"clientCode": settings.client_code,
			"virtualAccountNumber": virtual_account_number,
			"queryType": "STATUS"
		}
		
		response = call_enquiry_api(payload, settings)
		
		if response.get("successFlag") == "1":
			va_status = response.get("virtualAccountStatus", {})
			return {
				"success": True,
				"status": va_status.get("status", ""),
				"balance": float(va_status.get("balance", 0)),
				"last_transaction_date": va_status.get("lastTransactionDate", ""),
				"raw_response": response
			}
		else:
			return {
				"success": False,
				"message": response.get("errMsg", "Unknown error")
			}
			
	except Exception as e:
		frappe.log_error(f"Virtual Account Status Query Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def reconcile_transactions(from_date=None, to_date=None):
	"""Reconcile transactions between ICICI and ERPNext"""
	try:
		if not from_date:
			from_date = frappe.utils.add_days(frappe.utils.today(), -7)
		if not to_date:
			to_date = frappe.utils.today()
		
		# Query ICICI for transactions
		icici_result = query_transaction_status(from_date=from_date, to_date=to_date)
		
		if not icici_result.get("success"):
			return icici_result
		
		icici_transactions = icici_result.get("transactions", [])
		
		# Get ERPNext payment intimations for the same period
		erpnext_intimations = frappe.get_all(
			"ICICI Payment Intimation",
			filters={
				"transaction_date": ["between", [from_date, to_date]]
			},
			fields=["utr_number", "virtual_account_number", "transaction_amount", "status"]
		)
		
		# Create lookup dictionaries
		erpnext_utrs = {intimation.utr_number: intimation for intimation in erpnext_intimations}
		icici_utrs = {txn["utr_number"]: txn for txn in icici_transactions}
		
		# Find discrepancies
		missing_in_erpnext = []
		missing_in_icici = []
		amount_mismatches = []
		
		# Check for transactions in ICICI but not in ERPNext
		for utr, icici_txn in icici_utrs.items():
			if utr not in erpnext_utrs:
				missing_in_erpnext.append(icici_txn)
			else:
				erpnext_txn = erpnext_utrs[utr]
				if abs(float(icici_txn["transaction_amount"]) - float(erpnext_txn.transaction_amount)) > 0.01:
					amount_mismatches.append({
						"utr": utr,
						"icici_amount": icici_txn["transaction_amount"],
						"erpnext_amount": erpnext_txn.transaction_amount
					})
		
		# Check for transactions in ERPNext but not in ICICI
		for utr, erpnext_txn in erpnext_utrs.items():
			if utr not in icici_utrs:
				missing_in_icici.append(erpnext_txn)
		
		return {
			"success": True,
			"reconciliation_summary": {
				"period": f"{from_date} to {to_date}",
				"icici_transactions": len(icici_transactions),
				"erpnext_intimations": len(erpnext_intimations),
				"missing_in_erpnext": len(missing_in_erpnext),
				"missing_in_icici": len(missing_in_icici),
				"amount_mismatches": len(amount_mismatches)
			},
			"discrepancies": {
				"missing_in_erpnext": missing_in_erpnext,
				"missing_in_icici": missing_in_icici,
				"amount_mismatches": amount_mismatches
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Transaction Reconciliation Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def sync_missing_transactions(utr_list=None):
	"""Sync missing transactions from ICICI to ERPNext"""
	try:
		if not utr_list:
			return {"success": False, "message": "No UTR numbers provided"}
		
		if isinstance(utr_list, str):
			utr_list = json.loads(utr_list)
		
		synced_count = 0
		errors = []
		
		for utr in utr_list:
			try:
				# Query ICICI for specific transaction
				result = query_transaction_status(utr_number=utr)
				
				if result.get("success") and result.get("transactions"):
					txn = result["transactions"][0]
					
					# Create payment intimation if it doesn't exist
					existing = frappe.db.exists("ICICI Payment Intimation", {"utr_number": utr})
					
					if not existing:
						intimation = frappe.new_doc("ICICI Payment Intimation")
						intimation.virtual_account_number = txn["virtual_account_number"]
						intimation.utr_number = txn["utr_number"]
						intimation.transaction_amount = txn["transaction_amount"]
						intimation.payment_mode = txn["payment_mode"]
						intimation.transaction_date = txn["transaction_date"]
						intimation.remitter_name = txn["remitter_name"]
						intimation.remitter_account = txn["remitter_account"]
						intimation.remitter_ifsc = txn["remitter_ifsc"]
						intimation.status = "Received"
						intimation.insert(ignore_permissions=True)
						
						synced_count += 1
					else:
						errors.append(f"UTR {utr} already exists in ERPNext")
				else:
					errors.append(f"UTR {utr} not found in ICICI records")
					
			except Exception as e:
				errors.append(f"Error syncing UTR {utr}: {str(e)}")
		
		return {
			"success": True,
			"message": f"Synced {synced_count} transactions",
			"synced_count": synced_count,
			"errors": errors
		}
		
	except Exception as e:
		frappe.log_error(f"Missing Transaction Sync Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_transaction_summary(from_date=None, to_date=None):
	"""Get transaction summary from ICICI"""
	try:
		if not from_date:
			from_date = frappe.utils.add_days(frappe.utils.today(), -30)
		if not to_date:
			to_date = frappe.utils.today()
		
		# Query transactions
		result = query_transaction_status(from_date=from_date, to_date=to_date)
		
		if not result.get("success"):
			return result
		
		transactions = result.get("transactions", [])
		
		# Calculate summary
		total_amount = sum(float(txn["transaction_amount"]) for txn in transactions)
		total_count = len(transactions)
		
		# Group by payment mode
		by_payment_mode = {}
		for txn in transactions:
			mode = txn["payment_mode"] or "Unknown"
			if mode not in by_payment_mode:
				by_payment_mode[mode] = {"count": 0, "amount": 0}
			by_payment_mode[mode]["count"] += 1
			by_payment_mode[mode]["amount"] += float(txn["transaction_amount"])
		
		# Group by date
		by_date = {}
		for txn in transactions:
			date = txn["transaction_date"][:10] if txn["transaction_date"] else "Unknown"
			if date not in by_date:
				by_date[date] = {"count": 0, "amount": 0}
			by_date[date]["count"] += 1
			by_date[date]["amount"] += float(txn["transaction_amount"])
		
		return {
			"success": True,
			"summary": {
				"period": f"{from_date} to {to_date}",
				"total_transactions": total_count,
				"total_amount": total_amount,
				"by_payment_mode": by_payment_mode,
				"by_date": dict(sorted(by_date.items()))
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Transaction Summary Error: {str(e)}")
		return {"success": False, "message": str(e)}
