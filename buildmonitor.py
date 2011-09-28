# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is mozilla.org code.
#
# The Initial Developer of the Original Code is Mozilla Foundation.
#
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""
Creates a ProfileRunner when a new build is detected from pulse.
User must pass in which platform this code is running on (linux, win32, macosx64, ...)
"""

from pulsebuildmonitor import start_pulse_monitor
from profiler import ProfilerRunner
import sys
import socket

def main():
    if len(sys.argv) != 2:
        sys.exit("Please pass in the platform of the current system (ex: linux, win32, ...)")
    platform = sys.argv[1]
    pr = ProfilerRunner(platform)
    monitor = start_pulse_monitor(buildCallback=pr.start,
                                  testCallback=None,
                                  pulseCallback=None,
                                  label="Profiler-" + socket.gethostname(),
                                  tree=['mozilla-central'],
                                  platform=platform,
                                  mobile=False,
                                  buildtype=None,
                                  logger="Profiler")
    monitor.join()

if __name__ == "__main__":
    main()
