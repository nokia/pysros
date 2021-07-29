# Python 3 for Nokia Service Router Operating System (pySROS) #

## Overview ##

The pySROS libraries provide a model-driven management interface for
Python developers to integrate with supported Nokia routers
running the Service Router Operating System (SR OS).

The libraries provide an Application Programming Interface (API) for developers
to create applications that can interact with Nokia SR OS devices, whether those
applications are executed from a development machine or directly on the router.

When a developer uses only libraries and constructs supported on SR OS, a
single application may be executed from a development machine or ported
directly to an SR OS node where the application is executed.

## Pre-requisites ##

In order to use the pySROS library the following pre-requisites must be met:

- One or more SR OS node
    - Running in model-driven mode
    - Running SR OS 21.7.R1 or greater (to execute applications on the SR OS device)
    - With NETCONF enabled and accessible by an authorized user (to execute applications
    remotely)
- A Python 3 interpreter of version 3.6 or newer when using the pySROS library to
  execute applications remotely

## License ##

Copyright 2021 Nokia.

The license is located [here](LICENSE.md).

*Please read this license carefully before downloading, installing, or using the software. 
By downloading, installing, or otherwise using the software, you are agreeing that you have read this license, 
understand it, and agree (individually, or, if employed, on behalf of the entity which employs you) to be bound 
by its terms and conditions. If you do not agree to all of the terms and conditions of this license or, if the 
license is to be used by or on behalf of an entity and you are not authorized by the entity, then do not 
install or use the software.*

## Installation ##

Multiple installation methods are available:

* [PyPi](#pypi)
* [Nokia support portal](#nokia-support-portal)
* [GitHub](#github)

Note: It is recommended to use Python virtual environments where appropriate.

### PyPi ###

The preferred method of installation of the pySROS libraries is to install
directly from the Python Package index (PyPi) using the ``pip`` tool.

The pySROS project is [located on PyPi.org](https://pypi.org/project/pysros).

The libraries can be downloaded and installed by using the following:

```
pip install pysros
```

### Nokia support portal ###


The pySROS libraries are available for [download from the portal](https://customer.nokia.com/support) for registered
customers.

The obtained file can be unzipped and subsequently installed using:

```
python3 setup.py install
```



### GitHub ###


The pySROS libraries are available for
[download from GitHub](https://github.com/jgcumming/pysros-examples).

The obtained file can be installed using:

```
git clone https://github.com/nokia/pysros
python3 setup.py install
```

## Documentation and examples ##

Guidance documentation is available in the SR OS System Management Guide.

API documentation is provided in this repository and may be compiled from source
using:

```shell
cd docs
pip3 install -r requirements.txt
make html
```

The built documentation will be available in the docs/build/html directory.

Alternative formats may be selected after the ``make`` command instead of the ``html`` attribute.  Some of
these include:

- singlehtml
- man
- text
