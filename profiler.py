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

from mozInstall import MozInstaller
import urllib
import os
from pulsebuildmonitor import PulseBuildMonitor
import re
import subprocess
import shutil

PLAIN_TESTS = { 'Harness_sanity/test_sanityEventUtils.html': 50,
                'Harness_sanity/test_sanitySimpletest.html': 60,
                'Harness_sanity/test_sanityPluginUtils.html': 10,
              }
# SpecialPowers can't be tested using window.open() so we can't loop them using mochitest.
# We can move these up to the PLAIN_TESTS once Bug 681392 is resolved
SPECIAL_TESTS = { 'test_SpecialPowersExtension.html': 20,
                  'test_sanityWindowSnapshot.html': 5
                }
CHROME_TESTS = { 'test_sanityChromeUtils.xul': 200,
                 'test_sanityEventUtilsChrome.xul': 50
               }

class ProfilerRunner(object):
    def __init__(self, builddata, dest):
        self.builddata = builddata
        self.dest = dest
        self.obj_dir = "/Users/mdas/Code/other-moz/mozilla/obj-dbg-win32/" #TODO: remove
        #self.getBuild()

    def getBuild(self):
        if self.builddata['buildurl']:
            urllib.urlretrieve(self.builddata['buildurl'], self.dest)

    def runTests(self):
        if not self.obj_dir:
            print 'No mozilla object directory given. Aborting.'
            return
        # Unfortunate hack: we can't use --close-when-done on single tests, shove the file in a temp dir and run it there.
        # I could have read the input and killed the make process instead, but that was getting tricky, hacky and I'm not sure how it would 
        # function in Windows.
        # Can clear this when Bug 508664 is resolved, as it will allow us to close single tests.
        temp_dir_name = 'temp_profiler_folder'
        harness_sanity_dir = os.path.join(self.obj_dir, '_tests', 'testing', 'mochitest', 'tests', 'Harness_sanity')
        temp_dir = os.path.join(harness_sanity_dir, temp_dir_name)
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        prof = re.compile("Profile::((\w+):\s*(\d+))")
        extra_args = '--loops=%s --close-when-done'
        print "creating: %s" % temp_dir
        os.mkdir(temp_dir)

        for test, loops in SPECIAL_TESTS.iteritems():
            print 'running: %s' % test
            shutil.copy(os.path.join(harness_sanity_dir, test), temp_dir)
            test_path = os.path.join('Harness_sanity', temp_dir_name)
            loadTime = 0
            runTime = 0
            times = loops
            while (times >= 0):
                output = subprocess.Popen(['make','-C', self.obj_dir,'mochitest-plain'],stdout=subprocess.PIPE,env={'TEST_PATH': test_path})
                matches = prof.findall(output.communicate()[0])
                for match in matches:
                    if 'Run' in match[1]:
                        runTime += int(match[2])
                    else:
                        loadTime += int(match[2])
                times -= 1
            print "Load: %s, Run: %s" % (loadTime / float(loops), runTime / float(loops))
            os.remove(os.path.join(temp_dir, test))
        shutil.rmtree(temp_dir)

        for test, loops in PLAIN_TESTS.iteritems():
            print test
            output = subprocess.Popen(['make','-C', self.obj_dir,'mochitest-plain'],stdout=subprocess.PIPE,env={'TEST_PATH': test, 'EXTRA_TEST_ARGS': extra_args % loops})
            loadTime = 0
            runTime = 0
            matches = prof.findall(output.communicate()[0])
            for match in matches:
                if 'Run' in match[1]:
                    runTime += int(match[2])
                else:
                    loadTime += int(match[2])
            print "Load: %s, Run: %s" % (loadTime / float(loops), runTime / float(loops))

        for test, loops in CHROME_TESTS.iteritems():
            output = subprocess.Popen(['make','-C', self.obj_dir,'mochitest-chrome'],stdout=subprocess.PIPE,env={'TEST_PATH': test, 'EXTRA_TEST_ARGS': extra_args % loops})
            loadTime = 0
            runTime = 0
            matches = prof.findall(output.communicate()[0])
            for match in matches:
                if 'Run' in match[1]:
                    runTime += int(match[2])
                else:
                    loadTime += int(match[2])
            print "Load: %s, Run: %s" % (loadTime / float(loops), runTime / float(loops))
        print 'Done'
if __name__ == "__main__":
    pr = ProfilerRunner({'buildurl': 'ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-inbound-macosx64/1312010895/firefox-8.0a1.en-US.mac.checksums'}, 'testfile')
    pr.runTests()
