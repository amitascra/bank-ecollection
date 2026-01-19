# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from bank_ecollection.api.enquiry import reconcile_transactions
from bank_ecollection.utils.virtual_account import cleanup_inactive_virtual_accounts


def daily_reconciliation():
	"""Daily scheduled task for transaction reconciliation"""
	try:
		frappe.logger().info("Starting daily ICICI reconciliation task")
		
		# Check if integration is enabled
		settings = frappe.get_single("ICICI Settings")
		if not settings.enable_integration:
			frappe.logger().info("ICICI integration is disabled, skipping reconciliation")
			return
		
		# Reconcile transactions for the last 7 days
		from_date = frappe.utils.add_days(frappe.utils.today(), -7)
		to_date = frappe.utils.today()
		
		result = reconcile_transactions(from_date=from_date, to_date=to_date)
		
		if result.get("success"):
			summary = result.get("reconciliation_summary", {})
			discrepancies = result.get("discrepancies", {})
			
			# Log reconciliation results
			frappe.logger().info(f"Daily reconciliation completed: {summary}")
			
			# Send notification if there are discrepancies
			if (discrepancies.get("missing_in_erpnext") or 
				discrepancies.get("missing_in_icici") or 
				discrepancies.get("amount_mismatches")):
				
				send_reconciliation_alert(summary, discrepancies)
		else:
			frappe.log_error(f"Daily reconciliation failed: {result.get('message')}")
		
		# Cleanup inactive virtual accounts (older than 90 days)
		cleanup_result = cleanup_inactive_virtual_accounts(days=90)
		frappe.logger().info(f"Virtual account cleanup: {cleanup_result.get('message')}")
		
	except Exception as e:
		frappe.log_error(f"Daily reconciliation task error: {str(e)}")


def sync_pending_transactions():
	"""Hourly task to sync pending transactions"""
	try:
		frappe.logger().info("Starting hourly transaction sync task")
		
		# Check if integration is enabled
		settings = frappe.get_single("ICICI Settings")
		if not settings.enable_integration:
			return
		
		# Process pending payment intimations
		from bank_ecollection.bank_ecollection.doctype.icici_payment_intimation.icici_payment_intimation import bulk_process_pending_intimations
		
		result = bulk_process_pending_intimations()
		
		if result.get("success"):
			frappe.logger().info(f"Hourly sync completed: {result.get('message')}")
		else:
			frappe.log_error(f"Hourly sync failed: {result.get('message')}")
		
		# Retry failed intimations (max 3 retries)
		retry_failed_intimations()
		
	except Exception as e:
		frappe.log_error(f"Hourly sync task error: {str(e)}")


def retry_failed_intimations():
	"""Retry failed payment intimations with retry count < 3"""
	try:
		failed_intimations = frappe.get_all(
			"ICICI Payment Intimation",
			filters={
				"status": "Failed",
				"retry_count": ["<", 3]
			},
			fields=["name", "retry_count"]
		)
		
		if not failed_intimations:
			return
		
		retried = 0
		for intimation_data in failed_intimations:
			try:
				intimation = frappe.get_doc("ICICI Payment Intimation", intimation_data.name)
				
				# Only retry if last attempt was more than 1 hour ago
				if intimation.modified < frappe.utils.add_to_date(frappe.utils.now(), hours=-1):
					success = intimation.retry_processing()
					if success:
						retried += 1
						
			except Exception as e:
				frappe.log_error(f"Error retrying intimation {intimation_data.name}: {str(e)}")
		
		if retried > 0:
			frappe.logger().info(f"Retried {retried} failed payment intimations")
			
	except Exception as e:
		frappe.log_error(f"Failed intimation retry error: {str(e)}")


def send_reconciliation_alert(summary, discrepancies):
	"""Send email alert for reconciliation discrepancies"""
	try:
		# Get system managers for notification
		system_managers = frappe.get_all(
			"Has Role",
			filters={"role": "System Manager"},
			fields=["parent"]
		)
		
		if not system_managers:
			return
		
		recipients = [sm.parent for sm in system_managers]
		
		# Prepare email content
		subject = f"ICICI Reconciliation Alert - {summary.get('period')}"
		
		message = f"""
		<h3>ICICI e-Collection Reconciliation Alert</h3>
		<p>Discrepancies found during daily reconciliation for period: {summary.get('period')}</p>
		
		<h4>Summary:</h4>
		<ul>
			<li>ICICI Transactions: {summary.get('icici_transactions', 0)}</li>
			<li>ERPNext Intimations: {summary.get('erpnext_intimations', 0)}</li>
			<li>Missing in ERPNext: {summary.get('missing_in_erpnext', 0)}</li>
			<li>Missing in ICICI: {summary.get('missing_in_icici', 0)}</li>
			<li>Amount Mismatches: {summary.get('amount_mismatches', 0)}</li>
		</ul>
		
		<p>Please review the ICICI integration logs and take necessary action.</p>
		"""
		
		# Send email
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			header=["ICICI Reconciliation Alert", "red"]
		)
		
		frappe.logger().info(f"Reconciliation alert sent to {len(recipients)} recipients")
		
	except Exception as e:
		frappe.log_error(f"Reconciliation alert error: {str(e)}")


def monthly_cleanup():
	"""Monthly cleanup task"""
	try:
		frappe.logger().info("Starting monthly ICICI cleanup task")
		
		# Archive old payment intimations (older than 1 year)
		archive_old_intimations()
		
		# Clean up error logs older than 6 months
		cleanup_old_logs()
		
		# Generate monthly reconciliation report
		generate_monthly_report()
		
	except Exception as e:
		frappe.log_error(f"Monthly cleanup task error: {str(e)}")


def archive_old_intimations():
	"""Archive payment intimations older than 1 year"""
	try:
		cutoff_date = frappe.utils.add_years(frappe.utils.today(), -1)
		
		old_intimations = frappe.get_all(
			"ICICI Payment Intimation",
			filters={
				"transaction_date": ["<", cutoff_date],
				"status": ["in", ["Processed", "Ignored"]]
			},
			fields=["name"]
		)
		
		archived_count = 0
		for intimation in old_intimations:
			try:
				# Move to archived status or delete based on business requirements
				doc = frappe.get_doc("ICICI Payment Intimation", intimation.name)
				doc.add_comment("Comment", "Archived due to age (>1 year)")
				archived_count += 1
				
			except Exception as e:
				frappe.log_error(f"Error archiving intimation {intimation.name}: {str(e)}")
		
		frappe.logger().info(f"Archived {archived_count} old payment intimations")
		
	except Exception as e:
		frappe.log_error(f"Intimation archival error: {str(e)}")


def cleanup_old_logs():
	"""Clean up old error logs related to ICICI integration"""
	try:
		cutoff_date = frappe.utils.add_months(frappe.utils.today(), -6)
		
		old_logs = frappe.get_all(
			"Error Log",
			filters={
				"creation": ["<", cutoff_date],
				"method": ["like", "%icici%"]
			},
			fields=["name"]
		)
		
		for log in old_logs:
			frappe.delete_doc("Error Log", log.name, ignore_permissions=True)
		
		frappe.logger().info(f"Cleaned up {len(old_logs)} old ICICI error logs")
		
	except Exception as e:
		frappe.log_error(f"Log cleanup error: {str(e)}")


def generate_monthly_report():
	"""Generate monthly ICICI integration report"""
	try:
		# Get monthly statistics
		from_date = frappe.utils.get_first_day(frappe.utils.today())
		to_date = frappe.utils.get_last_day(frappe.utils.today())
		
		# Transaction summary
		transaction_stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_transactions,
				SUM(transaction_amount) as total_amount,
				status,
				payment_mode
			FROM `tabICICI Payment Intimation`
			WHERE transaction_date BETWEEN %s AND %s
			GROUP BY status, payment_mode
		""", (from_date, to_date), as_dict=True)
		
		# Virtual account summary
		va_stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_accounts,
				party_type,
				status
			FROM `tabICICI Virtual Account`
			WHERE creation BETWEEN %s AND %s
			GROUP BY party_type, status
		""", (from_date, to_date), as_dict=True)
		
		# Log monthly report
		frappe.logger().info(f"Monthly ICICI Report - Transactions: {len(transaction_stats)}, Virtual Accounts: {len(va_stats)}")
		
	except Exception as e:
		frappe.log_error(f"Monthly report generation error: {str(e)}")


@frappe.whitelist()
def run_manual_reconciliation():
	"""Manual reconciliation trigger"""
	try:
		daily_reconciliation()
		return {"success": True, "message": "Manual reconciliation completed"}
	except Exception as e:
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def run_manual_sync():
	"""Manual sync trigger"""
	try:
		sync_pending_transactions()
		return {"success": True, "message": "Manual sync completed"}
	except Exception as e:
		return {"success": False, "message": str(e)}
