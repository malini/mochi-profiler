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
import re
import stat
import subprocess
import shutil
import zipfile

PLAIN_REPEATS = 50

CHROME_REPEATS = 100
CHROME_TESTS = [ 'test_sanityChromeUtils.xul'
               ]

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
        self.plain_log_file = os.path.join(self.temp_build_dir, 'plainlog')
        self.chrome_log_file = os.path.join(self.temp_build_dir, 'chromelog')
        print "temp_build_dir: %s" % self.temp_build_dir

        self.build_url = self.builddata['buildurl']
        self.build_file = os.path.join(self.temp_build_dir, self.build_url.rpartition("/")[2])
        print "build_file: %s" % self.build_file


        self.test_url = self.builddata['testsurl']
        self.test_path = os.path.join(self.temp_build_dir, 'tests')
        self.cert_path = os.path.join(self.test_path, 'certs')
        self.util_path = os.path.join(self.test_path, 'bin')
        if 'mac' in self.platform:
            self.app_name = os.path.join(self.temp_build_dir, 'Minefield.app', 'Contents/MacOS/firefox-bin')
        if 'linux' in self.platform:
            self.app_name = os.path.join(self.temp_build_dir, 'firefox', 'firefox-bin')
        if 'win' in self.platform:
            self.app_name = os.path.join(self.temp_build_dir, 'firefox', 'firefox.exe')
        print "test_path: %s" % self.test_path

        # make a temp directory for the build/tests to extract to and run in
        os.mkdir(self.temp_build_dir)
        try:
            self.get_files()
            self.run_tests()
            self.parse_and_submit()
        finally:
            self.cleanup()

    def make_exec(self, path):
        def mod(arg, dir, names):
            for name in names:
                print dir,name
                os.chmod(os.path.join(dir, name), 0777)
        os.path.walk(path, mod, None)

    def get_files(self):
        # get the build
        print "getting build_url"
        urllib.urlretrieve(self.build_url, self.build_file)
        print "installing build"
        if 'mac' in self.platform:
            MozInstaller(src=self.build_file, dest=self.temp_build_dir, dest_app='Minefield.app') # dest_app is only used for dmgs
        else:
            MozInstaller(src=self.build_file, dest=self.temp_build_dir, dest_app='firefox')

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
        shutil.rmtree(self.temp_build_dir)

    def run_tests(self):
        # Unfortunate hack: we can't use --close-when-done on single tests, so just run all of Harness_sanity and pull out the relevant data
        # Can change this when Bug 508664 is resolved, as it will allow us to close single tests.
        runtests_location = os.path.join(self.test_path, 'mochitest', 'runtests.py')
        profile_location = os.path.join(self.test_path, 'mochitest', 'profile_path')
        print "runtests_location: %s" % runtests_location
        try:
            shutil.rmtree(temp_dir_path)
        except:
            pass
        extra_args = '--repeat=%s'

        harness = 'Harness_sanity'
        extra_profile_file = os.path.join(self.util_path, 'plugins')
        ret = subprocess.call(['python',
                                runtests_location,
                                '--profile-path=%s' % profile_location, 
                                '--test-path=%s' % harness,
                                extra_args % PLAIN_REPEATS,
                                '--certificate-path=%s' % self.cert_path,
                                '--utility-path=%s' % self.util_path,
                                '--appname=%s' % self.app_name,
                                '--log-file=%s' % self.plain_log_file,
                                '--extra-profile-file=%s' % extra_profile_file,
                                '--close-when-done',
                                '--autorun'
                                ])

        for test_path in CHROME_TESTS:
            print test_path
            ret = subprocess.call(['python',
                                    runtests_location,
                                    '--profile-path=%s' % profile_location,
                                    '--chrome',
                                    '--test-path=%s' % test_path,
                                    extra_args % CHROME_REPEATS,
                                    '--certificate-path=%s' % self.cert_path,
                                    '--utility-path=%s' % self.util_path,
                                    '--appname=%s' % self.app_name,
                                    '--log-file=%s' % self.chrome_log_file,
                                    '--close-when-done',
                                    '--autorun'
                                    ])
        print 'Done running tests'

    def parse_and_submit(self):
        plain_results = {}
        chrome_results = {}
        prof = re.compile("Profile::((\w+):\s*(\d+))")
        logs = open(self.plain_log_file, 'r')
        #parse out which test is being run.
        #also, parse out if the test failed
        for line in logs.readlines():
            matches = prof.findall(line)
            for match in matches:
                if plain_results.has_key(match[1]):
                    plain_results[match[1]] += int(match[2])
                else:
                    plain_results[match[1]] = int(match[2])
        logs.close()
        for k, v in plain_results.iteritems():
            plain_results[k] = plain_results[k] / PLAIN_REPEATS
        print plain_results
        logs = open(self.chrome_log_file, 'r')
        for line in logs.readlines():
            matches = prof.findall(line)
            for match in matches:
                if chrome_results.has_key(match[1]):
                    chrome_results[match[1]] += int(match[2])
                else:
                   chrome_results[match[1]] = int(match[2])
        logs.close()
        for k, v in chrome_results.iteritems():
            chrome_results[k] = chrome_results[k] / CHROME_REPEATS
        print chrome_results
        
"""
#for testing
if __name__ == "__main__":
    pr = ProfilerRunner('macosx64')
    pr.start({'buildurl': 'ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-macosx64/1314714989/firefox-9.0a1.en-US.mac.dmg',
              'testsurl': 'ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-macosx64/1314714989/firefox-9.0a1.en-US.mac.tests.zip',
              'platform': 'macosx64',
              'timestamp': 100
              })
"""
