@echo off
del /Q dist\*
python -m build
python -m twine upload dist/*