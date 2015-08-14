# -*- coding: utf-8 -*-
#                                               -*- Python -*-
#
# @file  distributed_wrapper.py
# @brief Permit to launch _exec func of OpenTURNSPythonFunction to several
#    nodes and cores in parallel.
#
# Copyright (C) 2005-2013 EDF-EADS-Phimeca
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
#
# @author souchaud
# @date   2012-08-28
#

"""
Permit to launch _exec func of OpenTURNSPythonFunction to several nodes and
cores in parallel.
Compatible with OpenTURNS >= 0.14 (needs _exec_sample) .
"""

import openturns as ot

# these imports cannot be absolute
import sys
sys.path.append(ot.__path__[0])
from otdistfunc import host_dispatcher
from otdistfunc import wrapper_data

import traceback
import signal
import os
import random
import time
import threading
import string


# __new__ permit to create automatically the NumericalMathFunction
class DistributedPythonFunction(ot.NumericalMathFunction):

    """
    DistributedPythonFunction allows to build an OpenTURNS function and
    distribute it to several nodes and cores.
    The python function must be implemented in a separate file.
    -----

    n_input:
    n_output:      input and output dimension implemented by the function
                   _exec() of the wrapper_file
    wrapper_file:  a file that must have a function named _exec(point)

    hosts:         host on which to send computing. I.e.: 
                   ['node-1', 'node-3', 'node-4']: in this case, every 
                   nodes compute the same amount of points.

                   ['node-1', 'node-3:2', 'node-4:4']: node-3 will compute
                   twice more points than node-1 (weight of 1 by default)
                   and node-4 will compute 2 times more points than node-3.

    scheduler:     scheduler name (i.e. \"PBS\") in order to retrieve the
                   host reserved. Override hosts parameter.
                   Note: the submission (qsub ...) must have been already
                   done.
                   If neither 'hosts' nor 'scheduler' params are filled,
                   computation will be launched on localhost.

    analytical:    True: each thread share the same workdir, useful only for
                   analytical formula (n_cores is then set to 1).
                   False (default): each thread has its own working
                   directory.

    n_cores:       nb of core per host to use. 0 set the number of local
                   (or remote) cores available.
    files_to_send: list of files to send into each workdirs
    cleanup:       determine how to cleanup workdirs
                   "no", no cleanup;
                   "ok", cleanup everything except points that failed;
                   "all", cleanup everything anyway
    tmpdir:        local temporary directory where workdir will be created.
                   If set to None, tmpdir is set to default system temporary
                   directory (/tmp on linux).
    remote_tmpdir: temporary directory of the remote hosts. Overide tmpdir.
                   If None is given, remote_tmpdir is set to tmpdir.
    user_data:     data that will be send to wrapper_file execution environment.
    """

    def __new__(self,
                n_input,
                n_output,
                wrapper_file,
                hosts=[],
                scheduler=None,
                analytical=False,
                n_cores=0,
                files_to_send=[],
                cleanup='ok',
                tmpdir=None,
                remote_tmpdir=None,
                user_data=None,
               ):

        instance = OpenTURNSDistributedPythonFunction(n_input,
                                                      n_output,
                                                      wrapper_file,
                                                      hosts,
                                                      scheduler,
                                                      analytical,
                                                      n_cores,
                                                      files_to_send,
                                                      cleanup,
                                                      tmpdir,
                                                      remote_tmpdir,
                                                      user_data,
                                                     )
        return ot.NumericalMathFunction(instance)


class OpenTURNSDistributedPythonFunction(ot.OpenTURNSPythonFunction):

    """
    See DistributedPythonFunction description.
    """

    def __init__(self,
                 n_input,
                 n_output,
                 wrapper_file,
                 hosts=[],
                 scheduler=None,
                 analytical=False,
                 n_cores=0,
                 files_to_send=[],
                 cleanup='ok',
                 tmpdir=None,
                 remote_tmpdir=None,
                 user_data=None,
                ):

        # not compatible with ot < 1.2
        super(OpenTURNSDistributedPythonFunction, self).__init__(n_input, n_output)
        # ok with ot < 1.2
        #ot.OpenTURNSPythonFunction.__init__(self, n_input, n_output)

        wd_hosts_in = wrapper_data.WrapperDataHostsIn()
        self.wd_hosts_in = wd_hosts_in

        wd_hosts_in.scheduler = scheduler
        wd_hosts_in.n_cores = n_cores
        self.set_separate_workdir(not analytical)

        wd_hosts_in.wrapper_file = os.path.realpath(wrapper_file)
        if not os.path.exists(wd_hosts_in.wrapper_file):
            raise Exception(
                "wrapper_file (" + str(wd_hosts_in.wrapper_file) + ") not found!")

        for f in files_to_send:
            if not os.path.exists(f):
                raise Exception("file to send (" + str(f) + ") not found!")
        wd_hosts_in.files_to_send = files_to_send

        if tmpdir and len(tmpdir) > 0 and tmpdir[-1] == os.sep:
            tmpdir = tmpdir[:-1]
        wd_hosts_in.tmpdir = tmpdir

        if remote_tmpdir:
            if len(remote_tmpdir) and remote_tmpdir[-1] == os.sep:
                remote_tmpdir = remote_tmpdir[:-1]
            wd_hosts_in.remote_tmpdir = remote_tmpdir
        else:
            wd_hosts_in.remote_tmpdir = tmpdir

        if hosts:
            self.add_hosts(hosts)
        wd_hosts_in.cleanup = cleanup
        wd_hosts_in.user_data = user_data

        if cleanup not in "nokall":
            raise Exception("wrong cleanup parameter (" + str(cleanup) + ")!")

        if (ot.Log.Flags() & ot.Log.DBG) != 0:
            wd_hosts_in.extended_check = True

        # stop everything when set to true
        self.stop = False

    # extanded options ###
#
#    def add_scheduler(self, host, walltime, nb_nodes, mem_required,
#                      scheduler_type="PBS", qsub_param=""):
#
#    def add_file_to_send(self, local_file, remote_dir="", recursive=True,
#                         readonly=False, shared_file_system=False):
#        """
#        only useful for remote and scheduler compute
#        if remote_dir == "" (default): the file will be put on node's workdir
#        can be called several times
#        recursive, read_only, shared_file_system, remote_dir : not implemented
#        """
#
#    def add_file_to_get(self, remote_file, local_dir="", recursive=True):
#        """ get file from remote hosts """
#
#    def get_workdirs:     get every workdirs contents localy (not implemented)
    def set_separate_workdir(self, separate_workdir=True):
        """
        !use it only if you know what you are doing!
        separate_workdir:
            True: each thread has its own working directory,
            False: each thread share the same workdir, permit to avoid passing
              internally in/out point by file, useful only if each compute
              last less than 2s.
        """
        self.wd_hosts_in.separate_workdir = separate_workdir

    def add_hosts(self, hosts):
        for host in hosts:
            host_weight = 1
            host_name = host
            # if present separate host weight from host name
            try:
                weight_pos = string.rfind(host, ':')
                if weight_pos != -1:
                    host_name = host[:weight_pos]
                    host_weight = int(host[weight_pos+1:])
            except:
                ot.Log.Warn("Weight not understood for host: " + host + " . Set "
                            "to default weight: " + str(host_weight) + ' .')

            if host_name not in [h for h, w in self.wd_hosts_in.hosts]:
                self.wd_hosts_in.hosts.append([host_name, host_weight])
            else:
                ot.Log.Warn("Same host (" + host_name + ") added twice. "
                            "Instance not added twice.")

    # implement OT needed func ###

    def _exec(self, in_point):
        """ OT point entry """

        return (self._exec_sample([in_point]))[0]

    def _exec_sample(self, in_sample):
        """ OT sample entry """

        if len(in_sample) == 0:
            return []

        start_time = time.time()
        self.set_workdir_basename()

        remote_compute = self.wd_hosts_in.scheduler or self.wd_hosts_in.hosts
        if remote_compute:
            self.redirect_signal()

        try:
            curdir_bkp = os.getcwd()


            # set in sample
            if self.wd_hosts_in.separate_workdir == False and not remote_compute:
                # do not convert when local and no separate_workdir compute
                self.wd_hosts_in.sample = in_sample
            else:
                self.wd_hosts_in.sample = self.convert_to_list_of_list(
                    in_sample)

            # init out data structure
            wd_hosts_out = wrapper_data.WrapperDataHostsOut()
            wd_hosts_out.hostname
            self.wd_hosts_out = wd_hosts_out

            self.show_logs = ShowLogs(wd_hosts_out, slow_update=remote_compute)
            self.show_logs.start()

            # launch compute
            hostdispatcher = host_dispatcher.HostDispatcher(
                self.wd_hosts_in, wd_hosts_out)
            self.hostdispatcher = hostdispatcher
            hostdispatcher.exec_sample()

            # restore previous dir
            os.chdir(curdir_bkp)

        except Exception as e:
            ex_info = traceback.format_exc()
            ot.Log.Error('Exception received (' + ex_info + ')')
            if remote_compute:
                #e.errno, e.strerror
                self.restore_signal()
                self.stop_now()
            self.show_logs.show = False
            raise e
        if remote_compute:
            self.restore_signal()

        self.show_logs.show = False
        self.show_logs.join()

        compute_time = str(time.time() - start_time)
        ot.Log.Info('finished computing sample (' + str(len(in_sample)) +
                    ' points) in {0:.3f} s.'.format(float(compute_time)))

        return wd_hosts_out.sample

    # internal function ###
    def set_workdir_basename(self):
        """ get a workdir name that will be uniq for one compute """
        wrapper_name, extension = \
            os.path.splitext(
                os.path.basename(self.wd_hosts_in.wrapper_file))
        dirname = wrapper_name + '_' + time.strftime("%Y-%m-%d_%H-%M-%S")
        dirname += '_' + self.get_uuid()
        self.wd_hosts_in.workdir_basename = dirname
        ot.Log.Info('workdir basename: ' + dirname)

    def get_uuid(self):
        """ get a unique identifier """
        uuid = ""
        for i in range(6):
            r = random.randint(0, 9 + 26)
            if r > 9:
                r = chr(55 + r)
            uuid = uuid + str(r)
        return uuid

    def convert_to_list_of_list(self, in_sample):
        """
        private function

        convert data to pure python in order to be able to manipulate them
        without any OT dependances
        """
        return [[s for s in p] for p in in_sample]

    def redirect_signal(self):
        """
        private function
        """
        try:
            # ! When threads are enabled, this function can only be called from
            # the main thread
            self._prev_handler = signal.signal(signal.SIGINT,
                                               self.sigint_handler)
        except:
            ot.Log.Warn("Failed to setup sigint interrupt handler. Remote "
                        "compute will not been properly stopped when CTRL-C is "
                        "pressed.")

    def restore_signal(self):
        """
        private function
        """
        try:
            signal.signal(signal.SIGINT, self._prev_handler)
        except:
            ot.Log.Warn("Failed to reset sigint interrupt handler.")

    def sigint_handler(self, signum, frame):
        """
        private function
        """
        # if self.sigint_retry != 0:
        #    ot.Log.Warn('Sigint received. press CTRC-C again to exit.')
        #    self.sigint_retry -= 1
        # else:
        ot.Log.Error('Sigint received.')
        self.stop_now()
        #raise Exception("Sigint received.")

    def stop_now(self):
        if not self.stop:
            # avoid calling stop_now twice (should be protected by mutex?)
            self.stop = True

            ot.Log.Error('Start stopping children.')
            self.hostdispatcher.stop_now()
            self.show_logs.show = False
            ot.Log.Error('Children stopped.')


class ShowLogs(threading.Thread):

    """ a thread that show logs """

    def __init__(self, wd_hosts_out, slow_update=False):

        super(ShowLogs, self).__init__()
        self.wd_hosts_out = wd_hosts_out

        self.show = True

        if slow_update:
            self.cur_sleep = 1
            self.max_sleep = 2
        else:
            self.cur_sleep = 0.1
            self.max_sleep = 1

    def run(self):

        while True:
            hosts_out = self.wd_hosts_out
            log = hosts_out.get_next_log()

            while log:
                flag = log[0]
                timestamp = log[1]
                data = log[2]
                time_str = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                if flag == hosts_out.flag_debug:
                    ot.Log.Debug(time_str + ' - ' + data)
                elif flag == hosts_out.flag_warn:
                    ot.Log.Warn(time_str + ' - ' + data)
                elif flag == hosts_out.flag_error:
                    ot.Log.Warn(time_str + ' - Point ' + str(data[0]) +
                                ' encounter an error (' + data[1] + ')')
                elif flag == hosts_out.flag_point:
                    # ot.Log.Info(time_str + ' - Point ' + str(data[0]) + ' finished in ' +
                    #            data[1] + 's')
                    ot.Log.Info(time_str + ' - ' + data[2])

                log = hosts_out.get_next_log()

            # stop loop after having shown every log
            if not self.show:
                break

            time.sleep(self.cur_sleep)
            if self.cur_sleep < self.max_sleep:
                self.cur_sleep += 0.2


"""
====================================
Todo list
----

detect NFS if available
improve tranfert on localhost
get remote file
progress bar during file transfer
parallel fetch: try to get results of each hosts anytimes

print less logs (threads that print a summary every 5 minutes (nb of points), at the end: max moy min compute time, speedup.
put a log summary every 2 minutes to avoid ssh freeze. or give an option tune summmary frequency

test relaunch compute?
handle ssh communication error

warning if localhost != hostname, or localhost != localcompute, hostname hostname...
weight on nodes : change the params n_cores to a list of cores (one per host) OR give RAM and CPU of a single compute and compute the max nb of parallel compute launchable at a time OR call a user define function on each machine

be able to relaunch on a point or on a sample in order to relaunch from any point
on error, possibility to wait a correct point (the user would relaunch the point manually)
choose behavior on point error : crash on any point error; return default settable value (i.e. NaN) on point error; crash if nb point > x% (OT trow the whole sample if an error arise : no cache of the point that succeed (perhaps to be modified in OT))
on coupling_tools.execute function add a walltime argument : kill the process if it last longer than x seconds.
permit to the user to send log to OT from _exec() function of the wrapper

launch through a frontale
launch with some more scheduler (SGE, ...)
compress (tar or ssh -C) before send/receive them

improve pickle perf (use cpickle on file < 1GB)

improve when computing arithmetic function : python threading is really slow : _exec_sample + multiprocessing + numpy in wrapper?

reliable stop of subprocess (especially windows) when stopping OT script (e.g. CTRL-c)
improvment: multiprocessing or threading module? multiprocessing would permit os.chdir? would avoid pickling between core_dispatcher and wrapper_launcher?


==================================
Version
----

+improvment
-bugfix

r342
  +add host weight (permit to balance the number of point to compute per host)

r338
  +add user_data arg

v0.3 -===-
  +make otdistfunc an openturns module

r2761
  +remove python-paramiko dependancy
  +login and ssh port options for each hosts (through ~/.ssh/config file)
  -Fix do not remove workdir on sigint

r2753
  +Possibility to get the sample/point from any pickle file.
  +Improve modularity (i.e. in order to add sysfera support), improve in and out pickle data structure.

r2718
  +Stop subprocesses (remote ones too) when stopping openturns script (CTRL-c)
  +Get hosts from PBS scheduler.
  +Add coupling_tools module
  +Return error msg if the core_dispatcher_launcher fail to start on remote hosts (needs Debug OT log enabled).
  +Add wrapper name to the workdir.
  +wrapper_launcher.py is present on each point's workdir (permit to restart point's compute)
  +Access to remote hosts.
  +Adjust nb of core (global).
  -Fix compute on a point.
  -Fix n_cores when remote computing.
  -Remove hosts that appears twice.
  -Fix errors when setting tmpdir on NFS.

"""
