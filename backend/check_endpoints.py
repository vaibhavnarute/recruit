"""
Quick test to verify Flask endpoints are registered
"""

import sys
sys.path.insert(0, '.')

from app import app

# Get all registered routes
routes = []
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        routes.append({
            'endpoint': rule.rule,
            'methods': ','.join(rule.methods - {'HEAD', 'OPTIONS'})
        })

# Sort by endpoint
routes.sort(key=lambda x: x['endpoint'])

print("\n" + "="*80)
print("🔍 Registered Flask Endpoints")
print("="*80)

# Check for prediction endpoints
prediction_endpoints = []
for route in routes:
    print(f"{route['methods']:15} {route['endpoint']}")
    if 'predict' in route['endpoint']:
        prediction_endpoints.append(route['endpoint'])

print("="*80)

# Verify prediction endpoints exist
print("\n✅ Checking ML Prediction Endpoints:")
print("-"*80)

expected = ['/api/predict-salary', '/api/predict-job-possibility']
for endpoint in expected:
    if endpoint in prediction_endpoints:
        print(f"✅ {endpoint:40} FOUND")
    else:
        print(f"❌ {endpoint:40} NOT FOUND")

if len(prediction_endpoints) == 2:
    print("\n🎉 SUCCESS: Both ML prediction endpoints are registered!")
else:
    print(f"\n⚠️  WARNING: Expected 2 endpoints, found {len(prediction_endpoints)}")

print("="*80)
