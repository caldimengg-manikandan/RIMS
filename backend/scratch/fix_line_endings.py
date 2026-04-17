"""
Fix the mangled interviews.py file:
1. Restore \r\r\n -> \r\n (fix the double-conversion damage)
2. Apply the end_interview patch correctly
"""

path = r'c:\Users\aashi\OneDrive\Desktop\Project\rims\backend\app\api\interviews.py'

# Read as raw bytes
with open(path, 'rb') as f:
    raw = f.read()

# Fix the mangled \r\r\n -> \r\n
fixed = raw.replace(b'\r\r\n', b'\r\n')

# Verify fix worked
assert b'\r\r\n' not in fixed, "Still has mangled line endings!"

# Write back
with open(path, 'wb') as f:
    f.write(fixed)

print(f"Fixed mangled line endings. New size: {len(fixed)} bytes")

# Now verify line count
lines = fixed.decode('utf-8').split('\r\n')
print(f"Line count: {len(lines)}")
