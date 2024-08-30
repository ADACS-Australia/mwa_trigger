#! /usr/bin/env python
"""Setup for tracet
"""
from setuptools import find_packages, setup

with open("app/README.md", "r") as f:
    long_description = f.read()

setup(
    name="proposalsettings",
    version="0.1.0",
    description="VOEvent handling daemon and library for gen",
    package_dir={"": "app"},
    packages=find_packages(where="app"),
    long_description=long_description,
    url="https://github.com/ADACS-Australia/proposal_factory.git",
    # long_description=read('README.md'),
    python_requires=">=3.10",
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
)
