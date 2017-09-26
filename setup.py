# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='RainHue',
    version='0.2.0',
    description='Rain checker application',
    long_description=readme,
    author='Joakim Landegren',
    author_email='joakimlandegren@me.com',
    url='https://github.com/joakimlandegren/RainHue',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
