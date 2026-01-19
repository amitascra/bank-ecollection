app_name = "bank_ecollection"
app_title = "Bank E-Collection"
app_publisher = "Amit Kumar"
app_description = "ICICI Bank e-Collection Integration for ERPNext"
app_email = "amit@ascratech.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "bank_ecollection",
# 		"logo": "/assets/bank_ecollection/logo.png",
# 		"title": "Bank E-Collection-ERPnext",
# 		"route": "/bank_ecollection",
# 		"has_permission": "bank_ecollection.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/bank_ecollection/css/bank_ecollection.css"
# app_include_js = "/assets/bank_ecollection/js/bank_ecollection.js"

# include js, css files in header of web template
# web_include_css = "/assets/bank_ecollection/css/bank_ecollection.css"
# web_include_js = "/assets/bank_ecollection/js/bank_ecollection.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "bank_ecollection/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "bank_ecollection/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Fixtures
# ----------

fixtures = [
	{
		"dt": "Dashboard Chart",
		"filters": [
			["name", "in", ["ICICI Transaction Summary", "Virtual Account Status", "Payment Processing Status"]]
		]
	},
	{
		"dt": "Number Card", 
		"filters": [
			["name", "in", ["Total Virtual Accounts", "Active Virtual Accounts", "Payment Intimations", "Processed Payments"]]
		]
	}
]

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "bank_ecollection.utils.jinja_methods",
# 	"filters": "bank_ecollection.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "bank_ecollection.install.before_install"
after_install = "bank_ecollection.bank_e_collection.dashboard_fixtures.install_fixtures"

# Uninstallation
# ------------

# before_uninstall = "bank_ecollection.uninstall.before_uninstall"
# after_uninstall = "bank_ecollection.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "bank_ecollection.utils.before_app_install"
# after_app_install = "bank_ecollection.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "bank_ecollection.utils.before_app_uninstall"
# after_app_uninstall = "bank_ecollection.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "bank_ecollection.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Customer": {
		"after_insert": "bank_ecollection.api.bene_upload.create_virtual_account",
		"on_update": "bank_ecollection.api.bene_upload.update_virtual_account"
	},
	"Supplier": {
		"after_insert": "bank_ecollection.api.bene_upload.create_virtual_account",
		"on_update": "bank_ecollection.api.bene_upload.update_virtual_account"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"bank_ecollection.tasks.scheduled_tasks.daily_reconciliation"
	],
	"hourly": [
		"bank_ecollection.tasks.scheduled_tasks.sync_pending_transactions"
	]
}

# Testing
# -------

# before_tests = "bank_ecollection.install.before_tests"

# Overriding Methods
# ------------------------------
#
# Whitelisted Methods
# -------------------

whitelisted_methods = [
	"bank_ecollection.api.intimation_webhook.handle_payment_notification",
	"bank_ecollection.api.enquiry.query_transaction_status",
	"bank_ecollection.api.bene_upload.manual_upload_beneficiary",
	"bank_ecollection.utils.reconciliation.run_reconciliation"
]

# Website Routes for Webhooks
# ----------------------------

website_route_rules = [
	{
		"from_route": "/api/icici/intimation",
		"to_route": "bank_ecollection.api.intimation_webhook.handle_payment_notification"
	}
]

# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "bank_ecollection.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "bank_ecollection.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["bank_ecollection.utils.before_request"]
# after_request = ["bank_ecollection.utils.after_request"]

# Job Events
# ----------
# before_job = ["bank_ecollection.utils.before_job"]
# after_job = ["bank_ecollection.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"bank_ecollection.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

