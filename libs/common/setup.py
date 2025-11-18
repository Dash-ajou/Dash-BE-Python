from setuptools import setup, find_packages

setup(
    name="dash_common",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'redis'
    ],
)