# ===================================================================
#
# Copyright (c) 2022-2024 Workday, Inc.
#
# This file is provided to you under the Apache License,
# Version 2.0 (the "License"); you may not use this file
# except in compliance with the License.  You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# ===================================================================
#
# This file lives in the 'bin' directory to be shared by command scripts.
# After it's imported, ../lib (if it exists) is in the module search path,
# so other support modules can be loaded from there transparently.
#

def _init_module():
    import os, sys
    # __file__ isn't guaranteed to be absolute prior to Python 3.9
    bindir = os.path.dirname(os.path.abspath(__file__))
    libdir = os.path.join(os.path.dirname(bindir), 'lib')

    if os.path.isdir(libdir) and os.access(libdir, (os.R_OK|os.X_OK)):
        sp = sys.path
        # see if it was already set via command line or $PYTHONPATH
        for elem in sp:
            # There can be nonexistent elements in sp, which will raise
            # an error from os.path.samefile
            if os.path.exists(elem) and os.path.samefile(elem, libdir):
                return
        # sp0 *should* be bindir
        sp0 = sp[0]
        if os.path.exists(sp0) and os.path.samefile(sp0, bindir):
            # insert our lib immediately after it
            sp.insert(1, libdir)
        else:
            # not expected, so play it safe
            sp.append(libdir)

# Execute on module load then discard. We don't want or need it in memory,
# and there's no reason to ever invoke it again.
_init_module()
del _init_module
