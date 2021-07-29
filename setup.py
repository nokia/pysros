# Copyright 2021 Nokia

from setuptools import setup

setup(
    name='pysros',
    version='21.7.1rc1',
    packages=['pysros'],
    url='https://www.nokia.com',
    license='Copyright 2021 Nokia.  License available in the LICENSE.md file.',
    author='Nokia',
    author_email='',
    description='Python for the Nokia Service Router Operating Systems (pySROS)',
    project_urls={
        "Documentation": "https://network.developer.nokia.com/static/sr/learn/pysros",
    },
    classifiers=[
        "License :: Other/Proprietary License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Topic :: Internet",
        "Development Status :: 4 - Beta",
    ],
    install_requires=[
        "ncclient~=0.6.12",
        "lxml~=4.6.1",
    ],
    python_requires=">=3.6",
)
