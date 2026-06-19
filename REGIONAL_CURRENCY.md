# SecurePay — Regional Currency Support

## Overview

SecurePay now supports regional currency detection and management. Users are automatically assigned a currency based on their region when they sign up, and they can change their region/currency at any time.

## Features

### 1. **Automatic Region Detection on Registration**
When a user signs up, their region is automatically detected from:
- `X-Region` header (if provided by frontend)
- `Accept-Language` header (extracts country code from language preference)
- Defaults to `US` if no region is detected

### 2. **Supported Regions & Currencies**

| Region Code | Region Name | Currency | Symbol |
|------------|-------------|----------|--------|
| IN | India | INR | ₹ |
| US | United States | USD | $ |
| GB | United Kingdom | GBP | £ |
| EU | Europe | EUR | € |
| DE | Germany | EUR | € |
| CA | Canada | CAD | C$ |
| AU | Australia | AUD | A$ |
| JP | Japan | JPY | ¥ |
| SG | Singapore | SGD | S$ |
| BR | Brazil | BRL | R$ |
| ZA | South Africa | ZAR | R |
| AE | UAE | AED | د.إ |

And more... See `app/utils/region.py` for the complete list.

## API Endpoints

### Get Available Regions
```http
GET /api/profile/regions
```

**Response:**
```json
{
  "regions": [
    {
      "code": "IN",
      "name": "India",
      "currency": "INR",
      "symbol": "₹"
    },
    ...
  ]
}
```

### Get User's Current Region
```http
GET /api/profile/region
Authorization: Bearer <token>
```

**Response:**
```json
{
  "region": "IN",
  "regionName": "India",
  "currency": "INR",
  "symbol": "₹"
}
```

### Update User's Region
```http
PUT /api/profile/region
Authorization: Bearer <token>
Content-Type: application/json

{
  "region": "IN"
}
```

**Response:**
```json
{
  "region": "IN",
  "regionName": "India",
  "currency": "INR",
  "symbol": "₹"
}
```

## Database Changes

The following fields were added:

### `users` table
- `region` (VARCHAR(2), DEFAULT 'US') - ISO 3166-1 alpha-2 country code

### `accounts` table
- `currency` (VARCHAR(3), DEFAULT 'USD') - Updated with user's currency

## Migration

### Option 1: Fresh Database (Recommended for development)
```bash
# Delete your old database
# For MySQL: DROP DATABASE apexpay;

# Run seed script to create fresh database with new schema
python seed.py
```

### Option 2: Migrate Existing Database
```bash
python migrate_regional_currency.py
```

This script will:
1. Add the `region` column to the `users` table
2. Add/update the `currency` column in the `accounts` table
3. Handle cases where columns already exist

## Usage in Frontend

### Display Currency Symbol
```javascript
// After fetching user profile
const user = response.user;
console.log(user.currency); // "INR"
console.log(user.region);   // "IN"

// Use in formatting
const formatted = `${symbol} ${amount.toFixed(2)}`;
// e.g., "₹ 1,234.50"
```

### Update User Region
```javascript
const response = await fetch('/api/profile/region', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ region: 'IN' })
});

const data = await response.json();
console.log(data.currency); // "INR"
```

### Pass Region in Registration
```javascript
// The frontend can pass region hint in headers
const response = await fetch('/api/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept-Language': 'en-IN', // Auto-detected from this
    // OR explicitly:
    'X-Region': 'IN', // ISO country code
  },
  body: JSON.stringify({
    fullName: 'User Name',
    email: 'user@example.com',
    password: 'SecurePass123'
  })
});
```

## Utility Functions

Available in `app/utils/region.py`:

```python
from app.utils.region import (
    detect_region_from_request,        # Auto-detect from request
    get_currency_for_region,           # Get currency code for region
    get_currency_symbol,               # Get symbol for currency
    get_region_name,                   # Get display name for region
    format_currency,                   # Format amount as currency string
)

# Examples
region = detect_region_from_request()  # Returns 'IN'
currency = get_currency_for_region('IN')  # Returns 'INR'
symbol = get_currency_symbol('INR')    # Returns '₹'
name = get_region_name('IN')           # Returns 'India'
formatted = format_currency(1234.50, 'INR')  # Returns '₹ 1,234.50'
```

## Model Updates

### User Model
```python
class User(db.Model):
    # ... existing fields ...
    region = db.Column(db.String(2), default="US")
    
    def to_dict(self, include_balance=True):
        # ... includes 'region' in response ...
        return {
            "region": self.region,
            # ... other fields ...
        }
```

### Account Model
- Already had `currency` field, now properly set during account creation

### Transaction Model
- Already had `currency` field, now properly set during transaction creation

## Examples

### Example 1: Indian User Registration
1. User from India accesses the app
2. `Accept-Language: en-IN` is sent in the request
3. System detects region as `IN`
4. User's currency is set to `INR` automatically
5. All transactions show in `₹`

### Example 2: Change Region
1. User updates their region to `GB` via settings
2. `PUT /api/profile/region` with `{"region": "GB"}`
3. User's currency changes to `GBP`
4. All accounts are updated to show currency in `£`
5. New transactions default to `GBP`

## Notes

- **Currency is per-user**: Each user has their own preferred currency
- **Account currency**: Each account inherits the user's currency
- **Transaction currency**: Transactions store currency at creation time (for historical accuracy)
- **Multi-currency transfers**: Currently not implemented (can be added later if needed)

## Future Enhancements

1. **Multi-currency accounts**: Allow a single user to hold multiple currencies
2. **Currency conversion**: Automatic conversion between currencies for transfers
3. **Regional formatting**: Display numbers/dates according to region standards
4. **Regional payment methods**: Show region-specific payment options
