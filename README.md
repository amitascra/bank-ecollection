# ICICI Bank e-Collection Integration for ERPNext

A comprehensive ERPNext app for integrating ICICI Bank's e-Collection services, enabling automated virtual account management, payment processing, and reconciliation.

## Features

### 🏦 **Core Integration**
- **Virtual Account Management**: Automatic creation of ICICI virtual accounts for Customers/Suppliers
- **Real-time Payment Notifications**: Webhook-based payment intimations from ICICI Bank
- **Automated Payment Processing**: Auto-creation of Payment Entries from bank notifications
- **Transaction Reconciliation**: Daily reconciliation between ICICI and ERPNext records

### 🔐 **Security & Encryption**
- **RSA 4096-bit Encryption**: Secure API communication with ICICI Bank
- **IP Whitelisting**: Webhook security with configurable IP restrictions
- **Authentication**: Basic auth support for webhook endpoints

### 📊 **Management & Monitoring**
- **Comprehensive Dashboard**: Monitor virtual accounts and payment processing
- **Error Handling**: Robust error logging and retry mechanisms
- **Scheduled Tasks**: Automated daily reconciliation and hourly sync
- **Audit Trail**: Complete transaction history and status tracking

## Installation

1. **Install the app:**
   ```bash
   bench get-app https://github.com/your-repo/bank_ecollection
   bench --site your-site install-app bank_ecollection
   ```

2. **Run migrations:**
   ```bash
   bench --site your-site migrate
   ```

## Configuration

### 1. ICICI Settings Setup
Navigate to **ICICI Settings** and configure:

- **Environment**: UAT or Production
- **Client Code**: Your ICICI client code
- **API Key**: ICICI provided API key
- **Encryption Keys**: RSA public/private key paths
- **Webhook Credentials**: Username/password for webhook authentication
- **Default Accounts**: Company, bank account, and cash account settings

### 2. Generate Encryption Keys
```python
# In ERPNext console
from bank_ecollection.api.encryption import generate_key_pair
result = generate_key_pair()
print(result)
```

### 3. Webhook Configuration
Configure your ICICI webhook URL as:
```
https://your-domain.com/api/icici/intimation
```

## API Endpoints

### Webhook Endpoints
- `POST /api/icici/intimation` - Receive payment notifications from ICICI

### Management APIs
- `bank_ecollection.api.bene_upload.manual_upload_beneficiary` - Manual virtual account creation
- `bank_ecollection.api.enquiry.query_transaction_status` - Query transaction status
- `bank_ecollection.api.encryption.test_encryption` - Test encryption functionality

## Doctypes

### ICICI Settings (Single)
Central configuration for ICICI integration settings.

### ICICI Virtual Account
Manages virtual accounts linked to ERPNext Customers/Suppliers.

### ICICI Payment Intimation
Records payment notifications received from ICICI Bank.

## Workflow

1. **Customer/Supplier Creation** → Automatic virtual account creation via ICICI API
2. **Payment Made to Virtual Account** → ICICI sends webhook notification
3. **Webhook Processing** → Creates Payment Intimation record
4. **Auto Payment Processing** → Creates Payment Entry in ERPNext
5. **Reconciliation** → Daily sync ensures data consistency

## Testing

### Test Webhook Endpoint
```python
from bank_ecollection.api.intimation_webhook import test_webhook_endpoint
result = test_webhook_endpoint()
print(result)
```

### Test API Connection
```python
from bank_ecollection.bank_e_collection.doctype.icici_settings.icici_settings import test_api_connection
result = test_api_connection()
print(result)
```

## Scheduled Tasks

- **Daily Reconciliation**: Compares ICICI and ERPNext transaction records
- **Hourly Sync**: Processes pending payment intimations
- **Monthly Cleanup**: Archives old records and generates reports

## Troubleshooting

### Common Issues

1. **Virtual Account Creation Fails**
   - Check ICICI Settings configuration
   - Verify API credentials and environment
   - Check encryption key setup

2. **Webhook Not Receiving Notifications**
   - Verify webhook URL configuration in ICICI portal
   - Check IP whitelisting settings
   - Validate webhook credentials

3. **Payment Processing Errors**
   - Review Payment Intimation error messages
   - Check default account configurations
   - Verify party account mappings

### Logs and Monitoring
- Check **Error Log** doctype for integration errors
- Monitor **ICICI Payment Intimation** status
- Review **ICICI Virtual Account** sync status

## Development

### File Structure
```
bank_ecollection/
├── bank_e_collection/
│   ├── doctype/
│   │   ├── icici_settings/
│   │   ├── icici_virtual_account/
│   │   └── icici_payment_intimation/
├── api/
│   ├── bene_upload.py
│   ├── intimation_webhook.py
│   ├── enquiry.py
│   └── encryption.py
├── utils/
│   ├── virtual_account.py
│   └── payment_handler.py
└── tasks/
    └── scheduled_tasks.py
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:
- Email: amit@ascratech.com
- Create an issue in the repository
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
