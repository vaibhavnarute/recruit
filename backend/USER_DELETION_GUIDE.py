"""
USER DELETION WITH FIREBASE AUTH CLEANUP
========================================

This feature automatically deletes users from both MongoDB and Firebase Authentication
when a user is removed from the database.

## How It Works

1. **Delete Request**: When you delete a user from MongoDB
2. **Retrieve Firebase UID**: System retrieves the user's Firebase UID
3. **MongoDB Deletion**: User is deleted from MongoDB
4. **Firebase Cleanup**: System automatically deletes the same user from Firebase Auth
5. **Status Report**: Returns detailed status of both deletions

## Benefits

✅ No orphaned Firebase Auth accounts
✅ Fresh testing with same email addresses
✅ Automatic cleanup - no manual Firebase Console visits
✅ Consistent user data across both systems
✅ Detailed deletion status reporting

## API Endpoints

### Delete User by ID
DELETE /api/auth/user/<user_id>

Response:
{
    "success": true,
    "message": "User deleted from MongoDB and Firebase Auth",
    "mongodb_deleted": true,
    "firebase_deleted": true,
    "firebase_message": "Deleted from Firebase Auth",
    "firebase_uid": "firebase-abc123"
}

### Delete User by Email
DELETE /api/auth/user/email/<email>

Response:
{
    "success": true,
    "message": "User user@example.com deleted from MongoDB and Firebase Auth",
    "mongodb_deleted": true,
    "firebase_deleted": true,
    "firebase_message": "Deleted from Firebase Auth",
    "firebase_uid": "firebase-abc123"
}

## Setup (Optional - For Full Firebase Cleanup)

By default, the system will delete users from MongoDB. To enable automatic Firebase Auth
deletion, you need to configure Firebase Admin SDK:

### Step 1: Install Firebase Admin SDK
```bash
pip install firebase-admin
```

### Step 2: Get Service Account Key

1. Go to Firebase Console: https://console.firebase.google.com/
2. Select your project: resumate-a897e
3. Click the gear icon (⚙️) → Project settings
4. Go to "Service accounts" tab
5. Click "Generate new private key"
6. Save the JSON file (e.g., `firebase-service-account.json`)
7. Move it to your backend folder

### Step 3: Configure Environment Variable

Add to backend/.env:
```
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json
```

### Step 4: Restart Backend
```bash
cd backend
python app.py
```

Now user deletions will automatically clean up Firebase Auth!

## Usage Examples

### Python (Backend)
```python
from services.firebase_auth_service import FirebaseAuthService

service = FirebaseAuthService()

# Delete by user ID
result = service.delete_user("507f1f77bcf86cd799439011")
print(result)
# {
#     'success': True,
#     'mongodb_deleted': True,
#     'firebase_deleted': True,
#     'message': 'User deleted from MongoDB and Firebase Auth'
# }

# Delete by email
result = service.delete_user_by_email("user@example.com")
print(result)
```

### cURL (API)
```bash
# Delete by user ID
curl -X DELETE http://localhost:5000/api/auth/user/507f1f77bcf86cd799439011

# Delete by email
curl -X DELETE http://localhost:5000/api/auth/user/email/user@example.com
```

### JavaScript (Frontend)
```javascript
// Delete user by ID
const deleteUser = async (userId) => {
  const response = await fetch(`http://localhost:5000/api/auth/user/${userId}`, {
    method: 'DELETE'
  });
  const result = await response.json();
  console.log(result);
};

// Delete user by email
const deleteUserByEmail = async (email) => {
  const response = await fetch(
    `http://localhost:5000/api/auth/user/email/${encodeURIComponent(email)}`, 
    { method: 'DELETE' }
  );
  const result = await response.json();
  console.log(result);
};
```

## Testing

Run the test script:
```bash
cd backend
python test_user_deletion.py
```

This will:
1. Create test users
2. Delete them from MongoDB
3. Attempt Firebase Auth cleanup
4. Show detailed results

## Without Firebase Admin SDK

If Firebase Admin SDK is not configured, the system will:
- ✅ Still delete users from MongoDB
- ⚠️ Skip Firebase Auth deletion
- 📝 Report: "Firebase Admin SDK not available"

You can still manually delete from Firebase Console if needed.

## Error Handling

### User Not Found
```json
{
    "success": false,
    "message": "User not found in MongoDB",
    "mongodb_deleted": false,
    "firebase_deleted": false
}
```

### MongoDB Deleted, Firebase Failed
```json
{
    "success": true,
    "message": "User deleted from MongoDB",
    "mongodb_deleted": true,
    "firebase_deleted": false,
    "firebase_message": "Firebase deletion failed: User not found"
}
```

### Full Success
```json
{
    "success": true,
    "message": "User deleted from MongoDB and Firebase Auth",
    "mongodb_deleted": true,
    "firebase_deleted": true,
    "firebase_message": "Deleted from Firebase Auth",
    "firebase_uid": "abc123"
}
```

## Security Notes

1. **Service Account Security**: Keep your Firebase service account JSON file secure
   - Don't commit it to Git (add to .gitignore)
   - Use environment variables for the path
   - Restrict file permissions (read-only for app user)

2. **API Authentication**: In production, protect delete endpoints with:
   - User authentication
   - Admin role verification
   - Rate limiting

3. **Audit Trail**: Consider logging all user deletions for compliance

## Troubleshooting

### Firebase Admin SDK Not Initializing
- Check FIREBASE_SERVICE_ACCOUNT_PATH is correct
- Verify JSON file exists and is readable
- Ensure firebase-admin is installed

### Firebase Deletion Fails
- Verify service account has correct permissions
- Check Firebase UID exists in Firebase Auth
- User may already be deleted from Firebase

### MongoDB Deletion Fails
- Check user_id format (must be valid ObjectId)
- Verify MongoDB connection is active
- Check user exists in database

## Benefits for Testing

With this feature, you can:
- Delete test users completely
- Re-register with same email addresses
- No "email already in use" errors
- Clean slate for each test run
- No need to manually clean Firebase Console

Perfect for development and testing! 🎉
"""

print(__doc__)
