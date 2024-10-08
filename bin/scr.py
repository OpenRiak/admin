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
# After it's imported, 'LIB_DIR' (if it exists) is in the module search path,
# so other support modules can be loaded from there transparently.
#

import logging
import os
import sys
from typing import Mapping, NoReturn, Optional, Sequence

# ===================================================================
# Common type aliases
# ===================================================================

CmdArgs = Sequence[str]
CmdName = str
FsPath  = str
Name    = str
Names   = Sequence[Name]
SemVer  = str
Vsn     = Sequence[int]

# ===================================================================
# Pseudo-constants
# ===================================================================

BIN_DIR:    FsPath
CUR_DIR:    FsPath
ETC_DIR:    FsPath
LIB_DIR:    FsPath
LOG_DIR:    FsPath
REL_DIR:    FsPath
SCH_DIR:    FsPath

PROG_NAME:  CmdName

LOG_LEVELS: Mapping[str, int]

# If True:
# - Print some additional info from certain operations.
# - Display stack traces on error.
debug: bool = False

# ===================================================================
# Validators suitable as the 'type' parameter in
#   argparse.ArgumentParser.add_argument(...)
# where their name will be reported on error.
# ===================================================================

def NamesListOrFile(param: str) -> Names:
    if param.startswith('@'):
        param = read_file(ReadableFile(param[1:]))
    # it'll be de-duplicated when it's consumed
    return param.replace(',', ' ').split()

# Argument validator function whose name may be reported on error
def PossibleFile(path: str) -> str:
    fp = os.path.abspath(os.path.expanduser(path))
    if os.path.exists(fp):
        if not os.path.isfile(fp):
            raise_param_error(f"exists but not a file: '{fp}'")
        # Must be at least readable OR writeable
        if not (os.access(fp, os.R_OK) or os.access(fp, os.W_OK)):
            raise_param_error(f"insufficient file permissions: '{fp}'")
    else:
        # Enclosing directory must exist and be writeable
        dp = os.path.dirname(fp)
        if not os.path.isdir(dp):
            raise_param_error(f"not a directory: '{dp}'")
        if not os.access(dp, os.W_OK):
            raise_param_error(f"insufficient directory permissions: '{dp}'")
    return fp

# Argument validator function whose name may be reported on error
def ReadableAbsDir(path: str) -> str:
    if not os.path.isdir(path):
        raise_param_error(f"not a directory: '{path}'")
    if not os.access(path, os.W_OK):
        raise_param_error(f"insufficient directory permissions: '{path}'")
    return path

# Argument validator function whose name may be reported on error
def ReadableAbsFile(path: str) -> str:
    if not (os.path.isfile(path) and os.access(path, os.R_OK)):
        raise_param_error(f"not a readable file: '{path}'")
    return path

# Argument validator function whose name may be reported on error
def ReadableDir(path: str) -> str:
    return ReadableAbsDir(os.path.abspath(os.path.expanduser(path)))

# Argument validator function whose name may be reported on error
def ReadableFile(path: str) -> str:
    return ReadableAbsFile(os.path.abspath(os.path.expanduser(path)))

# ===================================================================
# Common helpers
# ===================================================================

def dict_with(src: Mapping, keys: Sequence, keyorder: bool = True) -> dict:
    """
    Creates a new `dict` containing the `key => val` mappings from `src` whose
    keys exist in `keys`.
    :param src: The `Mapping` instance from which to draw keys and values.
    :param keys: The keys to be copied from `src` if they exist there.
    :param keyorder: If `True` (the default) the insertion order in the result
        dict is that of `keys`.
        If `False` the insertion order is that of `src`.
    :return: A new `dict` containing only the keys in `keys` that exist in `src`.
    """
    out = {}
    if keyorder:
        for key in keys:
            if key in src:
                out[key] = src[key]
    else:
        for key, val in src.items():
            if key in keys:
                out[key] = val
    return out

def read_file(path: str) -> str:
    """
    Reads and returns the contents of the specified file.
    :param path: The relative or absolute path of the file to be read.
    :return: The contents of the file in the default encoding.
    """
    with open(path, 'rt') as fd:
        return fd.read()

def resolve_conf_path(path: str) -> str:
    """
    Returns an absolute filesystem path with leading '~' or '{{...}}'
    patterns resolved.
    An unrecognized pattern causes a `KeyError` exception to be raised.
    :param path: An absolute or relative filesystem path, possibly with a
        leading substitution pattern.
    :return: An absolute path.
    """
    if path.startswith('~'):
        path = os.path.expanduser(path)
    elif path.startswith('{{'):
        # Build per-use as some *may* be changed at runtime. Building a dict
        # from constants is cheaper than a series of inline comparisons.
        stache_map: Mapping[str, str] = {
            'bin':    BIN_DIR,
            'etc':    ETC_DIR,
            'lib':    LIB_DIR,
            'log':    LOG_DIR,
            'prog':   PROG_NAME,
            'rel':    REL_DIR,
            'schema': SCH_DIR }
        subend: int = path.index('}}')
        substr: str = path[2:subend].strip().lower()
        repl: str = stache_map[substr]
        tail: str = path[(subend + 2):]
        if tail[0] in _fspath_seps:
            path = repl + tail
        else:
            path = os.path.join(repl, tail)
    return os.path.abspath(path)

def semver_to_vsn(vstr: SemVer) -> Vsn:
    """
    Parses a semver-ish string into a sequence of integers.
    :param vstr: The string to parse.
    :return: A sequence of the integral segments found in `vstr`.
    """
    return tuple(int(s) for s in vstr.split('.') if s.isdecimal())

def vsn_to_semver(vsn: Vsn) -> SemVer:
    """
    Joins a sequence of integers into a dotted-decimal string.
    :param vsn: A sequence of integers representing a version.
    :return: A semver string.
    """
    return '.'.join(str(i) for i in vsn)

def write_file(path: str,
               content: Optional[str] = None,
               mode: Optional[int] = None) -> int:
    """
    Creates or truncates the file at `path`, optionally wrting `content`
    and/or setting the file's `mode`.

    If `content` is not provided, a zero-byte file is created.
    :param path: The relative or absolute path of the file to be written.
    :param content: [optional]
        Content to be written to the file as text in the default encoding.
    :param mode: [optional]
        The integral permission bits to set on the target file.
    :return: The number of characters written.
    """
    with open(path, 'wt') as fd:
        if mode:
            os.chmod(path, mode)
        if content:
            return fd.write(content)
    return 0

# ===================================================================
# Exceptions
# ===================================================================

def raise_param_error(msg: str, bad_type: bool = False) -> NoReturn:
    exc: Exception
    if debug:
        exc = ParamTypeError(msg) if bad_type else ParamValueError(msg)
    else:
        exc = TypeError(msg) if bad_type else ValueError(msg)
    raise exc

class CommandError(Exception):
    pass

class ParamTypeError(Exception):
    pass

class ParamValueError(Exception):
    pass

# ===================================================================
# Initialization
# ===================================================================

def init_log(level: str,
        logdir: Optional[str] = None, logname: Optional[str] = None) -> None:
    global LOG_DIR
    if (loglevel := LOG_LEVELS[level.upper()]) < 0:
        # disable
        logging.disable((2^31)-1)
        return
    if logdir:
        LOG_DIR = logdir = resolve_conf_path(logdir)
    else:
        logdir = LOG_DIR
    if not os.path.isdir(logdir):
        if os.path.exists(logdir):
            raise_param_error(f"not a directory: '{logdir}'")
        os.mkdir(logdir)
    if not os.access(logdir, (os.R_OK|os.W_OK|os.X_OK)):
        raise_param_error(f"insufficient directory permissions: '{logdir}'")
    if not logname:
        logname = PROG_NAME
    logfile = os.path.join(logdir, logname + '.log')
    logging.basicConfig(
        filename=logfile, filemode='at',
        format='%(asctime)s %(levelname)-7s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=loglevel )

# ===================================================================
# Internal
# ===================================================================

# Probably overkill, but this is the ONLY place where we'd be
# incompatible with Windows otherwise.
_fspath_seps: str = (os.sep + os.altsep) if os.altsep else os.sep

# Initialize module constants and search path
def _init_module():
    global BIN_DIR, CUR_DIR, ETC_DIR, LIB_DIR, LOG_DIR, REL_DIR, SCH_DIR
    global LOG_LEVELS, PROG_NAME

    # sys.argv[0] won't always be absolute
    _script = os.path.abspath(sys.argv[0])
    _bindir = os.path.dirname(_script)
    _reldir = os.path.dirname(_bindir)
    _libdir = os.path.join(_reldir, 'lib')

    BIN_DIR = _bindir
    CUR_DIR = os.getcwd()
    ETC_DIR = os.path.join(_reldir, 'etc')
    LIB_DIR = _libdir
    LOG_DIR = os.path.join(_reldir, 'log')
    REL_DIR = _reldir
    SCH_DIR = os.path.join(_reldir, 'schema')
    PROG_NAME = os.path.basename(_script)

    LOG_LEVELS = {
        'ALL':      logging.NOTSET,
        'DEBUG':    logging.DEBUG,
        'INFO':     logging.INFO,
        'WARNING':  logging.WARNING,
        'ERROR':    logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'NONE': -1
    }
    if os.path.isdir(_libdir) and os.access(_libdir, (os.R_OK|os.X_OK)):
        _sp = sys.path
        # see if it was already set via command line or $PYTHONPATH
        for _d in _sp:
            # There can be nonexistent paths in _sp, which will raise
            # an error from os.path.samefile
            if os.path.exists(_d) and os.path.samefile(_d, _libdir):
                return
        # _sp[0] *should* be BIN_DIR
        _sp0 = _sp[0]
        if os.path.exists(_sp0) and os.path.samefile(_sp0, _bindir):
            # insert our lib immediately after it
            _sp.insert(1, _libdir)
        else:
            # not expected, so play it safe
            _sp.append(_libdir)

# Execute on module load then discard - don't want or need it in memory.
_init_module()
del _init_module
