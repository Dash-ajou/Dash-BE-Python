from setuptools import setup, find_packages

setup(
    name="dash_common",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'redis',
        'PyJWT>=2.8.0',  # JWT 토큰 검증을 위한 의존성
    ],
)