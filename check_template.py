import re

def check_tags(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tag pattern that handles newlines inside tags
    tag_pattern = re.compile(r'{%\s*(?P<name>if|endif|elif|else|for|endfor|block|endblock|comment|endcomment|with|endwith|autoescape|endautoescape|spaceless|endspaceless|filter|endfilter|localize|endlocalize|cache|endcache).*?%}', re.DOTALL)
    
    stack = []
    matches = list(tag_pattern.finditer(content))
    
    print(f"Analyzing {filepath}...")
    for match in matches:
        tag_name = match.group('name')
        full_tag = match.group(0)
        start_index = match.start()
        line_no = content.count('\n', 0, start_index) + 1
        
        if tag_name in ['if', 'for', 'block', 'comment', 'with', 'autoescape', 'spaceless', 'filter', 'localize', 'cache']:
            stack.append((tag_name, line_no, full_tag))
            # print(f"Pushing {tag_name} at line {line_no}")
        elif tag_name.startswith('end'):
            expected = tag_name[3:]
            if not stack:
                print(f"ERROR: Found {full_tag} at line {line_no} but stack is empty!")
            else:
                last_tag, last_line, last_full = stack.pop()
                # print(f"Popping {last_tag} (was at {last_line}) with {tag_name} at {line_no}")
                if last_tag != expected:
                    print(f"ERROR: Mismatched tags! Found {full_tag} at line {line_no}, expected end{last_tag} (from line {last_line}: {last_full})")
    
    while stack:
        last_tag, last_line, last_full = stack.pop()
        print(f"ERROR: Unclosed tag! {last_full} at line {last_line} was never closed.")

if __name__ == "__main__":
    check_tags(r'D:\DISHA\learnbridge\templates\base.html')
