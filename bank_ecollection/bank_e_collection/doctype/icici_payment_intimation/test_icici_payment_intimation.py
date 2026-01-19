# Copyright (c) 2026, Amit Kumar and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestICICIPaymentIntimation(FrappeTestCase):
	def setUp(self):
		# Create test customer and virtual account
		if not frappe.db.exists("Customer", "Test Customer ICICI Payment"):
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": "Test Customer ICICI Payment",
				"customer_type": "Individual"
			})
			customer.insert()

		if not frappe.db.exists("ICICI Virtual Account", {"virtual_account_number": "TEST987654321"}):
			va = frappe.get_doc({
				"doctype": "ICICI Virtual Account",
				"virtual_account_number": "TEST987654321",
				"party_type": "Customer",
				"party": "Test Customer ICICI Payment",
				"company": frappe.defaults.get_global_default("company"),
				"status": "Active"
			})
			va.insert()

	def test_payment_intimation_creation(self):
		"""Test payment intimation creation"""
		intimation = frappe.get_doc({
			"doctype": "ICICI Payment Intimation",
			"virtual_account_number": "TEST987654321",
			"utr_number": "UTR123456789",
			"transaction_amount": 10000.00,
			"payment_mode": "NEFT",
			"transaction_date": frappe.utils.now(),
			"remitter_name": "Test Remitter"
		})
		intimation.insert()
		
		self.assertEqual(intimation.virtual_account_number, "TEST987654321")
		self.assertEqual(intimation.utr_number, "UTR123456789")
		self.assertEqual(intimation.status, "Received")

	def test_duplicate_utr_validation(self):
		"""Test that duplicate UTR numbers are not allowed"""
		# Create first intimation
		intimation1 = frappe.get_doc({
			"doctype": "ICICI Payment Intimation",
			"virtual_account_number": "TEST987654321",
			"utr_number": "UTR123456790",
			"transaction_amount": 5000.00,
			"payment_mode": "RTGS",
			"transaction_date": frappe.utils.now()
		})
		intimation1.insert()
		
		# Try to create duplicate
		intimation2 = frappe.get_doc({
			"doctype": "ICICI Payment Intimation",
			"virtual_account_number": "TEST987654321",
			"utr_number": "UTR123456790",
			"transaction_amount": 7000.00,
			"payment_mode": "IMPS",
			"transaction_date": frappe.utils.now()
		})
		
		with self.assertRaises(frappe.ValidationError):
			intimation2.insert()

	def test_status_update(self):
		"""Test status update functionality"""
		intimation = frappe.get_doc({
			"doctype": "ICICI Payment Intimation",
			"virtual_account_number": "TEST987654321",
			"utr_number": "UTR123456791",
			"transaction_amount": 15000.00,
			"payment_mode": "UPI",
			"transaction_date": frappe.utils.now()
		})
		intimation.insert()
		
		intimation.update_status("Failed", "Test error message")
		
		self.assertEqual(intimation.status, "Failed")
		self.assertEqual(intimation.error_message, "Test error message")
		self.assertEqual(intimation.retry_count, 1)

	def test_party_details_retrieval(self):
		"""Test getting party details from virtual account"""
		intimation = frappe.get_doc({
			"doctype": "ICICI Payment Intimation",
			"virtual_account_number": "TEST987654321",
			"utr_number": "UTR123456792",
			"transaction_amount": 20000.00,
			"payment_mode": "NEFT",
			"transaction_date": frappe.utils.now()
		})
		intimation.insert()
		
		party_details = intimation.get_party_details()
		
		self.assertEqual(party_details["party_type"], "Customer")
		self.assertEqual(party_details["party"], "Test Customer ICICI Payment")
