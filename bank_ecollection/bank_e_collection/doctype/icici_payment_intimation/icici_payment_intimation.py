# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ICICIPaymentIntimation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bank_response: DF.JSON | None
		error_message: DF.Text | None
		naming_series: DF.Literal["ICICI-INT-.YYYY.-"]
		payment_entry: DF.Link | None
		payment_mode: DF.Literal["NEFT", "RTGS", "IMPS", "UPI", "FT", "Cash", "Cheque"]
		processed_date: DF.Datetime | None
		remitter_account: DF.Data | None
		remitter_bank: DF.Data | None
		remitter_ifsc: DF.Data | None
		remitter_name: DF.Data | None
		retry_count: DF.Int
		status: DF.Literal["Received", "Processed", "Failed", "Ignored"]
		transaction_amount: DF.Currency
		transaction_date: DF.Datetime
		utr_number: DF.Data
		virtual_account_number: DF.Data
	# end: auto-generated types

	def validate(self):
		"""Validate payment intimation data"""
		self.validate_virtual_account_exists()
		self.validate_duplicate_utr()

	def validate_virtual_account_exists(self):
		"""Validate that virtual account exists"""
		if not frappe.db.exists("ICICI Virtual Account", {"virtual_account_number": self.virtual_account_number}):
			frappe.throw(f"Virtual Account {self.virtual_account_number} does not exist")

	def validate_duplicate_utr(self):
		"""Validate that UTR number is unique"""
		existing = frappe.db.get_value(
			"ICICI Payment Intimation",
			{
				"utr_number": self.utr_number,
				"name": ("!=", self.name)
			},
			"name"
		)
		
		if existing:
			frappe.throw(f"Payment intimation with UTR {self.utr_number} already exists: {existing}")

	def before_save(self):
		"""Update processed date when status changes"""
		if self.has_value_changed("status") and self.status == "Processed":
			self.processed_date = frappe.utils.now()

	def get_virtual_account(self):
		"""Get associated virtual account document"""
		return frappe.get_doc("ICICI Virtual Account", {"virtual_account_number": self.virtual_account_number})

	def get_party_details(self):
		"""Get party details from virtual account"""
		va = self.get_virtual_account()
		return {
			"party_type": va.party_type,
			"party": va.party,
			"company": va.company
		}

	def process_payment(self):
		"""Process payment intimation and create Payment Entry"""
		try:
			if self.status != "Received":
				frappe.throw(f"Cannot process payment with status: {self.status}")

			# Get ICICI settings
			settings = frappe.get_single("ICICI Settings")
			
			if not settings.auto_create_payment_entry:
				self.status = "Ignored"
				self.save()
				return False

			# Create Payment Entry
			from bank_ecollection.utils.payment_handler import create_payment_entry_from_intimation
			
			payment_entry = create_payment_entry_from_intimation(self)
			
			if payment_entry:
				self.payment_entry = payment_entry.name
				self.status = "Processed"
				self.processed_date = frappe.utils.now()
				self.error_message = None
				self.save()
				
				# Auto-submit if enabled
				if settings.auto_submit_payment_entry and payment_entry.docstatus == 0:
					payment_entry.submit()
				
				return True
			else:
				self.update_status("Failed", "Failed to create Payment Entry")
				return False
				
		except Exception as e:
			frappe.log_error(f"Payment Processing Error: {str(e)}")
			self.update_status("Failed", str(e))
			return False

	def update_status(self, status, error_message=None):
		"""Update intimation status"""
		self.status = status
		if error_message:
			self.error_message = error_message
			self.retry_count = (self.retry_count or 0) + 1
		else:
			self.error_message = None
		
		if status == "Processed":
			self.processed_date = frappe.utils.now()
		
		self.save(ignore_permissions=True)

	def retry_processing(self):
		"""Retry processing failed payment"""
		if self.status not in ["Failed", "Received"]:
			frappe.throw(f"Cannot retry processing for status: {self.status}")
		
		self.status = "Received"
		self.error_message = None
		return self.process_payment()


@frappe.whitelist()
def process_payment_intimation(intimation_name):
	"""Process a specific payment intimation"""
	try:
		intimation = frappe.get_doc("ICICI Payment Intimation", intimation_name)
		success = intimation.process_payment()
		
		if success:
			return {"success": True, "message": "Payment processed successfully"}
		else:
			return {"success": False, "message": intimation.error_message}
			
	except Exception as e:
		frappe.log_error(f"Payment Intimation Processing Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def retry_failed_intimation(intimation_name):
	"""Retry processing failed intimation"""
	try:
		intimation = frappe.get_doc("ICICI Payment Intimation", intimation_name)
		success = intimation.retry_processing()
		
		if success:
			return {"success": True, "message": "Payment processed successfully on retry"}
		else:
			return {"success": False, "message": intimation.error_message}
			
	except Exception as e:
		frappe.log_error(f"Payment Intimation Retry Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def bulk_process_pending_intimations():
	"""Process all pending payment intimations"""
	try:
		pending_intimations = frappe.get_all(
			"ICICI Payment Intimation",
			filters={"status": "Received"},
			fields=["name"]
		)
		
		processed = 0
		failed = 0
		
		for intimation_data in pending_intimations:
			intimation = frappe.get_doc("ICICI Payment Intimation", intimation_data.name)
			if intimation.process_payment():
				processed += 1
			else:
				failed += 1
		
		return {
			"success": True,
			"message": f"Processed: {processed}, Failed: {failed}",
			"processed": processed,
			"failed": failed
		}
		
	except Exception as e:
		frappe.log_error(f"Bulk Processing Error: {str(e)}")
		return {"success": False, "message": str(e)}
