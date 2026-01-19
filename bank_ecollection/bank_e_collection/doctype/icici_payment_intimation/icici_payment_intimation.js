// Copyright (c) 2026, Amit Kumar and contributors
// For license information, please see license.txt

frappe.ui.form.on('ICICI Payment Intimation', {
	refresh: function(frm) {
		// Add custom buttons based on status
		if (!frm.doc.__islocal) {
			if (frm.doc.status === 'Received') {
				frm.add_custom_button(__('Process Payment'), function() {
					process_payment_intimation(frm);
				}, __('Actions'));
			}

			if (frm.doc.status === 'Failed') {
				frm.add_custom_button(__('Retry Processing'), function() {
					retry_payment_processing(frm);
				}, __('Actions'));
			}

			if (frm.doc.payment_entry) {
				frm.add_custom_button(__('View Payment Entry'), function() {
					frappe.set_route('Form', 'Payment Entry', frm.doc.payment_entry);
				});
			}

			frm.add_custom_button(__('View Virtual Account'), function() {
				view_virtual_account(frm);
			});

			// Add status indicators
			if (frm.doc.status === 'Processed') {
				frm.dashboard.set_headline_alert(__('Payment Processed Successfully'), 'green');
			} else if (frm.doc.status === 'Failed') {
				frm.dashboard.set_headline_alert(__('Payment Processing Failed'), 'red');
			} else if (frm.doc.status === 'Received') {
				frm.dashboard.set_headline_alert(__('Payment Received - Pending Processing'), 'orange');
			}
		}

		// Set read-only fields
		frm.set_df_property('bank_response', 'read_only', 1);
		frm.set_df_property('processed_date', 'read_only', 1);
		frm.set_df_property('retry_count', 'read_only', 1);
		frm.set_df_property('payment_entry', 'read_only', 1);

		// Format currency
		if (frm.doc.transaction_amount) {
			frm.set_df_property('transaction_amount', 'description', 
				`Amount: ${format_currency(frm.doc.transaction_amount)}`);
		}
	},

	virtual_account_number: function(frm) {
		// Validate virtual account exists
		if (frm.doc.virtual_account_number) {
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'ICICI Virtual Account',
					filters: {'virtual_account_number': frm.doc.virtual_account_number},
					fieldname: ['party_type', 'party', 'company']
				},
				callback: function(r) {
					if (r.message) {
						frm.set_df_property('virtual_account_number', 'description', 
							`Linked to: ${r.message.party_type} - ${r.message.party}`);
					} else {
						frm.set_df_property('virtual_account_number', 'description', 
							'Virtual Account not found');
					}
				}
			});
		}
	}
});

function process_payment_intimation(frm) {
	frappe.confirm(
		__('Process this payment intimation and create Payment Entry?'),
		function() {
			frappe.call({
				method: 'bank_ecollection.bank_ecollection.doctype.icici_payment_intimation.icici_payment_intimation.process_payment_intimation',
				args: {
					intimation_name: frm.doc.name
				},
				callback: function(r) {
					if (r.message) {
						if (r.message.success) {
							frappe.msgprint({
								title: __('Processing Successful'),
								message: r.message.message,
								indicator: 'green'
							});
							frm.reload_doc();
						} else {
							frappe.msgprint({
								title: __('Processing Failed'),
								message: r.message.message,
								indicator: 'red'
							});
						}
					}
				}
			});
		}
	);
}

function retry_payment_processing(frm) {
	frappe.confirm(
		__('Retry processing this failed payment intimation?'),
		function() {
			frappe.call({
				method: 'bank_ecollection.bank_ecollection.doctype.icici_payment_intimation.icici_payment_intimation.retry_failed_intimation',
				args: {
					intimation_name: frm.doc.name
				},
				callback: function(r) {
					if (r.message) {
						if (r.message.success) {
							frappe.msgprint({
								title: __('Retry Successful'),
								message: r.message.message,
								indicator: 'green'
							});
							frm.reload_doc();
						} else {
							frappe.msgprint({
								title: __('Retry Failed'),
								message: r.message.message,
								indicator: 'red'
							});
						}
					}
				}
			});
		}
	);
}

function view_virtual_account(frm) {
	if (frm.doc.virtual_account_number) {
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				doctype: 'ICICI Virtual Account',
				filters: {'virtual_account_number': frm.doc.virtual_account_number},
				fieldname: 'name'
			},
			callback: function(r) {
				if (r.message && r.message.name) {
					frappe.set_route('Form', 'ICICI Virtual Account', r.message.name);
				} else {
					frappe.msgprint(__('Virtual Account not found'));
				}
			}
		});
	}
}
