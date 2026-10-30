"""Check the shared project environment, including notebook dependencies."""
import argparse
import json
import platform
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_requirements(path):
    path = Path(path)
    raw = path.read_bytes()
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    pins = {}
    for line in raw.decode(encoding).splitlines():
        line = line.split('#',1)[0].strip()
        if not line:
            continue
        if line.startswith('-r '):
            entries = read_requirements(path.parent/line[3:].strip())
        else:
            name,expected = line.split('==',1)
            entries = {name:expected}
        for name,expected in entries.items():
            if name in pins and pins[name]!=expected:
                raise ValueError(f'Conflicting requirement: {name}')
            pins[name] = expected
    return pins


def check_environment():
    filename = 'requirements.txt'
    expected = read_requirements(ROOT/filename)
    packages,problems = {},[]
    if platform.python_version()!='3.11.16':
        problems.append(f'Python: expected 3.11.16, found {platform.python_version()}')
    for name,pin in expected.items():
        try:
            actual = version(name)
        except PackageNotFoundError:
            actual = None
        packages[name] = {'expected':pin,'installed':actual,'matches':actual==pin}
        if actual!=pin:
            problems.append(f'{name}: expected {pin}, found {actual}')
    if problems:
        raise RuntimeError(f'Activate PC5253-KG (Python 3.11.16), then python -m pip install -r {filename}:\n'+'\n'.join(problems))
    return {'python':platform.python_version(),'required_python':'3.11.16',
            'requirements':filename,'packages':packages,'passed':True,'problems':[]}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    print(json.dumps(check_environment(),indent=2))
