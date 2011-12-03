# Copyright (c) 2002-2011 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from setuptools import setup, find_packages
import os

version = '1.0dev'


setup(name='zhit.zope2start',
      version=version,
      description="Simple script to start a zope 2 instance",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Framework :: Zope2",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='start zope2',
      author='Sylvain Viollon',
      author_email='thefunny@gmail.com',
      url='https://github.com/thefunny42/Zhit-Zope2Start',
      license='BSD',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      namespace_packages=['zhit',],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'setuptools',
        ],
      entry_points = """
      [console_scripts]
      zope = zhit.zope2start.ctl:main
      """,
      )
