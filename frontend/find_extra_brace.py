"""Show ALL brace events from line 1130 to 1150."""
import sys

def analyze_range(filename, start_line=1130, end_line=1150):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    depth = 0
    i = 0
    n = len(content)
    line_num = 1

    while i < n:
        c = content[i]
        if c == '\n':
            line_num += 1
            i += 1
            continue
        if c == '/' and i + 1 < n and content[i+1] == '/':
            while i < n and content[i] != '\n': i += 1
            continue
        if c == '/' and i + 1 < n and content[i+1] == '*':
            i += 2
            while i < n - 1:
                if content[i] == '*' and content[i+1] == '/': i += 2; break
                if content[i] == '\n': line_num += 1
                i += 1
            continue
        if c in ('"', "'"):
            quote = c; i += 1
            while i < n:
                ch = content[i]
                if ch == '\n': line_num += 1
                if ch == '\\': i += 2; continue
                if ch == quote: i += 1; break
                i += 1
            continue
        if c == '`':
            i += 1
            while i < n:
                ch = content[i]
                if ch == '\n': line_num += 1
                if ch == '\\': i += 2; continue
                if ch == '`': i += 1; break
                i += 1
            continue

        if c == '{':
            depth += 1
            if start_line <= line_num <= end_line:
                # Get surrounding context
                j = i
                while j > 0 and content[j] != '\n': j -= 1
                line_text = content[j+1:i+20].strip()[:60]
                print(f"  Line {line_num}: {{ -> depth={depth}  [{line_text}]")
        elif c == '}':
            if start_line <= line_num <= end_line:
                j = i
                while j > 0 and content[j] != '\n': j -= 1
                line_text = content[j+1:i+20].strip()[:60]
                print(f"  Line {line_num}: }} -> depth={depth-1}  [{line_text}]")
            depth -= 1
        i += 1

    print(f"\nFinal depth: {depth}")

if __name__ == "__main__":
    analyze_range(sys.argv[1])
