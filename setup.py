#!/usr/bin/env python
"""
Setup script
"""

import os
import re

from distutils.core import setup


scriptfile = os.path.join(os.path.dirname(__file__), "tbs.py")

# Thanks to SQLAlchemy:
# https://github.com/zzzeek/sqlalchemy/blob/master/setup.py#L104
with open(scriptfile) as stream:
    __version__ = (
        re.compile(r".*__version__ = \"(.*?)\"", re.S)
        .match(stream.read())
        .group(1)
    )


setup(
    name = 'tbs',
    description = 'TBS dashboard',
    description_long = '',
    version = __version__,
    author = 'Mohan Boddu, Tomas Hrcka',
    author_email = 'pllm@plllm.pllm',
    maintainer = '',
    maintainer_email = 'pllm@plllm.pllm',
    license = 'GPLv2+',
    download_url = '',
    url = '',
    scripts=['tbs.py'],
    )
