#!/bin/bash
trap 'echo "ERROR: A command has failed. Exiting the script. Line was ($0:$LINENO): $(sed -n "${LINENO}p" "$0")"; exit 3' ERR
set -Eeuo pipefail

rm -f dist/*
python -m pytest
bumpversion --verbose minor
python setup.py sdist
pip install twine
#twine upload --config-file .pypirc-bot dist/*
twine upload dist/*
