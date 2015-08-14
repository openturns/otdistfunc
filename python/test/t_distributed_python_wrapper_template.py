#! /usr/bin/env python
# -*- coding: utf8 -*-

# test that the python template is fine

import sys
import os

if len(sys.argv) == 1:
    template_dir = 'wrapper_python_distributed'
else:
    template_dir = sys.argv[1]
if 'win' in sys.platform:
    os.environ['PATH'] += ';' + os.getcwd()
os.chdir(template_dir)
start_script = sys.executable + ' ot_script.py'
os.system(start_script)
