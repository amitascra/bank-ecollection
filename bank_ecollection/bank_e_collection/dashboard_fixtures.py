# Copyright (c) 2026, Amit Kumar and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import add_months, nowdate


def get_data():
	return frappe._dict(
		{
			"dashboards": get_dashboards(),
			"charts": get_charts(),
			"number_cards": get_number_cards(),
		}
	)


def get_dashboards():
	return [
		{
			"name": "ICICI Integration",
			"dashboard_name": "ICICI Integration",
			"charts": [
				{"chart": "ICICI Transaction Summary", "width": "Full"},
				{"chart": "Virtual Account Status", "width": "Half"},
				{"chart": "Payment Processing Status", "width": "Half"},
			],
			"cards": [
				{"card": "Total Virtual Accounts"},
				{"card": "Active Virtual Accounts"},
				{"card": "Payment Intimations"},
				{"card": "Processed Payments"},
			],
		}
	]


def get_charts():
	return [
		{
			"doctype": "Dashboard Chart",
			"based_on": "creation",
			"chart_type": "Count",
			"chart_name": _("ICICI Transaction Summary"),
			"name": "ICICI Transaction Summary",
			"document_type": "ICICI Payment Intimation",
			"filters_json": json.dumps([["ICICI Payment Intimation", "docstatus", "!=", 2]]),
			"group_by_type": "Count",
			"time_interval": "Monthly",
			"timespan": "Last Year",
			"owner": "Administrator",
			"type": "Line",
			"is_public": 1,
			"timeseries": 1,
		},
		{
			"doctype": "Dashboard Chart",
			"chart_type": "Group By",
			"chart_name": _("Virtual Account Status"),
			"name": "Virtual Account Status",
			"document_type": "ICICI Virtual Account",
			"filters_json": json.dumps([]),
			"group_by_based_on": "status",
			"owner": "Administrator",
			"type": "Donut",
			"is_public": 1,
			"custom_options": json.dumps({"height": 300}),
		},
		{
			"doctype": "Dashboard Chart",
			"chart_type": "Group By",
			"chart_name": _("Payment Processing Status"),
			"name": "Payment Processing Status",
			"document_type": "ICICI Payment Intimation",
			"filters_json": json.dumps([]),
			"group_by_based_on": "status",
			"owner": "Administrator",
			"type": "Donut",
			"is_public": 1,
			"custom_options": json.dumps({"height": 300}),
		},
	]


def get_number_cards():
	start_date = add_months(nowdate(), -1)
	end_date = nowdate()

	return [
		{
			"doctype": "Number Card",
			"document_type": "ICICI Virtual Account",
			"name": "Total Virtual Accounts",
			"filters_json": json.dumps([]),
			"function": "Count",
			"is_public": 1,
			"label": _("Total Virtual Accounts"),
			"show_percentage_stats": 1,
			"stats_time_interval": "Weekly",
		},
		{
			"doctype": "Number Card",
			"document_type": "ICICI Virtual Account",
			"name": "Active Virtual Accounts",
			"filters_json": json.dumps([["ICICI Virtual Account", "status", "=", "Active"]]),
			"function": "Count",
			"is_public": 1,
			"label": _("Active Virtual Accounts"),
			"show_percentage_stats": 1,
			"stats_time_interval": "Weekly",
		},
		{
			"doctype": "Number Card",
			"document_type": "ICICI Payment Intimation",
			"name": "Payment Intimations",
			"filters_json": json.dumps([
				["ICICI Payment Intimation", "creation", "between", [start_date, end_date]]
			]),
			"function": "Count",
			"is_public": 1,
			"label": _("Monthly Payment Intimations"),
			"show_percentage_stats": 1,
			"stats_time_interval": "Weekly",
		},
		{
			"doctype": "Number Card",
			"document_type": "ICICI Payment Intimation",
			"name": "Processed Payments",
			"filters_json": json.dumps([
				["ICICI Payment Intimation", "status", "=", "Processed"],
				["ICICI Payment Intimation", "creation", "between", [start_date, end_date]]
			]),
			"function": "Count",
			"is_public": 1,
			"label": _("Monthly Processed Payments"),
			"show_percentage_stats": 1,
			"stats_time_interval": "Weekly",
		},
	]


def install_fixtures():
	"""Install dashboard fixtures after app installation"""
	try:
		data = get_data()
		
		# Create Dashboard Charts
		for chart in data.charts:
			if not frappe.db.exists("Dashboard Chart", chart["name"]):
				chart_doc = frappe.get_doc(chart)
				chart_doc.insert(ignore_permissions=True)
				frappe.logger().info(f"Created Dashboard Chart: {chart['name']}")
		
		# Create Number Cards
		for card in data.number_cards:
			if not frappe.db.exists("Number Card", card["name"]):
				card_doc = frappe.get_doc(card)
				card_doc.insert(ignore_permissions=True)
				frappe.logger().info(f"Created Number Card: {card['name']}")
		
		frappe.db.commit()
		frappe.logger().info("ICICI dashboard fixtures installed successfully")
		
	except Exception as e:
		frappe.log_error(f"Error installing ICICI dashboard fixtures: {str(e)}")
		frappe.logger().error(f"Failed to install ICICI dashboard fixtures: {str(e)}")
