##############################################################################
#
# Copyright (c) 2006-2007 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""zopectl -- control Zope using zdaemon.

Usage: zopectl [options] [action [arguments]]

Options:
-h/--help -- print usage message and exit
-i/--interactive -- start an interactive shell after executing commands
action [arguments] -- see below

Actions are commands like "start", "stop" and "status". If -i is specified or
no action is specified on the command line, a "shell" interpreting actions
typed interactively is started. Use the action "help" to find out about
available actions.
"""

import csv
import os
import os.path
import sys
from pkg_resources import iter_entry_points

from Zope2.Startup import zopectl


class AdjustedZopeCmd(zopectl.ZopeCmd):

    def do_start(self, arg):
        self.get_status()
        if not self.zd_up:
            args = [
                self.options.python,
                self.options.zdrun,
                ]
            args += self._get_override("-S", "schemafile")
            args += self._get_override("-C", "configfile")
            args += self._get_override("-b", "backofflimit")
            args += self._get_override("-d", "daemon", flag=1)
            args += self._get_override("-f", "forever", flag=1)
            args += self._get_override("-s", "sockname")
            args += self._get_override("-u", "user")
            if self.options.umask:
                args += self._get_override("-m", "umask",
                                           oct(self.options.umask))
            args += self._get_override("-x", "exitcodes",
                ",".join(map(str, self.options.exitcodes)))
            args += self._get_override("-z", "directory")

            args.extend(self.options.program)

            if self.options.daemon:
                flag = os.P_NOWAIT
            else:
                flag = os.P_WAIT
            env = self.environment().copy()
            env.update({'ZMANAGED': '1', })
            os.spawnvpe(flag, args[0], args, env)
        elif not self.zd_pid:
            self.send_action("start")
        else:
            print "daemon process already running; pid=%d" % self.zd_pid
            return
        self.awhile(lambda: self.zd_pid,
                    "daemon process started, pid=%(zd_pid)d")

    def environment(self):
        configroot = self.options.configroot
        env = dict(os.environ)
        try:
            shome = configroot.softwarehome
        except AttributeError:
            shome = None
        env.update({'INSTANCE_HOME': configroot.instancehome})
        if shome:
            env.update({'PYTHONPATH': os.pathsep.join(sys.path + [shome])})
        return env

    def get_startup_cmd(self, python, more, pyflags=""):
        # If we pass the configuration filename as a win32
        # backslashed path using a ''-style string, the backslashes
        # will act as escapes.  Use r'' instead.
        # Also, don't forget that 'python'
        # may have spaces and needs to be quoted.
        cmdline = ('"%s" %s -c "from Zope2 import configure; '
                   'configure(r\'%s\'); ' %
                   (python, pyflags, self.options.configfile))
        cmdline = cmdline + more + '\"'
        return cmdline

    def do_run(self, arg):
        # If the command line was something like
        # """bin/instance run "one two" three"""
        # cmd.parseline will have converted it so
        # that arg == 'one two three'. This is going to
        # foul up any quoted command with embedded spaces.
        # So we have to return to self.options.args,
        # which is a tuple of command line args,
        # throwing away the "run" command at the beginning.
        #
        # Further complications: if self.options.args has come
        # via subprocess, it may look like
        # ['run "arg 1" "arg2"'] rather than ['run','arg 1','arg2'].
        # If that's the case, we'll use csv to do the parsing
        # so that we can split on spaces while respecting quotes.
        if len(self.options.args) == 1:
            tup = csv.reader(self.options.args, delimiter=' ').next()[1:]
        else:
            tup = self.options.args[1:]

        if not tup:
            print "usage: run <script> [args]"
            return

        # If we pass the script filename as a win32 backslashed path
        # using a ''-style string, the backslashes will act as
        # escapes.  Use r'' instead.
        #
        # Remove -c and add script as sys.argv[0]
        script = tup[0]
        cmd = 'import sys; sys.argv.pop(); sys.argv.append(r\'%s\'); ' % script
        if len(tup) > 1:
            argv = tup[1:]
            cmd += '[sys.argv.append(x) for x in %s]; ' % argv
        cmd += 'import Zope2; app=Zope2.app(); execfile(r\'%s\')' % script
        cmdline = self.get_startup_cmd(self.options.python, cmd)

        self._exitstatus = os.system(cmdline)

    def do_console(self, arg):
        self.do_foreground(arg, debug=False)

    def help_console(self):
        print "console -- Run the program in the console."
        print "    In contrast to foreground this does not turn on debug mode."

    def do_debug(self, arg):
        cmdline = self.get_startup_cmd(self.options.python,
                                       'import Zope2; app=Zope2.app()',
                                       pyflags = '-i', )
        print ('Starting debugger (the name "app" is bound to the top-level '
               'Zope object)')
        os.system(cmdline)

    def do_foreground(self, arg, debug=True):
        self.get_status()
        pid = self.zd_pid
        if pid:
            print "To run the program in the foreground, please stop it first."
            return

        import subprocess
        env = self.environment()
        program = self.options.program
        local_additions = []

        if debug:
            if not program.count('-X'):
                local_additions += ['-X']
            if not program.count('debug-mode=on'):
                local_additions += ['debug-mode=on']
            program.extend(local_additions)

        command = program

        if debug:
            try:
                self._exitstatus = subprocess.call(command, env=env)
            except KeyboardInterrupt:
                return
            for addition in local_additions:
                program.remove(addition)
        else:
            # non-debug mode on Unix: replace the current process
            # (required by e.g. supervisord)
            os.execve(program[0], command, env)

    def do_test(self, arg):
        print("The test command is no longer supported. Please use a "
              "zc.recipe.testrunner section in your buildout config file "
              "to get a test runner for your environment. Most often you "
              "will name the section `test` and can run tests via: "
              "bin/test -s <my.package>")
        return


def main(configuration=None):
    """
    Customized entry point for launching Zope without forking
    other processes
    """
    args = sys.argv[1:]
    if configuration is not None:
        args = ['-C', configuration] + args

    options = zopectl.ZopeCtlOptions()
    # Realize arguments and set documentation which is used in the -h option
    options.realize(args, doc=__doc__)

    # Change the program to avoid warning messages
    startup = os.path.dirname(zopectl.__file__)

    script = os.path.join(startup, 'run.py')
    options.program = [options.python, script, '-C', options.configfile]

    # We use our own ZopeCmd set, that is derived from the original one.
    c = AdjustedZopeCmd(options)

    # Mix in any additional commands supplied by other packages:
    for ep in iter_entry_points('plone.recipe.zope2instance.ctl'):
        func_name = 'do_' + ep.name
        func = ep.load()
        # avoid overwriting the standard commands
        if func_name not in dir(c):
            setattr(c.__class__, func_name, func)

    # The PYTHONPATH is not set, so all commands starting a new shell fail
    # unless we set it explicitly
    os.environ['PYTHONPATH'] = os.path.pathsep.join(sys.path)

    # If a command was specified: call the corresponding do_*() method.
    #
    # If that method set an exit status, exit this Python script
    # with exit status 1 ("abnormal termination"). Otherwise use the
    # default exit code 0 ("successful termination").
    #
    # The exit status is used for "Restart" on the ZMI Control Panel or
    # @@maintenance-controlpanel (see http://dev.plone.org/plone/ticket/10906).
    #
    # Arguably we should return the exit status and let the wrapper script exit.
    # But it's generated by setuptools, and doesn't have that functionality.

    if options.args:
        c.onecmd(' '.join(options.args))
        sys.exit(min(c._exitstatus, 1))

    # If no command was specified: enter interactive mode.

    try:
        import readline
    except ImportError:
        pass
    print 'Program: %s' % ' '.join(options.program)
    c.do_status()
    c.cmdloop()
