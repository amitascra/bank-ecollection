# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return [
		{
			"module_name": "Bank E-Collection",
			"category": "Modules",
			"label": _("Bank E-Collection"),
			"color": "#3498db",
			"icon": "fa fa-university",
			"type": "module",
			"description": "ICICI Bank e-Collection Integration for ERPNext"
		}
	]
