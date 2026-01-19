# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.party import get_party_account


def create_payment_entry(intimation_doc):
	"""Create Payment Entry from ICICI Payment Intimation using ERPNext standard workflow"""
	try:
		# Get virtual account details
		va_doc = frappe.get_doc("ICICI Virtual Account", intimation_doc.virtual_account_number)
		
		# Get ICICI settings
		settings = frappe.get_single("ICICI Settings")
		
		# First create Bank Transaction (ERPNext standard approach)
		bank_transaction = create_bank_transaction_from_intimation(intimation_doc, va_doc, settings)
		
		# Then create Payment Entry using ERPNext's Bank Reconciliation Tool
		payment_entry = create_payment_entry_from_bank_transaction(bank_transaction, va_doc, settings)
		
		# Update intimation with references
		intimation_doc.bank_transaction = bank_transaction.name
		intimation_doc.payment_entry = payment_entry.name if payment_entry else None
		intimation_doc.status = "Processed"
		intimation_doc.save(ignore_permissions=True)
		
		frappe.logger().info(f"Created Bank Transaction {bank_transaction.name} and Payment Entry {payment_entry.name if payment_entry else 'None'} for ICICI intimation {intimation_doc.name}")
		
		return payment_entry
		
	except Exception as e:
		frappe.log_error(f"Payment Entry Creation Error: {str(e)}")
		intimation_doc.status = "Failed"
		intimation_doc.error_message = str(e)
		intimation_doc.save(ignore_permissions=True)
		raise


def create_bank_transaction_from_intimation(intimation_doc, va_doc, settings):
	"""Create Bank Transaction using ERPNext standard approach"""
	# Get the ERPNext Bank Account linked to virtual account
	bank_account_name = va_doc.bank_account
	if not bank_account_name:
		# Fallback to settings default
		bank_account_name = get_bank_account_from_settings(settings)
	
	# Create Bank Transaction
	bt = frappe.new_doc("Bank Transaction")
	bt.date = intimation_doc.transaction_date
	bt.bank_account = bank_account_name
	bt.deposit = intimation_doc.transaction_amount
	bt.withdrawal = 0.0
	bt.currency = "INR"  # ICICI is INR
	bt.reference_number = intimation_doc.utr_number
	bt.description = f"ICICI Virtual Account Payment - {intimation_doc.virtual_account_number}"
	bt.party_type = va_doc.party_type
	bt.party = va_doc.party
	bt.status = "Pending"
	
	bt.insert(ignore_permissions=True)
	bt.submit()
	
	return bt


def create_payment_entry_from_bank_transaction(bank_transaction, va_doc, settings):
	"""Create Payment Entry from Bank Transaction using ERPNext's standard method"""
	try:
		from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import create_payment_entry_bts
		
		# Use ERPNext's standard method to create Payment Entry from Bank Transaction
		payment_entry = create_payment_entry_bts(
			bank_transaction_name=bank_transaction.name,
			reference_number=bank_transaction.reference_number,
			reference_date=bank_transaction.date,
			party_type=va_doc.party_type,
			party=va_doc.party,
			posting_date=bank_transaction.date,
			mode_of_payment=map_icici_payment_mode("NEFT"),  # Default mode
			allow_edit=False  # Auto-submit
		)
		
		return payment_entry
		
	except Exception as e:
		frappe.log_error(f"Payment Entry from Bank Transaction Error: {str(e)}")
		# If auto-creation fails, leave Bank Transaction for manual reconciliation
		return None


def get_bank_account_from_settings(settings):
	"""Get bank account from ICICI settings"""
	if settings.default_bank_account:
		# Get the actual account linked to the bank account
		bank_account_doc = frappe.get_doc("Bank Account", settings.default_bank_account)
		return bank_account_doc.account
	else:
		# Fallback to cash account
		return settings.default_cash_account


def get_mode_of_payment(icici_payment_mode):
	"""Map ICICI payment mode to ERPNext Mode of Payment"""
	try:
		# Mapping dictionary
		mode_mapping = {
			"NEFT": "NEFT",
			"RTGS": "RTGS", 
			"IMPS": "IMPS",
			"UPI": "UPI",
			"FT": "Bank Transfer",
			"Cash": "Cash",
			"Cheque": "Cheque"
		}
		
		mapped_mode = mode_mapping.get(icici_payment_mode, "Bank Transfer")
		
		# Check if mode of payment exists in ERPNext
		if frappe.db.exists("Mode of Payment", mapped_mode):
			return mapped_mode
		else:
			# Create mode of payment if it doesn't exist
			return create_mode_of_payment(mapped_mode)
			
	except Exception as e:
		frappe.log_error(f"Mode of Payment Mapping Error: {str(e)}")
		return "Bank Transfer"  # Default fallback


def create_mode_of_payment(mode_name):
	"""Create Mode of Payment if it doesn't exist"""
	try:
		if frappe.db.exists("Mode of Payment", mode_name):
			return mode_name
		
		mode_doc = frappe.new_doc("Mode of Payment")
		mode_doc.mode_of_payment = mode_name
		mode_doc.type = "Bank"
		mode_doc.insert(ignore_permissions=True)
		
		frappe.logger().info(f"Created Mode of Payment: {mode_name}")
		return mode_name
		
	except Exception as e:
		frappe.log_error(f"Mode of Payment Creation Error: {str(e)}")
		return "Bank Transfer"


def allocate_payment_to_invoices(payment_entry, party_type, party, company):
	"""Allocate payment entry to outstanding invoices"""
	try:
		# Get outstanding invoices for the party
		invoice_doctype = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"
		
		outstanding_invoices = frappe.get_all(
			invoice_doctype,
			filters={
				party_type.lower(): party,
				"company": company,
				"docstatus": 1,
				"outstanding_amount": [">", 0]
			},
			fields=["name", "outstanding_amount", "posting_date"],
			order_by="posting_date asc"
		)
		
		if not outstanding_invoices:
			return False
		
		# Allocate payment to invoices (FIFO basis)
		remaining_amount = payment_entry.paid_amount
		references = []
		
		for invoice in outstanding_invoices:
			if remaining_amount <= 0:
				break
			
			allocated_amount = min(remaining_amount, invoice.outstanding_amount)
			
			references.append({
				"reference_doctype": invoice_doctype,
				"reference_name": invoice.name,
				"allocated_amount": allocated_amount
			})
			
			remaining_amount -= allocated_amount
		
		# Update payment entry with references
		if references:
			payment_entry.references = []
			for ref in references:
				payment_entry.append("references", ref)
			
			payment_entry.save(ignore_permissions=True)
			frappe.logger().info(f"Allocated payment {payment_entry.name} to {len(references)} invoices")
			return True
		
		return False
		
	except Exception as e:
		frappe.log_error(f"Payment Allocation Error: {str(e)}")
		return False


def create_bank_transaction_entry(intimation):
	"""Create Bank Transaction entry for reconciliation"""
	try:
		settings = frappe.get_single("ICICI Settings")
		
		# Check if bank transaction already exists
		existing = frappe.db.exists("Bank Transaction", {"reference_number": intimation.utr_number})
		if existing:
			return frappe.get_doc("Bank Transaction", existing)
		
		# Create new bank transaction
		bt = frappe.new_doc("Bank Transaction")
		bt.date = frappe.utils.getdate(intimation.transaction_date)
		bt.bank_account = settings.default_bank_account
		bt.deposit = intimation.transaction_amount if intimation.transaction_amount > 0 else 0
		bt.withdrawal = abs(intimation.transaction_amount) if intimation.transaction_amount < 0 else 0
		bt.currency = frappe.get_cached_value("Company", settings.default_company, "default_currency")
		bt.description = f"ICICI e-Collection payment from {intimation.remitter_name}"
		bt.reference_number = intimation.utr_number
		bt.unallocated_amount = intimation.transaction_amount
		
		# Set party details if available
		party_details = intimation.get_party_details()
		if party_details:
			bt.party_type = party_details["party_type"]
			bt.party = party_details["party"]
		
		bt.insert(ignore_permissions=True)
		bt.submit()
		
		frappe.logger().info(f"Bank Transaction {bt.name} created for UTR: {intimation.utr_number}")
		return bt
		
	except Exception as e:
		frappe.log_error(f"Bank Transaction Creation Error: {str(e)}")
		return None


def reconcile_payment_with_bank_transaction(payment_entry, intimation):
	"""Reconcile payment entry with bank transaction"""
	try:
		# Create or get bank transaction
		bank_transaction = create_bank_transaction_entry(intimation)
		
		if not bank_transaction:
			return False
		
		# Link payment entry to bank transaction
		from erpnext.accounts.doctype.bank_transaction.bank_transaction import reconcile_vouchers
		
		vouchers = [{
			"payment_doctype": "Payment Entry",
			"payment_name": payment_entry.name,
			"amount": payment_entry.paid_amount
		}]
		
		reconcile_vouchers(bank_transaction.name, frappe.as_json(vouchers))
		
		frappe.logger().info(f"Reconciled Payment Entry {payment_entry.name} with Bank Transaction {bank_transaction.name}")
		return True
		
	except Exception as e:
		frappe.log_error(f"Payment Reconciliation Error: {str(e)}")
		return False


@frappe.whitelist()
def process_bulk_payments(intimation_names):
	"""Process multiple payment intimations in bulk"""
	try:
		if isinstance(intimation_names, str):
			intimation_names = frappe.parse_json(intimation_names)
		
		processed = 0
		failed = 0
		errors = []
		
		for intimation_name in intimation_names:
			try:
				intimation = frappe.get_doc("ICICI Payment Intimation", intimation_name)
				
				if intimation.status == "Received":
					success = intimation.process_payment()
					if success:
						processed += 1
					else:
						failed += 1
						errors.append(f"{intimation_name}: {intimation.error_message}")
				else:
					errors.append(f"{intimation_name}: Invalid status - {intimation.status}")
					
			except Exception as e:
				failed += 1
				errors.append(f"{intimation_name}: {str(e)}")
		
		return {
			"success": True,
			"message": f"Processed: {processed}, Failed: {failed}",
			"processed": processed,
			"failed": failed,
			"errors": errors[:10]  # Limit error list
		}
		
	except Exception as e:
		frappe.log_error(f"Bulk Payment Processing Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_payment_processing_summary():
	"""Get summary of payment processing status"""
	try:
		# Get counts by status
		status_summary = frappe.db.sql("""
			SELECT status, COUNT(*) as count, SUM(transaction_amount) as total_amount
			FROM `tabICICI Payment Intimation`
			GROUP BY status
		""", as_dict=True)
		
		# Get recent processing activity
		recent_activity = frappe.get_all(
			"ICICI Payment Intimation",
			fields=["name", "utr_number", "transaction_amount", "status", "processed_date"],
			filters={"processed_date": [">=", frappe.utils.add_days(frappe.utils.today(), -7)]},
			order_by="processed_date desc",
			limit=20
		)
		
		# Get failed payments for retry
		failed_payments = frappe.get_all(
			"ICICI Payment Intimation",
			fields=["name", "utr_number", "transaction_amount", "error_message", "retry_count"],
			filters={"status": "Failed"},
			order_by="modified desc",
			limit=10
		)
		
		return {
			"success": True,
			"status_summary": status_summary,
			"recent_activity": recent_activity,
			"failed_payments": failed_payments
		}
		
	except Exception as e:
		frappe.log_error(f"Payment Processing Summary Error: {str(e)}")
		return {"success": False, "message": str(e)}
