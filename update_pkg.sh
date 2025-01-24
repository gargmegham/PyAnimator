!#/bin/bash
pip3 uninstall pyanimator
rm -rf dist/
python3 setup.py sdist bdist_wheel
twine upload dist/*