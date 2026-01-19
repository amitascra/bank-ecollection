# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return {
		"heatmap": True,
		"heatmap_message": _("This is based on transactions against this ICICI Integration"),
		"fieldname": "company",
		"transactions": [
			{
				"label": _("Virtual Accounts"),
				"items": ["ICICI Virtual Account"]
			},
			{
				"label": _("Payment Processing"),
				"items": ["ICICI Payment Intimation"]
			},
			{
				"label": _("Configuration"),
				"items": ["ICICI Settings"]
			}
		]
	}
