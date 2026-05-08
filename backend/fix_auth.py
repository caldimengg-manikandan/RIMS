import sys

path = r'c:\Users\user\Desktop\RIMS\rims\backend\app\core\auth.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'if exp_at.tzinfo is None:' in line:
        continue
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Cleaned up auth.py successfully')
