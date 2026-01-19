# Copyright (c) 2026, Amit Kumar and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestICICISettings(FrappeTestCase):
	def test_default_urls_uat(self):
		"""Test that UAT URLs are set correctly"""
		settings = frappe.get_single("ICICI Settings")
		settings.environment = "UAT"
		settings.set_default_urls()
		
		self.assertIn("apigwuat.icicibank.com", settings.bene_upload_url)
		self.assertIn("apigwuat.icicibank.com", settings.enquiry_url)

	def test_default_urls_production(self):
		"""Test that Production URLs are set correctly"""
		settings = frappe.get_single("ICICI Settings")
		settings.environment = "Production"
		settings.set_default_urls()
		
		self.assertIn("apigw.icicibank.com", settings.bene_upload_url)
		self.assertIn("apigw.icicibank.com", settings.enquiry_url)

	def test_callback_url_generation(self):
		"""Test callback URL generation"""
		settings = frappe.get_single("ICICI Settings")
		settings.set_callback_url()
		
		self.assertIn("/api/icici/intimation", settings.intimation_callback_url)

	def test_integration_enabled_check(self):
		"""Test integration enabled checks"""
		settings = frappe.get_single("ICICI Settings")
		settings.enable_integration = 1
		settings.enable_customer_integration = 1
		settings.enable_supplier_integration = 0
		
		self.assertTrue(settings.is_integration_enabled("Customer"))
		self.assertFalse(settings.is_integration_enabled("Supplier"))
		
		settings.enable_integration = 0
		self.assertFalse(settings.is_integration_enabled("Customer"))
