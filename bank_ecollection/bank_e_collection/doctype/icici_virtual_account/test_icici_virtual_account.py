# Copyright (c) 2026, Amit Kumar and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestICICIVirtualAccount(FrappeTestCase):
	def setUp(self):
		# Create test customer
		if not frappe.db.exists("Customer", "Test Customer ICICI"):
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": "Test Customer ICICI",
				"customer_type": "Individual"
			})
			customer.insert()

	def test_virtual_account_creation(self):
		"""Test virtual account creation"""
		va = frappe.get_doc({
			"doctype": "ICICI Virtual Account",
			"virtual_account_number": "TEST123456789",
			"party_type": "Customer",
			"party": "Test Customer ICICI",
			"company": frappe.defaults.get_global_default("company"),
			"status": "Active"
		})
		va.insert()
		
		self.assertEqual(va.virtual_account_number, "TEST123456789")
		self.assertEqual(va.party_type, "Customer")
		self.assertEqual(va.status, "Active")

	def test_unique_party_validation(self):
		"""Test that duplicate virtual accounts for same party are not allowed"""
		# Create first virtual account
		va1 = frappe.get_doc({
			"doctype": "ICICI Virtual Account",
			"virtual_account_number": "TEST123456790",
			"party_type": "Customer",
			"party": "Test Customer ICICI",
			"company": frappe.defaults.get_global_default("company")
		})
		va1.insert()
		
		# Try to create duplicate
		va2 = frappe.get_doc({
			"doctype": "ICICI Virtual Account",
			"virtual_account_number": "TEST123456791",
			"party_type": "Customer",
			"party": "Test Customer ICICI",
			"company": frappe.defaults.get_global_default("company")
		})
		
		with self.assertRaises(frappe.ValidationError):
			va2.insert()

	def test_status_update(self):
		"""Test status update functionality"""
		va = frappe.get_doc({
			"doctype": "ICICI Virtual Account",
			"virtual_account_number": "TEST123456792",
			"party_type": "Customer",
			"party": "Test Customer ICICI",
			"company": frappe.defaults.get_global_default("company")
		})
		va.insert()
		
		va.update_status("Error", "Test error message")
		
		self.assertEqual(va.status, "Error")
		self.assertEqual(va.error_message, "Test error message")
		self.assertEqual(va.retry_count, 1)
