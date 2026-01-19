# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
	"""Get context for ICICI reconciliation page"""
	context.title = _("ICICI Transaction Reconciliation & Debug Tools")
	context.show_sidebar = True
	
	# Check if user has permission
	if not frappe.has_permission("ICICI Settings", "read"):
		frappe.throw(_("You don't have permission to access this page"))
	
	return context


@frappe.whitelist()
def run_reconciliation(from_date=None, to_date=None):
	"""Run transaction reconciliation"""
	try:
		from bank_ecollection.api.enquiry import reconcile_transactions
		result = reconcile_transactions(from_date=from_date, to_date=to_date)
		return result
	except Exception as e:
		frappe.log_error(f"ICICI Reconciliation Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_reconciliation_summary():
	"""Get reconciliation summary"""
	try:
		# Get counts from last 30 days
		from frappe.utils import add_days, today
		
		end_date = today()
		start_date = add_days(end_date, -30)
		
		# Virtual accounts summary
		va_summary = frappe.db.sql("""
			SELECT status, COUNT(*) as count
			FROM `tabICICI Virtual Account`
			GROUP BY status
		""", as_dict=True)
		
		# Payment intimations summary
		pi_summary = frappe.db.sql("""
			SELECT status, COUNT(*) as count
			FROM `tabICICI Payment Intimation`
			WHERE DATE(creation) BETWEEN %s AND %s
			GROUP BY status
		""", (start_date, end_date), as_dict=True)
		
		# Bank transactions related to ICICI
		bt_summary = frappe.db.sql("""
			SELECT status, COUNT(*) as count
			FROM `tabBank Transaction`
			WHERE description LIKE '%ICICI%'
			AND DATE(date) BETWEEN %s AND %s
			GROUP BY status
		""", (start_date, end_date), as_dict=True)
		
		# Recent activity
		recent_activity = frappe.get_all(
			"ICICI Payment Intimation",
			fields=["name", "utr_number", "transaction_amount", "status", "creation", "bank_transaction", "payment_entry"],
			filters={"creation": [">=", add_days(today(), -7)]},
			order_by="creation desc",
			limit=10
		)
		
		return {
			"success": True,
			"summary": {
				"virtual_accounts": va_summary,
				"payment_intimations": pi_summary,
				"bank_transactions": bt_summary,
				"recent_activity": recent_activity,
				"period": f"{start_date} to {end_date}"
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Reconciliation Summary Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def sync_missing_transactions(utr_list):
	"""Sync missing transactions"""
	try:
		from bank_ecollection.api.enquiry import sync_missing_transactions
		result = sync_missing_transactions(utr_list)
		return result
	except Exception as e:
		frappe.log_error(f"Sync Missing Transactions Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_bank_reconciliation_status():
	"""Get ERPNext bank reconciliation status for ICICI"""
	try:
		# Get ICICI bank accounts
		icici_bank_accounts = frappe.get_all("Bank Account", 
			filters={"bank": ["like", "%ICICI%"]},
			fields=["name", "account_name", "account", "company"])
		
		reconciliation_data = []
		
		for bank_account in icici_bank_accounts:
			# Get unreconciled transactions
			unreconciled = frappe.db.count("Bank Transaction", {
				"bank_account": bank_account.name,
				"status": ["in", ["Pending", "Unreconciled"]]
			})
			
			# Get reconciled transactions
			reconciled = frappe.db.count("Bank Transaction", {
				"bank_account": bank_account.name,
				"status": "Reconciled"
			})
			
			reconciliation_data.append({
				"bank_account": bank_account.name,
				"account_name": bank_account.account_name,
				"company": bank_account.company,
				"unreconciled": unreconciled,
				"reconciled": reconciled,
				"total": unreconciled + reconciled
			})
		
		return {
			"success": True,
			"bank_accounts": reconciliation_data
		}
		
	except Exception as e:
		frappe.log_error(f"Bank Reconciliation Status Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def create_test_bank_transaction():
	"""Create a test bank transaction for debugging"""
	try:
		settings = frappe.get_single("ICICI Settings")
		if not settings.default_bank_account:
			return {"success": False, "message": "Default bank account not configured"}
		
		# Create test bank transaction
		bt = frappe.new_doc("Bank Transaction")
		bt.date = frappe.utils.today()
		bt.bank_account = settings.default_bank_account
		bt.deposit = 1000.00
		bt.withdrawal = 0.0
		bt.currency = "INR"
		bt.reference_number = f"TEST-{frappe.utils.random_string(10)}"
		bt.description = "ICICI Test Transaction - Debug Mode"
		bt.status = "Pending"
		
		bt.insert(ignore_permissions=True)
		bt.submit()
		
		return {
			"success": True,
			"message": f"Test Bank Transaction created: {bt.name}",
			"bank_transaction": bt.name
		}
		
	except Exception as e:
		frappe.log_error(f"Test Bank Transaction Error: {str(e)}")
		return {"success": False, "message": str(e)}
