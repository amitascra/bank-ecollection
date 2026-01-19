// Copyright (c) 2026, Amit Kumar and contributors
// For license information, please see license.txt

frappe.ui.form.on('ICICI Virtual Account', {
	refresh: function(frm) {
		// Add custom buttons
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__('Sync with Bank'), function() {
				sync_virtual_account(frm);
			});

			frm.add_custom_button(__('View Payment Intimations'), function() {
				view_payment_intimations(frm);
			});

			// Add status indicator
			if (frm.doc.status === 'Active') {
				frm.dashboard.set_headline_alert(__('Virtual Account is Active'), 'green');
			} else if (frm.doc.status === 'Error') {
				frm.dashboard.set_headline_alert(__('Virtual Account has Error'), 'red');
			}
		}

		// Set field properties
		frm.set_df_property('bank_response', 'read_only', 1);
		frm.set_df_property('last_sync_date', 'read_only', 1);
		frm.set_df_property('retry_count', 'read_only', 1);
	},

	party_type: function(frm) {
		// Clear party when party type changes
		frm.set_value('party', '');
	},

	company: function(frm) {
		// Filter party based on company if applicable
		if (frm.doc.company && frm.doc.party_type) {
			set_party_filter(frm);
		}
	}
});

function set_party_filter(frm) {
	if (frm.doc.party_type === 'Customer') {
		frm.set_query('party', function() {
			return {
				filters: {
					'disabled': 0
				}
			};
		});
	} else if (frm.doc.party_type === 'Supplier') {
		frm.set_query('party', function() {
			return {
				filters: {
					'disabled': 0
				}
			};
		});
	}
}

function sync_virtual_account(frm) {
	frappe.call({
		method: 'bank_ecollection.bank_e_collection.doctype.icici_virtual_account.icici_virtual_account.sync_virtual_account',
		args: {
			virtual_account_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message) {
				if (r.message.success) {
					frappe.msgprint({
						title: __('Sync Successful'),
						message: r.message.message,
						indicator: 'green'
					});
					frm.reload_doc();
				} else {
					frappe.msgprint({
						title: __('Sync Failed'),
						message: r.message.message,
						indicator: 'red'
					});
				}
			}
		}
	});
}

function view_payment_intimations(frm) {
	frappe.route_options = {
		'virtual_account_number': frm.doc.virtual_account_number
	};
	frappe.set_route('List', 'ICICI Payment Intimation');
}
