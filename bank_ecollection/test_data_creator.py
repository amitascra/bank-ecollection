import frappe
from frappe.utils import random_string, today, add_days

@frappe.whitelist()
def create_test_data():
    """Create test data for ICICI integration"""
    
    try:
        print("=== Setting up ICICI Test Data ===")
        
        # 1. Setup ICICI Settings
        settings = frappe.get_single("ICICI Settings")
        settings.environment = "UAT"
        settings.enable_integration = 0  # Disabled initially
        settings.enable_customer_integration = 0
        settings.auto_create_payment_entry = 1
        settings.auto_submit_payment_entry = 0
        
        # Test credentials
        settings.client_code = "TEST_CLIENT_001"
        settings.set("api_key", "test_api_key_12345")
        settings.webhook_username = "icici_webhook_user"
        settings.set("webhook_password", "icici_webhook_pass_123")
        settings.webhook_ip_whitelist = "127.0.0.1,::1,103.14.97.178,103.14.97.179"
        
        # Set default company
        companies = frappe.get_all("Company", limit=1)
        if companies:
            settings.default_company = companies[0].name
        
        settings.save(ignore_permissions=True)
        print("✓ ICICI Settings configured")
        
        # 2. Create test customer
        customer_name = "TEST-CUSTOMER-001"
        if not frappe.db.exists("Customer", customer_name):
            customer = frappe.new_doc("Customer")
            customer.customer_name = "Test Customer for ICICI Integration"
            customer.customer_type = "Individual"
            customer.customer_group = "All Customer Groups"
            customer.territory = "All Territories"
            customer.company = settings.default_company
            customer.email_id = "test.customer@example.com"
            customer.mobile_no = "9876543210"
            customer.insert(ignore_permissions=True)
            print(f"✓ Test customer created: {customer.name}")
        else:
            print(f"✓ Test customer already exists: {customer_name}")
        
        # 3. Create test bank account
        bank_account_name = f"ICICI Test Account - {settings.default_company}"
        if not frappe.db.exists("Bank Account", bank_account_name):
            # Create bank if not exists
            if not frappe.db.exists("Bank", "ICICI Bank"):
                bank = frappe.new_doc("Bank")
                bank.bank_name = "ICICI Bank"
                bank.insert(ignore_permissions=True)
            
            bank_account = frappe.new_doc("Bank Account")
            bank_account.account_name = bank_account_name
            bank_account.bank = "ICICI Bank"
            bank_account.company = settings.default_company
            bank_account.is_company_account = 1
            bank_account.insert(ignore_permissions=True)
            print(f"✓ Bank Account created: {bank_account_name}")
        else:
            print(f"✓ Bank Account already exists: {bank_account_name}")
        
        # Update settings with bank account
        settings.default_bank_account = bank_account_name
        settings.save(ignore_permissions=True)
        
        # 4. Create test virtual accounts
        va_numbers = ["TEST123456789", "TEST987654321", "TEST555666777"]
        created_vas = []
        
        for va_number in va_numbers:
            if not frappe.db.exists("ICICI Virtual Account", {"virtual_account_number": va_number}):
                va = frappe.new_doc("ICICI Virtual Account")
                va.virtual_account_number = va_number
                va.bank_account = bank_account_name
                va.party_type = "Customer"
                va.party = customer_name
                va.company = settings.default_company
                va.status = "Active"
                va.insert(ignore_permissions=True)
                created_vas.append(va_number)
                print(f"✓ Virtual Account created: {va_number}")
            else:
                created_vas.append(va_number)
                print(f"✓ Virtual Account already exists: {va_number}")
        
        # 5. Create test payment intimations
        test_payments = [
            {"va": created_vas[0], "amount": 10000.00, "mode": "NEFT", "remitter": "Test Customer A"},
            {"va": created_vas[1] if len(created_vas) > 1 else created_vas[0], "amount": 25000.00, "mode": "RTGS", "remitter": "Test Customer B"},
            {"va": created_vas[2] if len(created_vas) > 2 else created_vas[0], "amount": 5000.00, "mode": "IMPS", "remitter": "Test Customer C"}
        ]
        
        for i, payment in enumerate(test_payments):
            utr_number = f"UTR{random_string(10).upper()}"
            
            intimation = frappe.new_doc("ICICI Payment Intimation")
            intimation.virtual_account_number = payment["va"]
            intimation.utr_number = utr_number
            intimation.transaction_amount = payment["amount"]
            intimation.payment_mode = payment["mode"]
            intimation.transaction_date = add_days(today(), -i)
            intimation.remitter_name = payment["remitter"]
            intimation.remitter_account = f"12345678{i:02d}"
            intimation.remitter_ifsc = "ICIC0001234"
            intimation.status = "Pending"
            
            intimation.insert(ignore_permissions=True)
            print(f"✓ Payment Intimation created: {utr_number} - ₹{payment['amount']:,.2f}")
        
        # 6. Create test bank transactions
        test_transactions = [
            {"amount": 12000.00, "desc": "ICICI Virtual Account Payment - Customer A"},
            {"amount": 8500.00, "desc": "ICICI Virtual Account Payment - Customer B"},
            {"amount": 30000.00, "desc": "ICICI Virtual Account Payment - Customer C"}
        ]
        
        for i, txn in enumerate(test_transactions):
            ref_number = f"TEST{random_string(8).upper()}"
            
            bt = frappe.new_doc("Bank Transaction")
            bt.date = add_days(today(), -i)
            bt.bank_account = bank_account_name
            bt.deposit = txn["amount"]
            bt.withdrawal = 0.0
            bt.currency = "INR"
            bt.reference_number = ref_number
            bt.description = txn["desc"]
            bt.status = "Pending"
            
            bt.insert(ignore_permissions=True)
            bt.submit()
            
            print(f"✓ Bank Transaction created: {ref_number} - ₹{txn['amount']:,.2f}")
        
        # 7. Enable integration
        settings.enable_integration = 1
        settings.enable_customer_integration = 1
        settings.save(ignore_permissions=True)
        print("✓ ICICI integration enabled")
        
        frappe.db.commit()
        
        result = {
            "success": True,
            "message": "Test data created successfully!",
            "data": {
                "customer": customer_name,
                "bank_account": bank_account_name,
                "virtual_accounts": created_vas,
                "payment_intimations": len(test_payments),
                "bank_transactions": len(test_transactions)
            }
        }
        
        print("\n🎉 Test data setup completed successfully!")
        print(f"Created: {customer_name}, {bank_account_name}, {len(created_vas)} VAs, {len(test_payments)} PIs, {len(test_transactions)} BTs")
        
        return result
        
    except Exception as e:
        frappe.db.rollback()
        error_msg = f"Error creating test data: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "message": error_msg}
