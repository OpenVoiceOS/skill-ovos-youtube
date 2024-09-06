"""
on merge to master -> declare stable (remove alpha)
"""
import argparse
import fileinput
import sys
from os.path import abspath, join, dirname


def update_alpha(version_file):
    alpha_var_name = "VERSION_ALPHA"

    for line in fileinput.input(version_file, inplace=True):
        if line.startswith(alpha_var_name):
            print(f"{alpha_var_name} = 0")
        else:
            print(line.rstrip('\n'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Update the version based on the specified part (major, minor, build, alpha)')
    parser.add_argument('--version-file', help='Path to the version.py file', required=True)

    args = parser.parse_args()

    update_alpha(abspath(args.version_file))
