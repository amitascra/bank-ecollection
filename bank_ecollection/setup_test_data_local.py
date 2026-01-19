#!/usr/bin/env python3

import frappe
import os
from frappe.utils import random_string, now, today, add_days

def setup_test_data_local():
    """Setup test data for ICICI integration without API calls"""
    
    print("=== Setting up ICICI Test Data (Local Mode) ===")
    
    # 1. Setup ICICI Settings with integration disabled initially
    settings = setup_icici_settings_disabled()
    
    # 2. Create test customer (hooks won't trigger since integration is disabled)
    customer_name = create_test_customer_local()
    
    # 3. Create test virtual accounts (manually without API)
    va_numbers = create_test_virtual_accounts_local(customer_name)
    
    # 4. Create test payment intimations
    create_test_payment_intimations(va_numbers)
    
    # 5. Create test bank transactions
    create_test_bank_transactions()
    
    # 6. Re-enable integration now that test data is created
    enable_icici_integration(settings)
    
    print("=== Test Data Setup Complete ===")
    return True

def setup_icici_settings_disabled():
    """Setup ICICI Settings with UAT configuration but integration disabled"""
    print("Setting up ICICI Settings (integration disabled)...")
    
    settings = frappe.get_single("ICICI Settings")
    
    # UAT Configuration - but keep integration disabled initially
    settings.environment = "UAT"
    settings.enable_integration = 0  # Disabled initially
    settings.enable_customer_integration = 0  # Disabled initially
    settings.enable_supplier_integration = 0  # Disabled initially
    settings.auto_create_payment_entry = 1
    settings.auto_submit_payment_entry = 0  # Keep draft for testing
    
    # UAT URLs
    settings.bene_upload_url = "https://apibankingone.icicibank.com/api/Corporate/CIB/v1/Transaction"
    settings.enquiry_url = "https://apibankingone.icicibank.com/api/Corporate/CIB/v1/Enquiry"
    
    # Test credentials
    settings.client_code = "TEST_CLIENT_001"
    settings.set("api_key", "test_api_key_12345")
    
    # Webhook configuration
    settings.webhook_username = "icici_webhook_user"
    settings.set("webhook_password", "icici_webhook_pass_123")
    settings.webhook_ip_whitelist = "127.0.0.1,::1,103.14.97.178,103.14.97.179"
    
    # Set default company
    companies = frappe.get_all("Company", limit=1)
    if companies:
        settings.default_company = companies[0].name
    
    # Generate and set encryption keys
    setup_encryption_keys(settings)
    
    settings.save(ignore_permissions=True)
    print(f"✓ ICICI Settings configured for {settings.environment} environment (integration disabled)")
    
    return settings

def enable_icici_integration(settings):
    """Enable ICICI integration after test data is created"""
    print("Enabling ICICI integration...")
    
    settings.enable_integration = 1
    settings.enable_customer_integration = 1
    settings.enable_supplier_integration = 1
    settings.save(ignore_permissions=True)
    
    print("✓ ICICI integration enabled")

def setup_encryption_keys(settings):
    """Generate test encryption keys"""
    try:
        # Create keys directory
        keys_dir = os.path.join(frappe.get_site_path(), "private", "files", "icici_keys")
        os.makedirs(keys_dir, exist_ok=True)
        
        public_key_path = os.path.join(keys_dir, "icici_public_key.pem")
        private_key_path = os.path.join(keys_dir, "icici_private_key.pem")
        
        # Create dummy key files for testing
        public_key_content = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1234567890ABCDEF...
(This is a dummy public key for testing purposes only)
-----END PUBLIC KEY-----"""
        
        private_key_content = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDXYZ1234567890...
(This is a dummy private key for testing purposes only)
-----END PRIVATE KEY-----"""
        
        with open(public_key_path, 'w') as f:
            f.write(public_key_content)
        
        with open(private_key_path, 'w') as f:
            f.write(private_key_content)
        
        # Set proper permissions
        os.chmod(public_key_path, 0o644)
        os.chmod(private_key_path, 0o600)
        
        settings.public_key_path = public_key_path
        settings.private_key_path = private_key_path
        
        print("✓ Test encryption keys generated")
        
    except Exception as e:
        print(f"⚠ Encryption key setup failed: {str(e)}")

def create_test_customer_local():
    """Create test customer without triggering ICICI hooks"""
    print("Creating test customer...")
    
    customer_name = "TEST-CUSTOMER-001"
    
    if frappe.db.exists("Customer", customer_name):
        print(f"✓ Test customer {customer_name} already exists")
        return customer_name
    
    # Get default settings
    settings = frappe.get_single("ICICI Settings")
    company = settings.default_company or frappe.get_all("Company", limit=1)[0].name
    
    # Temporarily disable hooks
    frappe.flags.ignore_hooks = True
    
    customer = frappe.new_doc("Customer")
    customer.customer_name = "Test Customer for ICICI Integration"
    customer.customer_type = "Individual"
    customer.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
    customer.territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
    customer.company = company
    customer.email_id = "test.customer@example.com"
    customer.mobile_no = "9876543210"
    
    customer.insert(ignore_permissions=True)
    
    # Re-enable hooks
    frappe.flags.ignore_hooks = False
    
    print(f"✓ Test customer created: {customer.name}")
    return customer.name

def create_test_virtual_accounts_local(customer_name):
    """Create test virtual accounts manually"""
    print("Creating test virtual accounts...")
    
    va_numbers = [
        "TEST123456789",
        "TEST987654321", 
        "TEST555666777"
    ]
    
    settings = frappe.get_single("ICICI Settings")
    
    # Try to create a test bank account, but continue even if it fails
    try:
        bank_account = create_test_bank_account(settings.default_company)
    except Exception as e:
        print(f"⚠ Bank account creation failed: {str(e)}")
        # Get any existing bank account or use None
        existing_accounts = frappe.get_all("Bank Account", limit=1)
        bank_account = existing_accounts[0].name if existing_accounts else None
    
    created_vas = []
    
    for va_number in va_numbers:
        if frappe.db.exists("ICICI Virtual Account", {"virtual_account_number": va_number}):
            print(f"✓ Virtual Account {va_number} already exists")
            created_vas.append(va_number)
            continue
        
        va = frappe.new_doc("ICICI Virtual Account")
        va.virtual_account_number = va_number
        # Only set bank_account if we have one
        if bank_account:
            va.bank_account = bank_account
        va.party_type = "Customer"
        va.party = customer_name
        va.company = settings.default_company
        va.status = "Active"
        va.creation_date = today()
        
        # Add dummy bank response
        va.bank_response = {
            "successFlag": "1",
            "message": "Virtual Account created successfully (Test Data)",
            "virtualAccountNumber": va_number,
            "status": "Active"
        }
        
        try:
            va.insert(ignore_permissions=True)
            created_vas.append(va_number)
            print(f"✓ Virtual Account created: {va_number}")
        except Exception as e:
            print(f"⚠ Failed to create Virtual Account {va_number}: {str(e)}")
            # Continue with other VAs
    
    return created_vas

def create_test_bank_account(company):
    """Create test bank account for ICICI"""
    bank_account_name = "ICICI Test Account - " + company
    
    if frappe.db.exists("Bank Account", bank_account_name):
        return bank_account_name
    
    # Create bank if not exists
    if not frappe.db.exists("Bank", "ICICI Bank"):
        bank = frappe.new_doc("Bank")
        bank.bank_name = "ICICI Bank"
        bank.insert(ignore_permissions=True)
    
    # Create bank account
    bank_account = frappe.new_doc("Bank Account")
    bank_account.account_name = bank_account_name
    bank_account.bank = "ICICI Bank"
    bank_account.company = company
    bank_account.is_company_account = 1
    # Don't set account_type as it's causing validation issues
    
    bank_account.insert(ignore_permissions=True)
    frappe.db.commit()  # Ensure bank account is committed before referencing
    
    print(f"✓ Bank Account created: {bank_account_name}")
    return bank_account_name

def create_test_payment_intimations(va_numbers):
    """Create test payment intimations"""
    print("Creating test payment intimations...")
    
    if not va_numbers:
        print("⚠ No virtual accounts available for payment intimations")
        return
    
    # Use only available VA numbers
    test_payments = []
    if len(va_numbers) >= 1:
        test_payments.extend([
            {"va": va_numbers[0], "amount": 10000.00, "mode": "NEFT", "remitter": "Test Customer A"},
            {"va": va_numbers[0], "amount": 25000.00, "mode": "RTGS", "remitter": "Test Customer B"},
        ])
    if len(va_numbers) >= 2:
        test_payments.extend([
            {"va": va_numbers[1], "amount": 5000.00, "mode": "IMPS", "remitter": "Test Customer C"},
            {"va": va_numbers[1], "amount": 15000.00, "mode": "UPI", "remitter": "Test Customer D"},
        ])
    if len(va_numbers) >= 3:
        test_payments.append({"va": va_numbers[2], "amount": 50000.00, "mode": "NEFT", "remitter": "Test Customer E"})
    
    # If we have fewer VAs, just use the first one for all payments
    if len(va_numbers) == 1:
        test_payments = [
            {"va": va_numbers[0], "amount": 10000.00, "mode": "NEFT", "remitter": "Test Customer A"},
            {"va": va_numbers[0], "amount": 25000.00, "mode": "RTGS", "remitter": "Test Customer B"},
            {"va": va_numbers[0], "amount": 5000.00, "mode": "IMPS", "remitter": "Test Customer C"},
            {"va": va_numbers[0], "amount": 15000.00, "mode": "UPI", "remitter": "Test Customer D"},
            {"va": va_numbers[0], "amount": 50000.00, "mode": "NEFT", "remitter": "Test Customer E"}
        ]
    
    for i, payment in enumerate(test_payments):
        utr_number = f"UTR{random_string(10).upper()}"
        
        if frappe.db.exists("ICICI Payment Intimation", {"utr_number": utr_number}):
            continue
        
        intimation = frappe.new_doc("ICICI Payment Intimation")
        intimation.virtual_account_number = payment["va"]
        intimation.utr_number = utr_number
        intimation.transaction_amount = payment["amount"]
        intimation.payment_mode = payment["mode"]
        intimation.transaction_date = add_days(today(), -i)  # Spread over last few days
        intimation.remitter_name = payment["remitter"]
        intimation.remitter_account = f"12345678{i:02d}"
        intimation.remitter_ifsc = "ICIC0001234"
        intimation.status = "Pending"
        
        # Add dummy bank response
        intimation.bank_response = {
            "virtualAccountNumber": payment["va"],
            "utrNumber": utr_number,
            "amount": payment["amount"],
            "paymentMode": payment["mode"],
            "remitterName": payment["remitter"]
        }
        
        intimation.insert(ignore_permissions=True)
        print(f"✓ Payment Intimation created: {utr_number} - ₹{payment['amount']:,.2f}")

def create_test_bank_transactions():
    """Create test bank transactions for ERPNext banking integration"""
    print("Creating test bank transactions...")
    
    # Get ICICI bank account
    bank_accounts = frappe.get_all("Bank Account", 
        filters={"bank": "ICICI Bank", "is_company_account": 1}, 
        limit=1)
    
    if not bank_accounts:
        print("⚠ No ICICI bank account found for creating bank transactions")
        return
    
    bank_account = bank_accounts[0].name
    
    test_transactions = [
        {"amount": 12000.00, "ref": "BT001", "desc": "ICICI Virtual Account Payment - Customer A"},
        {"amount": 8500.00, "ref": "BT002", "desc": "ICICI Virtual Account Payment - Customer B"},
        {"amount": 30000.00, "ref": "BT003", "desc": "ICICI Virtual Account Payment - Customer C"},
        {"amount": 7500.00, "ref": "BT004", "desc": "ICICI Virtual Account Payment - Customer D"}
    ]
    
    for i, txn in enumerate(test_transactions):
        ref_number = f"TEST{random_string(8).upper()}"
        
        bt = frappe.new_doc("Bank Transaction")
        bt.date = add_days(today(), -i)
        bt.bank_account = bank_account
        bt.deposit = txn["amount"]
        bt.withdrawal = 0.0
        bt.currency = "INR"
        bt.reference_number = ref_number
        bt.description = txn["desc"]
        bt.status = "Pending"
        
        bt.insert(ignore_permissions=True)
        bt.submit()
        
        print(f"✓ Bank Transaction created: {ref_number} - ₹{txn['amount']:,.2f}")

if __name__ == "__main__":
    # This will be executed via bench execute, so frappe is already initialized
    try:
        setup_test_data_local()
        frappe.db.commit()
        print("\n🎉 All test data created successfully!")
        print("\nYou can now test:")
        print("- ICICI Integration workspace")
        print("- Virtual Accounts with dummy data")
        print("- Payment Intimations with sample transactions")
        print("- Bank Transactions for reconciliation")
        print("- ERPNext Banking workflow")
        
    except Exception as e:
        frappe.db.rollback()
        print(f"\n❌ Error setting up test data: {str(e)}")
        import traceback
        traceback.print_exc()
