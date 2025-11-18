from setuptools import setup, find_packages

setup(
    name="dash_schemas",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'fastapi',
        'pydantic',
        'fastapi_pagination',
    ],
)
