"""
on merge to dev:
- depending on labels (conventional commits) script is called with "major", "minor", "build", "alpha"
- on merge to dev, update version.py string to enforce semver
"""

import sys
import argparse
from os.path import abspath

def read_version(version_file):
    VERSION_MAJOR = 0
    VERSION_MINOR = 0
    VERSION_BUILD = 0
    VERSION_ALPHA = 0

    with open(version_file, 'r') as file:
        content = file.read()
    for l in content.split("\n"):
        l = l.strip()
        if l.startswith("VERSION_MAJOR"):
            VERSION_MAJOR = int(l.split("=")[-1])
        elif l.startswith("VERSION_MINOR"):
            VERSION_MINOR = int(l.split("=")[-1])
        elif l.startswith("VERSION_BUILD"):
            VERSION_BUILD = int(l.split("=")[-1])
        elif l.startswith("VERSION_ALPHA"):
            VERSION_ALPHA = int(l.split("=")[-1])
    return VERSION_MAJOR, VERSION_MINOR, VERSION_BUILD, VERSION_ALPHA


def update_version(part, version_file):
    VERSION_MAJOR, VERSION_MINOR, VERSION_BUILD, VERSION_ALPHA = read_version(version_file)

    if part == 'major':
        VERSION_MAJOR += 1
        VERSION_MINOR = 0
        VERSION_BUILD = 0
        VERSION_ALPHA = 1
    elif part == 'minor':
        VERSION_MINOR += 1
        VERSION_BUILD = 0
        VERSION_ALPHA = 1
    elif part == 'build':
        VERSION_BUILD += 1
        VERSION_ALPHA = 1
    elif part == 'alpha':
        VERSION_ALPHA += 1

    with open(version_file, 'w') as file:
        file.write(f"""# START_VERSION_BLOCK
VERSION_MAJOR = {VERSION_MAJOR}
VERSION_MINOR = {VERSION_MINOR}
VERSION_BUILD = {VERSION_BUILD}
VERSION_ALPHA = {VERSION_ALPHA}
# END_VERSION_BLOCK""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update the version based on the specified part (major, minor, build, alpha)')
    parser.add_argument('part', help='Part of the version to update (major, minor, build, alpha)')
    parser.add_argument('--version-file', help='Path to the version.py file', required=True)

    args = parser.parse_args()

    update_version(args.part, abspath(args.version_file))
