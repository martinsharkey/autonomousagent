import glob, json, os

files = sorted(glob.glob('evolution/mutations/mutation_*.json'), key=lambda f: os.path.getmtime(f), reverse=True)[:3]
for f in files:
    print(os.path.basename(f))
