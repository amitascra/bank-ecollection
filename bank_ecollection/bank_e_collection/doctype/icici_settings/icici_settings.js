// Copyright (c) 2026, Amit Kumar and contributors
// For license information, please see license.txt

frappe.ui.form.on('ICICI Settings', {
	refresh: function(frm) {
		// Add custom buttons
		frm.add_custom_button(__('Test API Connection'), function() {
			test_api_connection(frm);
		});

		frm.add_custom_button(__('Generate Keys'), function() {
			generate_encryption_keys(frm);
		});

		// Set field dependencies
		frm.toggle_display('auto_submit_payment_entry', frm.doc.auto_create_payment_entry);
	},

	environment: function(frm) {
		// Clear URLs when environment changes to set defaults
		if (frm.doc.environment) {
			frm.set_value('bene_upload_url', '');
			frm.set_value('enquiry_url', '');
		}
	},

	auto_create_payment_entry: function(frm) {
		frm.toggle_display('auto_submit_payment_entry', frm.doc.auto_create_payment_entry);
		if (!frm.doc.auto_create_payment_entry) {
			frm.set_value('auto_submit_payment_entry', 0);
		}
	},

	default_company: function(frm) {
		// Filter bank accounts by company
		if (frm.doc.default_company) {
			frm.set_query('default_bank_account', function() {
				return {
					filters: {
						'company': frm.doc.default_company,
						'is_company_account': 1
					}
				};
			});

			frm.set_query('default_cash_account', function() {
				return {
					filters: {
						'company': frm.doc.default_company,
						'account_type': 'Cash'
					}
				};
			});
		}
	}
});

function test_api_connection(frm) {
	frappe.call({
		method: 'bank_ecollection.bank_ecollection.doctype.icici_settings.icici_settings.test_api_connection',
		callback: function(r) {
			if (r.message) {
				if (r.message.success) {
					frappe.msgprint({
						title: __('Connection Test'),
						message: r.message.message,
						indicator: 'green'
					});
				} else {
					frappe.msgprint({
						title: __('Connection Test Failed'),
						message: r.message.message,
						indicator: 'red'
					});
				}
			}
		}
	});
}

function generate_encryption_keys(frm) {
	frappe.confirm(
		__('This will generate new RSA key pair for ICICI encryption. Continue?'),
		function() {
			frappe.call({
				method: 'bank_ecollection.api.encryption.generate_key_pair',
				callback: function(r) {
					if (r.message) {
						frm.set_value('public_key_path', r.message.public_key_path);
						frm.set_value('private_key_path', r.message.private_key_path);
						frappe.msgprint({
							title: __('Keys Generated'),
							message: __('RSA key pair generated successfully'),
							indicator: 'green'
						});
					}
				}
			});
		}
	);
}
