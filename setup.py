# Copyright 2021 Nokia

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='pysros',
    version='21.10.9',
    packages=['pysros'],
    url='https://www.nokia.com',
    license='Copyright 2021 Nokia.  License available in the LICENSE.md file.',
    author='Nokia',
    author_email='',
    description='Python for the Nokia Service Router Operating Systems (pySROS)',
    project_urls={
        "Documentation": "https://network.developer.nokia.com/static/sr/learn/pysros/latest/",
        "Source": "https://github.com/nokia/pysros",
    },
    classifiers=[
        "License :: Other/Proprietary License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Topic :: Internet",
        "Development Status :: 5 - Production/Stable",
    ],
    install_requires=[
        "ncclient~=0.6.12",
        "lxml~=4.6.3",
    ],
    python_requires=">=3.6",
    long_description=long_description,
    long_description_content_type="text/markdown",
)

