import glob, json, os
from datetime import datetime

files = sorted(glob.glob('evolution/mutations/mutation_*.json'), key=lambda f: os.path.getmtime(f), reverse=True)[:5]
print('RECENT MUTATION DETAILS:')
for f in files:
    m = json.load(open(f))
    name = os.path.basename(f)[:20]
    status = m.get('status', 'N/A')
    mtype = m.get('mutation_type', 'N/A')
    desc = str(m.get('description', ''))[:120]
    rationale = str(m.get('rationale', ''))[:120]
    changes = m.get('proposed_changes', {})
    print(f'--- {name} ---')
    print(f'  Status: {status}')
    print(f'  Type: {mtype}')
    print(f'  Desc: {desc}')
    print(f'  Rationale: {rationale}')
    if isinstance(changes, dict):
        if 'file_changes' in changes:
            for fc in changes['file_changes'][:2]:
                if isinstance(fc, dict):
                    print(f'  File: {fc.get("path")} ({fc.get("kind")})')
                    content = fc.get('content', '')
                    print(f'  Content preview: {str(content)[:100]}...')
        else:
            print(f'  Params: {changes}')
    print()
