#! /usr/bin/env python
# -*- coding: utf8 -*-

import sys
import os

# space separated list of hosts
#remote_hosts = "localhost node-1:2 node-3:4"
remote_hosts = "localhost"

test_dir = os.path.dirname(os.path.realpath(__file__))

start_script = sys.executable + " " + test_dir + os.sep + \
    "t_distributed_python_wrapper.py"

test_type = "local"
if len(sys.argv) >= 3:
    test_type = sys.argv[2]

if test_type == "local":
    default_param = " --test local "
elif test_type == "remote":
    default_param = " --test remote --hosts " + remote_hosts + " "
else:
    print ('Wrong arguments!')
    exit(1)

os.system(start_script + default_param + " --point ")
os.system(start_script + default_param + " --analytical ")
os.system(start_script + default_param + " --point --analytical ")

os.system(start_script + default_param +
          "--sample-size 50 --work-time 0.1 ")

os.system(start_script + default_param +
          "--sample-size 10 --nb-output 1000 ")

os.system(start_script + default_param +
          "--sample-size 1 ")

os.system(start_script + default_param +
          "--sample-size 5 --work-time 0.1 --cleanup no ")
os.system(start_script + default_param +
          "--sample-size 1 --cleanup no ")

os.system(start_script + default_param +
          "--sample-size 5 --work-time 0.1 --cleanup all ")
os.system(start_script + default_param +
          "--sample-size 1 --cleanup all ")

os.system(start_script + default_param +
          " --sample-size 10 --work-time 0.1 --error ")
os.system(start_script + default_param +
          " --sample-size 4 --work-time 0.1 --error --cleanup no")
os.system(start_script + default_param +
          " --sample-size 4 --work-time 0.1 --error --cleanup all")
