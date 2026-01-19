# ICICI Bank e-Collection UAT Testing Guide

## 🎯 **UAT Environment Configuration**

### **ICICI UAT Endpoints (Updated)**
- **Bene Upload API**: `https://uat-onprem-dmz-hybrid.icicibank.com/apibanking/live/corpapi/ixc/v2/beneupload`
- **Enquiry API**: `https://uat-onprem-dmz-hybrid.icicibank.com/misenquiry/status`

### **IP Whitelisting**
- **UAT API Access**: `103.87.42.45:443`
- **Webhook Source IPs**: 
  - `103.87.42.133`
  - `103.87.43.222`
  - `103.87.43.226`

## 🔧 **Setup Steps**

### **1. Configure ICICI Settings**
Navigate to: **ICICI Integration → ICICI Settings**

**Required Configuration:**
```
Environment: UAT
Client Code: [Your ICICI Client Code]
API Key: [Your ICICI API Key]
Enable Integration: ✓
Enable Customer Integration: ✓
Enable Supplier Integration: ✓
Auto Create Payment Entry: ✓
Auto Submit Payment Entry: ✗ (Keep draft for testing)
```

**Auto-populated URLs:**
- Bene Upload URL: `https://uat-onprem-dmz-hybrid.icicibank.com/apibanking/live/corpapi/ixc/v2/beneupload`
- Enquiry URL: `https://uat-onprem-dmz-hybrid.icicibank.com/misenquiry/status`
- Webhook IPs: `103.87.42.133, 103.87.43.222, 103.87.43.226`

### **2. Generate RSA Encryption Keys**
```python
# In ERPNext Console
from bank_ecollection.api.encryption import generate_key_pair
result = generate_key_pair()
print("Public Key:", result["public_key"][:100] + "...")
print("Private Key:", result["private_key"][:100] + "...")
```

**Save keys to:**
- Public Key: `/sites/ascra.refurb/private/files/icici_public_key.pem`
- Private Key: `/sites/ascra.refurb/private/files/icici_private_key.pem`

### **3. Configure Webhook**
**Webhook URL**: `https://your-domain.com/api/icici/intimation`

**Webhook Credentials:**
- Username: `icici_webhook_user`
- Password: `icici_webhook_pass_123`

## 🧪 **Testing Procedures**

### **Test 1: Encryption Functionality**
```python
from bank_ecollection.api.encryption import test_encryption
result = test_encryption()
print(result)
# Expected: {"success": True, "message": "Encryption test successful"}
```

### **Test 2: Virtual Account Creation**
1. Create a test Customer:
   - Name: "Test Customer ICICI"
   - Customer Type: Individual
   - Email: test@example.com

2. Check ICICI Virtual Account creation:
   ```python
   from bank_ecollection.api.bene_upload import create_virtual_account
   customer = frappe.get_doc("Customer", "TEST-CUSTOMER-001")
   result = create_virtual_account(customer, "after_insert")
   print(result)
   ```

### **Test 3: Webhook Endpoint**
```python
from bank_ecollection.api.intimation_webhook import test_webhook_endpoint
result = test_webhook_endpoint()
print(result)
# Expected: {"success": True, "message": "Webhook test successful"}
```

### **Test 4: API Connection Test**
```python
from bank_ecollection.bank_e_collection.doctype.icici_settings.icici_settings import test_api_connection
result = test_api_connection()
print(result)
```

### **Test 5: Transaction Enquiry**
```python
from bank_ecollection.api.enquiry import query_transaction_status
result = query_transaction_status(from_date="2026-01-01", to_date="2026-01-19")
print(result)
```

## 📋 **Test Scenarios**

### **Scenario 1: Customer Virtual Account Workflow**
1. **Create Customer** → Auto-creates ICICI Virtual Account
2. **Verify VA Creation** → Check ICICI Virtual Account doctype
3. **Test API Call** → Verify Bene Upload API integration
4. **Check Status** → Confirm VA status and bank response

### **Scenario 2: Payment Notification Workflow**
1. **Simulate Payment** → Use webhook test endpoint
2. **Create Intimation** → Verify ICICI Payment Intimation creation
3. **Process Payment** → Auto-create Payment Entry
4. **Verify Reconciliation** → Check Payment Entry linkage

### **Scenario 3: Error Handling**
1. **Invalid API Key** → Test error handling
2. **Network Issues** → Test retry mechanisms
3. **Invalid Data** → Test validation errors
4. **Webhook Security** → Test IP whitelisting

## 🔍 **Monitoring & Debugging**

### **Check Integration Status**
```python
from bank_ecollection.utils.uat_setup import get_uat_status
status = get_uat_status()
print(status)
```

### **View Error Logs**
Navigate to: **Settings → Error Log**
Filter by: `icici` or `bank_ecollection`

### **Monitor Virtual Accounts**
Navigate to: **ICICI Integration → ICICI Virtual Account**
Check: Status, Bank Response, Error Messages

### **Monitor Payment Intimations**
Navigate to: **ICICI Integration → ICICI Payment Intimation**
Check: Processing Status, Payment Entry Links

## 🚀 **Production Readiness Checklist**

### **Security**
- [ ] Real RSA keys generated and secured
- [ ] Production API credentials configured
- [ ] IP whitelisting configured for production
- [ ] Webhook authentication secured

### **Configuration**
- [ ] Production URLs configured
- [ ] Default accounts set up
- [ ] Company settings configured
- [ ] Mode of payments created

### **Testing**
- [ ] All UAT tests passed
- [ ] End-to-end workflow tested
- [ ] Error scenarios handled
- [ ] Performance testing completed

### **Monitoring**
- [ ] Scheduled tasks configured
- [ ] Error logging enabled
- [ ] Reconciliation procedures tested
- [ ] Backup procedures in place

## 📞 **Support & Troubleshooting**

### **Common Issues**

1. **Virtual Account Creation Fails**
   - Check API credentials
   - Verify encryption keys
   - Check network connectivity to UAT

2. **Webhook Not Receiving**
   - Verify webhook URL accessibility
   - Check IP whitelisting
   - Validate authentication credentials

3. **Payment Processing Errors**
   - Check default account configuration
   - Verify party account mappings
   - Review error logs

### **Contact Information**
- **Technical Support**: amit@ascratech.com
- **ICICI Support**: [Your ICICI contact]
- **Documentation**: See README.md

## 📈 **Next Steps**

1. **Complete UAT Testing** with actual ICICI credentials
2. **Performance Testing** with high transaction volumes
3. **Security Review** of encryption and authentication
4. **Production Deployment** after successful UAT
5. **User Training** on ICICI integration features
6. **Go-Live Support** during initial production use

---

**Note**: This integration is ready for UAT testing. Update the client code and API key with actual ICICI credentials to begin testing with the UAT environment.
