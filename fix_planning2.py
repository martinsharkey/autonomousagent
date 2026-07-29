import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('core/planning.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

start = None
end = None
for i, line in enumerate(lines):
    if '_reasoning, action_text = extract_react_parts(content)' in line:
        start = i
    if start is not None and 'plan = json.loads(action_text)' in line:
        end = i + 1
        break

if start is not None and end is not None:
    replacement = [
        '            _reasoning, action_text = extract_react_parts(content)\n',
        '\n',
        '            action_text = action_text.strip()\n',
        '\n',
        '            if not action_text:\n',
        '\n',
        '                return {\n',
        '\n',
        '                    "goal": goal,\n',
        '\n',
        '                    "error": "Failed to create plan: empty LLM response",\n',
        '\n',
        '                    "status": "failed"\n',
        '\n',
        '                }\n',
        '\n',
        '            try:\n',
        '\n',
        '                plan = json.loads(action_text)\n',
        '\n',
        '            except Exception as e:\n',
        '\n',
        '                return {\n',
        '\n',
        '                    "goal": goal,\n',
        '\n',
        '                    "error": f"Failed to create plan: {str(e)}",\n',
        '\n',
        '                    "status": "failed"\n',
        '\n',
        '                }\n',
        '\n',
    ]
    new_lines = lines[:start] + replacement + lines[end:]
    with open('core/planning.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('REPLACED planning block')
else:
    print(f'Could not find block: start={start}, end={end}')
