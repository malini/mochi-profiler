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
import stat
import subprocess
import shutil
import zipfile

PLAIN_TESTS = { 'Harness_sanity/test_sanityEventUtils.html': 2, #50,
                'Harness_sanity/test_sanitySimpletest.html': 2, #60,
                'Harness_sanity/test_sanityPluginUtils.html': 2,# 10,
                #'Harness_sanity/test_sanity.html': 1 #TODO: REMOVE
              }
# SpecialPowers can't be tested using window.open() so we can't loop them using mochitest.
# We can move these up to the PLAIN_TESTS once Bug 681392 is resolved
SPECIAL_TESTS = { #'test_SpecialPowersExtension.html': 1 #20,
                  'test_sanityWindowSnapshot.html': 1 #5
                }
CHROME_TESTS = { 'test_sanityChromeUtils.xul': 2, #200,
                 'test_sanityEventUtilsChrome.xul': 2 # 50
                 #'test_synthesizeDrop.xul': 1 #TODO: REMOVE
               }

#submit separated opt/debug metrics

class ProfilerRunner(object):
    def __init__(self, platform):
        self.platform = platform
        self.builddata = {}
        self.build_url = None
        self.build_file = None
        self.test_url = None
        self.test_path = None
        self.temp_build_dir = None
        self.cert_path = None
        self.util_path = None
        self.app_name = None

    def start(self, builddata):
        assert(builddata['buildurl'])
        assert(builddata['testsurl'])
        assert(builddata['timestamp'])
        assert(builddata['platform'] == self.platform)

        # extract useful data from builddata
        self.builddata = builddata
        self.temp_build_dir = 'profiler-%s' % builddata['timestamp']
        print "temp_build_dir: %s" % self.temp_build_dir

        self.build_url = self.builddata['buildurl']
        self.build_file = os.path.join(self.temp_build_dir, self.build_url.rpartition("/")[2])
        print "build_file: %s" % self.build_file


        self.test_url = self.builddata['testsurl']
        self.test_path = os.path.join(self.temp_build_dir, 'tests')
#python runtests.py --certificate-path=/Users/mdas/Downloads/temp/certs --utility-path=/Users/mdas/Downloads/temp/bin --appname=/Users/mdas/Code/mozilla-central/obj-dbg-mac/dist/Nightly.app/Contents/MacOS/firefox-bin
        self.cert_path = os.path.join(self.test_path, 'certs')
        self.util_path = os.path.join(self.test_path, 'bin')
        if 'osx' in self.platform:
            self.app_name = os.path.join(self.temp_build_dir, 'Minefield.app', 'Contents/MacOS/firefox-bin')
        if 'linux' in self.platform:
            #TODO: FIGURE THIS OUT
            pass
        if 'win' in self.platform:
            #TODO: FIGURE THIS OUT
            pass
        print "test_path: %s" % self.test_path

        # make a temp directory for the build/tests to extract to and run in
#        os.mkdir(self.temp_build_dir)
        try:
        #    self.getFiles()
            self.runTests()
        finally:
          #  self.cleanup()
          pass

    def make_exec(self, path):
        def mod(arg, dir, names):
            for name in names:
                print dir,name
                os.chmod(os.path.join(dir, name), 0777)
        os.path.walk(path, mod, None)

    def getFiles(self):
        # get the build
        print "getting build_url"
        urllib.urlretrieve(self.build_url, self.build_file)
        print "installing build"
        MozInstaller(src=self.build_file, dest=self.temp_build_dir, dest_app='Minefield.app') # dest_app is only used for dmgs

        # get the tests.zip
        print "getting tests.zip"
        test_zip = os.path.join(self.temp_build_dir, self.test_url.rpartition("/")[2])
        urllib.urlretrieve(self.test_url, test_zip)
        print "unzipping, oh la la: %s" % test_zip
        file = zipfile.ZipFile(test_zip, 'r')
        #file.external_attr = 0777 << 16L #TODO: doesn't work, but a solution like this is better than make_exec
        file.extractall(path=self.test_path)
        if not 'win' in self.platform:
            # make the certs and bin files executable
            self.make_exec(os.path.join(self.test_path, 'certs'))
            self.make_exec(os.path.join(self.test_path, 'bin'))
            self.make_exec(os.path.join(self.test_path, 'mochitest'))

    def cleanup(self):
        print "cleaning"
        #shutil.rmtree(self.temp_build_dir)

    def runTests(self):
        # Unfortunate hack: we can't use --close-when-done on single tests, shove the file in a temp dir and run it there.
        # I could have read the input and killed the make process instead, but that was getting tricky, hacky and I'm not sure how it would 
        # function in Windows.
        # Can clear this when Bug 508664 is resolved, as it will allow us to close single tests.
        runtests_location = os.path.join(self.test_path, 'mochitest', 'runtests.py')
        profile_location = os.path.join(self.test_path, 'mochitest', 'profile_path')
        print "runtests_location: %s" % runtests_location
        temp_dir_name = 'temp_profiler_folder'
        harness_sanity_dir = os.path.join(self.test_path, 'mochitest', 'tests', 'Harness_sanity')
        temp_dir = os.path.join(harness_sanity_dir, temp_dir_name)
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        prof = re.compile("Profile::((\w+):\s*(\d+))")
        #extra_args = '--repeat=%s'
        extra_args = '--loops=%s'
        print "creating: %s" % temp_dir
        os.mkdir(temp_dir)
        #os.mkdir(os.path.join(temp_dir, 'tests'))
        #shutil.copytree(os.path.join(self.test_path, 'mochitest', 'tests', 'SimpleTest'), os.path.join(temp_dir, 'tests', 'SimpleTest'))

        for test, loops in SPECIAL_TESTS.iteritems():
            print 'running: %s' % test
            shutil.copy(os.path.join(harness_sanity_dir, test), temp_dir)
            test_path = os.path.join('Harness_sanity', temp_dir_name)
            loadTime = 0
            runTime = 0
            times = loops
            while (times >= 0):
                print "calling runtests"
#python runtests.py --certificate-path=/Users/mdas/Downloads/temp/certs --utility-path=/Users/mdas/Downloads/temp/bin --appname=/Users/mdas/Code/mozilla-central/obj-dbg-mac/dist/Nightly.app/Contents/MacOS/firefox-bin
                output = subprocess.Popen(['python', runtests_location, '--profile-path=%s' % profile_location, '--test-path=%s' % test_path, '--certificate-path=%s' % self.cert_path, '--utility-path=%s' % self.util_path, '--appname=%s' % self.app_name,  '--close-when-done', '--autorun'], stdout=subprocess.PIPE)
                out = output.communicate()[0]
                print out
                matches = prof.findall(out)
                for match in matches:
                    print match
                    if 'Run' in match[1]:
                        print runTime
                        runTime += int(match[2])
                    else:
                        print loadTime
                        loadTime += int(match[2])
                times -= 1
            print "Load: %s, Run: %s" % (loadTime / float(loops), runTime / float(loops))

        for test, loops in PLAIN_TESTS.iteritems():
            print test
            output = subprocess.Popen(['python', runtests_location, '--profile-path=%s' % profile_location, '--test-path=%s' % test_path, extra_args % loops,  '--certificate-path=%s' % self.cert_path, '--utility-path=%s' % self.util_path, '--appname=%s' % self.app_name,  '--close-when-done', '--autorun'], stdout=subprocess.PIPE)
            loadTime = 0
            runTime = 0
            matches = prof.findall(output.communicate()[0])
            for match in matches:
                print match
                if 'Run' in match[1]:
                    runTime += int(match[2])
                else:
                    loadTime += int(match[2])
            print "Load: %s, Run: %s" % (loadTime / float(loops), runTime / float(loops))

        for test, loops in CHROME_TESTS.iteritems():
            output = subprocess.Popen(['python', runtests_location, '--profile-path=%s' % profile_location, '--test-path=%s' % test_path, extra_args % loops,  '--certificate-path=%s' % self.cert_path, '--utility-path=%s' % self.util_path, '--appname=%s' % self.app_name,  '--close-when-done', '--autorun'], stdout=subprocess.PIPE)
            loadTime = 0
            runTime = 0
            matches = prof.findall(output.communicate()[0])
            for match in matches:
                print match
                if 'Run' in match[1]:
                    runTime += int(match[2])
                else:
                    loadTime += int(match[2])
            print "Load: %s, Run: %s" % (loadTime / float(loops), runTime / float(loops))
        shutil.rmtree(temp_dir)
        print 'Done'

if __name__ == "__main__":
    pr = ProfilerRunner('macosx64')
    pr.start({'buildurl': 'ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-macosx64/1314714989/firefox-8.0a1.en-US.mac.dmg',
              'testsurl': 'ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-macosx64/1314714989/firefox-8.0a1.en-US.mac.tests.zip',
              'platform': 'macosx64',
              'timestamp': 100
              })
