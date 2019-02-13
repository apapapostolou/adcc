#!/usr/bin/env python3
## vi: tabstop=4 shiftwidth=4 softtabstop=4 expandtab
## ---------------------------------------------------------------------
##
## Copyright (C) 2019 by the adcc authors
##
## This file is part of adcc.
##
## adcc is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published
## by the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## adcc is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with adcc. If not, see <http://www.gnu.org/licenses/>.
##
## ---------------------------------------------------------------------

"""Setup for look4bas"""

from os.path import join
from setuptools.command.build_ext import build_ext
from setuptools import setup, Extension, find_packages
import glob
import json
import os
import setuptools
import sys


# Version of the python bindings and adcc python package.
__version__ = '0.6.0'


#
# Find AdcCore
#
def path_adccore_config():
    """
    Determine the path to the adccore config file.
    Return None if no config is found
    """
    this_dir = os.path.dirname(__file__)
    cfg = join(this_dir, "extension", "adccore", "adccore_config.json")
    return cfg


def adccore_config():
    cfg = path_adccore_config()
    if not os.path.isfile(cfg):
        # TODO Later one could do something more clever like downloading
        #      the binary tarball or automatic checkout / compilation of adccore
        raise RuntimeError(
            "Did not find adccore_config.json file in the directory tree. " +
            "Did you download or install adccore properly? See the adcc " +
            "documentation for help."
        )

    with open(cfg, "r") as fp:
        adccore = json.load(fp)
    adccore["prefix"] = os.path.dirname(cfg)
    return adccore


#
# Pybind11 BuildExt
#
class GetPyBindInclude:
    """Helper class to determine the pybind11 include path

    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
        f.write('int main (int argc, char **argv) { return 0; }')
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14] compiler flag.

    The c++14 is prefered over c++11 (when it is available).
    """
    if has_flag(compiler, '-std=c++14'):
        return '-std=c++14'
    elif has_flag(compiler, '-std=c++11'):
        return '-std=c++11'
    else:
        raise RuntimeError('Unsupported compiler -- at least C++11 support '
                           'is needed!')


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""
    def build_extensions(self):
        opts = []
        if sys.platform == "darwin":
            opts += ['-stdlib=libc++', '-mmacosx-version-min=10.7']
        if self.compiler.compiler_type == 'unix':
            opts.append(cpp_flag(self.compiler))
            potential_opts = [
                "-fvisibility=hidden", "-Werror", "-Wall", "-Wextra",
                "-pedantic", "-Wnon-virtual-dtor", "-Woverloaded-virtual",
                "-Wcast-align", "-Wconversion", "-Wsign-conversion",
                "-Wmisleading-indentation", "-Wduplicated-cond",
                "-Wduplicated-branches", "-Wlogical-op",
                "-Wdouble-promotion", "-Wformat=2",
                "-Wno-error=deprecated-declarations",
            ]
            opts.extend([opt for opt in potential_opts
                         if has_flag(self.compiler, opt)])

        for ext in self.extensions:
            ext.extra_compile_args = opts
        build_ext.build_extensions(self)


#
# Main setup code
#
adccore = adccore_config()
if adccore["version"] != __version__:
    raise RuntimeError(
        "Version mismatch between adcc (== {}) and adccore (== {})"
        "".format(__version__, adccore["version"])
    )

# Setup RPATH on Linux and MacOS
if sys.platform == "darwin":
    extra_link_args = ["$ORIGIN", "$ORIGIN/adcc/lib"]
    runtime_library_dirs = []
elif sys.platform == "linux":
    extra_link_args = []
    runtime_library_dirs = ["$ORIGIN", "$ORIGIN/adcc/lib"]
else:
    raise OSError("Unsupported platform: {}".format(sys.platform))

# Setup build of the libadcc extension
ext_modules = [
    Extension(
        'libadcc', glob.glob("extension/*.cc"),
        include_dirs=[
            # Path to pybind11 headers
            GetPyBindInclude(),
            GetPyBindInclude(user=True),
            join(adccore["prefix"], "include")
        ],
        libraries=adccore["libraries"],
        library_dirs=[join(adccore["prefix"], "lib")],
        extra_link_args=extra_link_args,
        runtime_library_dirs=runtime_library_dirs,
        language='c++',
    ),
]

setup(
    name='adcc',
    description='A python-based framework for running ADC calculations',
    long_description='',
    #
    url='https://github.com/mfherbst/adcc',
    author='adcc developers',
    author_email='adcc+developers@michael-herbst.com',
    maintainer='Michael F. Herbst',
    maintainer_email='info@michael-herbst.com',
    license="LGPL v3",
    #
    version=__version__,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: '
        'GNU Lesser General Public License v3 (LGPLv3)',
        'Intended Audience :: Science/Research',
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Education",
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Operating System :: Unix',
    ],
    #
    packages=find_packages(exclude=["*.test*", "test"]),
    package_data={'adcc': ["lib/*.so.*", "lib/*.dylib.*"]},
    ext_modules=ext_modules,
    cmdclass={'build_ext': BuildExt},
    zip_safe=False,
    #
    platforms=["Linux", "Mac OS-X", "Unix"],
    python_requires='>=3.5',
    install_requires=[
        'pybind11 (>= 2.2)',
        'numpy',
        'scipy',
    ],
    tests_require=["pytest", "h5py"],
    setup_requires=["pytest-runner"],
    #
    # TODO Proper unit test setup
    # TODO Download unit test data
)
