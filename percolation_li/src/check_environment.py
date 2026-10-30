"""Verify the authors' exact Python/package pins plus this section's additions."""
import json
import platform
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

PART = Path(__file__).resolve().parents[1]


def read_requirements(path):
    raw = path.read_bytes()
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    pins = {}
    for line in raw.decode(encoding).splitlines():
        line = line.split('#',1)[0].strip()
        if not line or line.startswith('-r '):
            continue
        name, expected = line.split('==',1)
        pins[name] = expected
    return pins


def check_environment(save=False):
    expected = read_requirements(PART.parent/'requirements.txt')
    additions = read_requirements(PART/'requirements.txt')
    if set(expected) & set(additions):
        raise RuntimeError('Section requirements must not redefine original pins')
    expected.update(additions)
    packages = {}
    problems = []
    if platform.python_version() != '3.11.16':
        problems.append(f'Python: expected 3.11.16, found {platform.python_version()}')
    for name, pin in expected.items():
        try:
            actual = version(name)
        except PackageNotFoundError:
            actual = None
        packages[name] = {'expected':pin,'installed':actual,'matches':actual==pin}
        if actual != pin:
            problems.append(f'{name}: expected {pin}, found {actual}')
    report = {'python':platform.python_version(),'required_python':'3.11.16',
        'packages':packages,'passed':not problems,'problems':problems}
    if save:
        path = PART/'outputs/environment_check.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2)+'\n')
    if problems:
        raise RuntimeError('Use PC5253-KG and install percolation_li/requirements.txt:\n'+'\n'.join(problems))
    return report


if __name__=='__main__':
    print(json.dumps(check_environment(save=True),indent=2))
