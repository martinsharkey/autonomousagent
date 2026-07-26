import json
from pathlib import Path

files = sorted(Path('evolution/mutations').glob('mutation_*.json'), key=lambda f: f.stat().st_mtime, reverse=True)
for f in files[:10]:
    with open(f) as fh:
        m = json.load(fh)
    mid = m['mutation_id'][:12]
    status = m['status']
    mtype = m['mutation_type']
    agent = m['agent_name']
    risk = m['risk_level']
    print(f'{mid}... status={status} type={mtype} agent={agent} risk={risk}')
    impl = m.get('implementation_result')
    if impl:
        promo = impl.get('promotion', '?')
        eval_score = impl.get('evaluation', {}).get('score', '?')
        print(f'  -> promotion={promo} score={eval_score}')
    print()