# Copyright 2021-2025 Nokia

from setuptools import setup
from pysros import __version__

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='pysros',
    version=__version__,
    packages=['pysros'],
    url='https://www.nokia.com',
    license='Copyright 2021-2025 Nokia.  License available in the LICENSE.md file.',
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
        "lxml~=5.3.0",
    ],
    python_requires=">=3.10",
    long_description=long_description,
    long_description_content_type="text/markdown",
)

