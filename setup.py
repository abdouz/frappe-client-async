from setuptools import setup

version = '0.1.0dev'

with open('requirements.txt') as requirements:
    install_requires = requirements.read().split()

setup(
    name='frappeclientasync',
    version=version,
    author='Abdullah Abouzekry',
    author_email='abouzekry@gmail.com',
    packages=[
        'frappeclientasync'
    ],
    install_requires=install_requires,
    tests_requires=[
        'httmock<=1.2.2',
        'nose<=1.3.4'
    ],
)
