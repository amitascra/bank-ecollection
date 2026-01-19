# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ICICIVirtualAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bank_response: DF.JSON | None
		company: DF.Link
		creation_date: DF.Date | None
		error_message: DF.Text | None
		last_sync_date: DF.Datetime | None
		party: DF.DynamicLink
		party_type: DF.Literal["Customer", "Supplier"]
		retry_count: DF.Int
		status: DF.Literal["Active", "Inactive", "Suspended", "Error"]
		virtual_account_number: DF.Data
	# end: auto-generated types

	def validate(self):
		"""Validate virtual account data"""
		self.validate_party_exists()
		self.validate_unique_party_account()

	def validate_party_exists(self):
		"""Validate that the party exists"""
		if not frappe.db.exists(self.party_type, self.party):
			frappe.throw(f"{self.party_type} {self.party} does not exist")

	def validate_unique_party_account(self):
		"""Ensure one virtual account per party per company"""
		existing = frappe.db.get_value(
			"ICICI Virtual Account",
			{
				"party_type": self.party_type,
				"party": self.party,
				"company": self.company,
				"name": ("!=", self.name)
			},
			"name"
		)
		
		if existing:
			frappe.throw(f"Virtual Account already exists for {self.party_type} {self.party} in company {self.company}")

	def before_save(self):
		"""Update last sync date"""
		if self.has_value_changed("bank_response"):
			self.last_sync_date = frappe.utils.now()

	def get_party_details(self):
		"""Get party document details"""
		return frappe.get_doc(self.party_type, self.party)

	def update_status(self, status, error_message=None):
		"""Update virtual account status"""
		self.status = status
		if error_message:
			self.error_message = error_message
			self.retry_count = (self.retry_count or 0) + 1
		else:
			self.error_message = None
			self.retry_count = 0
		
		self.save(ignore_permissions=True)

	def sync_with_bank(self):
		"""Sync virtual account status with ICICI Bank"""
		try:
			from bank_ecollection.api.enquiry import query_virtual_account_status
			
			response = query_virtual_account_status(self.virtual_account_number)
			
			if response.get("successFlag") == "1":
				self.bank_response = response
				self.update_status("Active")
				return True
			else:
				self.update_status("Error", response.get("errMsg", "Unknown error"))
				return False
				
		except Exception as e:
			frappe.log_error(f"Virtual Account Sync Error: {str(e)}")
			self.update_status("Error", str(e))
			return False

	def get_payment_intimations(self):
		"""Get all payment intimations for this virtual account"""
		return frappe.get_all(
			"ICICI Payment Intimation",
			filters={"virtual_account_number": self.virtual_account_number},
			fields=["name", "utr_number", "transaction_amount", "transaction_date", "status"],
			order_by="transaction_date desc"
		)


@frappe.whitelist()
def create_virtual_account_for_party(party_type, party, company=None):
	"""Create virtual account for a party"""
	try:
		from bank_ecollection.api.bene_upload import create_virtual_account_api
		
		# Check if virtual account already exists
		existing = frappe.db.get_value(
			"ICICI Virtual Account",
			{"party_type": party_type, "party": party, "company": company},
			"name"
		)
		
		if existing:
			return {"success": False, "message": f"Virtual Account already exists: {existing}"}
		
		# Create virtual account via API
		result = create_virtual_account_api(party_type, party, company)
		
		if result.get("success"):
			return {"success": True, "virtual_account": result.get("virtual_account_number")}
		else:
			return {"success": False, "message": result.get("message")}
			
	except Exception as e:
		frappe.log_error(f"Virtual Account Creation Error: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def sync_virtual_account(virtual_account_name):
	"""Sync virtual account with bank"""
	try:
		va = frappe.get_doc("ICICI Virtual Account", virtual_account_name)
		success = va.sync_with_bank()
		
		if success:
			return {"success": True, "message": "Sync completed successfully"}
		else:
			return {"success": False, "message": va.error_message}
			
	except Exception as e:
		frappe.log_error(f"Virtual Account Sync Error: {str(e)}")
		return {"success": False, "message": str(e)}
