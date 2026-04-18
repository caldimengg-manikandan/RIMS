import sys

def check_braces(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    count = 0
    lines = content.split('\n')
    for i, line in enumerate(lines):
        for char in line:
            if char == '{':
                count += 1
            elif char == '}':
                count -= 1
        
        if count == 0:
            print(f"Pre-close candidate at line {i+1}")
        if count < 0:
            print(f"ERROR: Unbalanced at line {i+1}: {line}")
            return
    
    print(f"Final count: {count}")
    if count != 0:
        print("ERROR: File ends with unbalanced braces!")

if __name__ == "__main__":
    check_braces(sys.argv[1])
