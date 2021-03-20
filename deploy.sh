#!/bin/bash
set -euxo pipefail
rm -f dist/*
pytest
bumpversion --verbose minor
python setup.py sdist
pip install twine
twine upload --config-file .pypirc-bot dist/*

