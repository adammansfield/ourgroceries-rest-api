#!/usr/bin/env python3

import os
import pathlib
import re
import subprocess
import sys
from typing import List

def main():
    os.chdir(str(get_toplevel_dir()))

    check_unstaged_changes()

    files = get_tracked_files()
    check_go_source(files)

    make('build')
    make('test')
    make('test-large')

def check_go_source(files: List[pathlib.Path]):
    go_files = [f for f in files if f.match('*.go')]
    if not go_files:
        return

    check_gofmt(go_files)
    check_golint('./...')
    # TODO: change govet path to ./... when openapi-generator is removed
    check_govet('./internal/go/...')

def check_gofmt(go_files: List[pathlib.Path]):
    unformatted_files = gofmt(go_files)
    if unformatted_files:
        print("  Go files must be formatted with gofmt. Please run:")
        for unformatted_file in unformatted_files:
            print("    gofmt -s -w {}".format(unformatted_file))
        sys.exit(1)

def check_golint(go_files: str):
    warnings = golint(go_files)

    # TODO: remove filter when openapi-generator is removed
    def ignore(w):
        for p in ['logger\.go', 'model_.+\.go', 'routers\.go']:
            if re.search(p, w):
                return True
        return False

    warnings = [w for w in warnings if not ignore(w)]
    if warnings:
        print("  Go files must pass golint. Please fix:")
        for warning in warnings:
            print("    {}".format(warning))
        sys.exit(1)

def check_govet(package: str):
    warnings = govet(package)
    if warnings:
        print("  Go files must pass go vet. Please fix:")
        for warning in warnings:
            print("    {}".format(warning))
        sys.exit(1)

def check_unstaged_changes():
    unstaged_changes = get_unstaged_changes()
    if unstaged_changes:
        print("Cannot push with unstaged changes:")
        for unstaged_change in unstaged_changes:
            print("  {}".format(unstaged_change))
        print("Please run either:")
        print("  git add -A && git commit")
        print("  git stash -k -u")
        sys.exit(1)

def get_tracked_files() -> List[pathlib.Path]:
    result = subprocess.run(
            ['git', 'ls-tree', '-r', 'HEAD', '--name-only'],
            check=True,
            stdout=subprocess.PIPE)
    files = result.stdout.decode('utf-8').rstrip('\n').splitlines()
    return [pathlib.Path(f) for f in files]

def get_toplevel_dir() -> pathlib.Path:
    result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            check=True,
            stdout=subprocess.PIPE)
    return pathlib.Path(result.stdout.decode('utf-8').rstrip('\n'))

def get_unstaged_changes() -> List[str]:
    result = subprocess.run(
            ['git', 'status', '--porcelain'],
            check=True,
            stdout=subprocess.PIPE)
    statuses = result.stdout.decode('utf-8').rstrip('\n')
    matches = re.findall(r"^((.D|.M|\?\?).+)$", statuses, re.MULTILINE)
    return [m[0] for m in matches]

def gofmt(files: List[pathlib.Path]) -> List[str]:
    print("gofmt")
    files_arg = [str(f) for f in files]
    result = subprocess.run(
            ['gofmt', '-l', '-s'] + files_arg,
            check=True,
            stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8').rstrip('\n').splitlines()

def golint(files: str) -> List[str]:
    print("golint")
    result = subprocess.run(
            ['golint', files],
            check=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8').rstrip('\n').splitlines()

def govet(package: str) -> List[str]:
    print("go vet")
    result = subprocess.run(
            ['go', 'vet', package],
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8').rstrip('\n').rstrip("exit status 1").splitlines()

def make(command: str):
    print("make {}".format(command))
    result = subprocess.run(
            ['make', command],
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE)
    if result.returncode != 0:
        print("make {} failed:".format(command))
        print(result.stdout.decode('utf-8').rstrip('\n'))
        sys.exit(1)

main()
