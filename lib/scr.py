# ===================================================================
#
# Copyright (c) 2022-2025 Workday, Inc.
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
# Shared common script support.
#

import logging
import os
import sys
import traceback

from typing import Mapping, NoReturn, Optional, Sequence, TypeVar, Union

# ===================================================================
# Common type aliases
# ===================================================================

CmdArgs = Sequence[str]
CmdName = str
ConfKey = str
ConfVal = Union[bool, int, str, CmdArgs]
Config  = Mapping[ConfKey, ConfVal]
FsPath  = str
MapKey  = TypeVar('MapKey')
MapVal  = TypeVar('MapVal')
Name    = str
Names   = Sequence[Name]
SemVer  = str
Vsn     = Sequence[int]

# ===================================================================
# Pseudo-constants
# Initialized at module load.
# ===================================================================

BIN_DIR:    FsPath
CUR_DIR:    FsPath
ETC_DIR:    FsPath
LIB_DIR:    FsPath
LOG_DIR:    FsPath
REL_DIR:    FsPath
SCH_DIR:    FsPath

PROG_NAME:  CmdName
PROJ_NAME:  CmdName

LOG_LEVELS: Mapping[str, int]

# Scripts are expected to initialize this before instantiating anything
# that might use it. Loading this module initializes it to None.
CONFIG:     Config

# These are initialized early, on the assumption that:
#   -d|--debug on the command-line indicates Debug mode.
#   -v|--verbose on the command-line indicates Verbose mode.
#   Debug mode always turns on Verbose mode.
# If VERBOSE:
#   Print some additional info from certain operations.
# If DEBUG:
#   Display stack traces on error.
DEBUG:      bool
VERBOSE:    bool

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

def conf_map() -> Mapping[str, str]:
    """
    Obtain a view of the current effective `'{{...}}'` pattern map.

    Notes:
      - This mapping can change at runtime, especially during configuration.
      - This is a relatively expensive operation, prefer `conf_val(key)`
        in most cases.
    :return: A view of the currently effective mappings.
    """
    g = globals()
    return {k: g[v] for k, v in _conf_map.items() if v in g}

def conf_val(key: str) -> str:
    """
    Obtain the value associated with `key` when `key` is in the current
    `{{...}}` substitution map (as returned by `conf_map()`).
    :param key: A currently assigned substitution key.
    :return: The value associated with `key`.
    :raises KeyError: Invalid substitution key `key`.
    :raises AttributeError: The value to which `key` maps has not yet been
        initialized.
    """
    if not (gkey := _conf_map.get(key)):
        raise KeyError(f"invalid configuration key '{key}'")
    if not (val := globals().get(gkey)):
        raise AttributeError(
            f"module '{__name__}' attribute '{gkey}' is not initialized")
    return val

def dict_with(
        src: Mapping[MapKey, MapVal], keys: Sequence[MapKey],
        keyorder: bool = True) -> dict[MapKey, MapVal]:
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
    if keyorder:
        return {k: src[k] for k in keys if k in src}
    else:
        return {k: v for k, v in src.items() if k in keys}

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

    Note that patterns are `ONLY` replaced at the beginning of `path`, and are
    `ALWAYS` followed by a filesystem path separator character.
    Use `resolve_conf_str(path)` to resolve embedded `'{{...}}'` patterns.

    See `conf_map()` for the currently supported keys.
    :param path: An absolute or relative filesystem path, possibly with a
        leading substitution pattern.
    :return: An absolute path.
    :raises ValueError: A `'{{'` pattern is not followed by `'}}'`.
    :raises KeyError: An unrecognized substitution `key` was encountered.
    :raises AttributeError: The value to which a recognized substitution `key`
        resolves has not yet been initialized.
    """
    if path.startswith('~'):
        path = os.path.expanduser(path)
    elif path.startswith('{{'):
        subend: int = path.index('}}')
        subkey: str = path[2:subend].strip().lower()
        repl: str = conf_val(subkey)
        tail: str = path[(subend + 2):]
        if tail[0] in _fspath_seps:
            path = repl + tail
        else:
            path = os.path.join(repl, tail)
    return os.path.abspath(path)

def resolve_conf_str(src: str) -> str:
    """
    Returns a string with '{{...}}' substitution patterns resolved.
    Nested patterns are `NOT` supported.

    See `conf_map()` for the currently supported keys.
    :param src: The string to resolve.
    :return: The string with substitution patterns resolved.
    :raise ValueError: A `'{{'` pattern is not followed by `'}}'`.
    :raise KeyError: An unrecognized substitution `key` was encountered.
    :raises AttributeError: The value to which a recognized substitution `key`
        resolves has not yet been initialized.
    """
    if not src or (pos := src.find('{{')) < 0:
        return src
    out = src[:pos]
    cur = src[(pos + 2):]
    while True:
        end = cur.index('}}')
        key = cur[:end].strip().lower()
        cur = cur[(end + 2):]
        out += conf_val(key)
        if (pos := cur.find('{{')) < 0:
            break
        out += cur[:pos]
        cur = cur[(pos + 2):]
    return out + cur

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

def exc_exit(exc: Exception) -> NoReturn:
    if DEBUG:
        si = sys.exc_info()
        traceback.print_exception(si[0], si[1], si[2])
    else:
        print(f"{exc.__class__.__name__}: {exc}")
    sys.exit(1)

def raise_param_error(msg: str, bad_type: bool = False) -> NoReturn:
    exc: Exception
    if DEBUG:
        exc = ParamTypeError(msg) if bad_type else ParamValueError(msg)
    else:
        exc = TypeError(msg) if bad_type else ValueError(msg)
    raise exc

class ParamTypeError(Exception):
    pass

class ParamValueError(Exception):
    pass

# ===================================================================
# Initialization
# ===================================================================

def init_log(level: str,
        logdir: Optional[str] = None, logname: Optional[str] = None) -> None:
    if (loglevel := LOG_LEVELS[level.upper()]) < 0:
        # disable
        logging.disable(0x7fffffff)
        return
    if logdir:
        logdir = resolve_conf_path(logdir)
        _conf_map['log'] = logdir
    else:
        logdir = conf_val('log')
    if not os.path.isdir(logdir):
        if os.path.exists(logdir):
            raise_param_error(f"not a directory: '{logdir}'")
        os.mkdir(logdir)
    if not os.access(logdir, (os.R_OK|os.W_OK|os.X_OK)):
        raise_param_error(f"insufficient directory permissions: '{logdir}'")
    if not logname:
        logname = conf_val('prog')
    logfile = os.path.join(logdir, logname + '.log')
    logging.basicConfig(
        filename=logfile, filemode='at',
        format='%(asctime)s %(levelname)-7s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=loglevel )

# ===================================================================
# Internal
# Module load initialization.
# ===================================================================

# Probably overkill, but this is the ONLY place where we'd be
# incompatible with Windows otherwise.
_fspath_seps: str

_conf_map: dict[str, str]

# Initialize module constants
def _init_module():
    global BIN_DIR, CUR_DIR, ETC_DIR, LIB_DIR, LOG_DIR, REL_DIR, SCH_DIR
    global _conf_map, _fspath_seps, CONFIG, LOG_LEVELS, PROG_NAME
    global DEBUG, VERBOSE

    argv = sys.argv
    DEBUG = ('-d' in argv or '--debug' in argv)
    if VERBOSE := (DEBUG or '-v' in argv or '--verbose' in argv):
        print('Using Python ' + vsn_to_semver(sys.version_info[:3]),
              file=sys.stderr)

    _fspath_seps = (os.sep + os.altsep) if os.altsep else os.sep

    # sys.argv[0] won't always be absolute
    _script = os.path.abspath(argv[0])
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

    # CONFIG *MUST* exist, even if the value is unusable
    CONFIG  = None

    _conf_map = {
        'bin':    'BIN_DIR',
        'cwd':    'CUR_DIR',
        'etc':    'ETC_DIR',
        'lib':    'LIB_DIR',
        'log':    'LOG_DIR',
        'rel':    'REL_DIR',
        'schema': 'SCH_DIR',
        'prog':   'PROG_NAME',
        'proj':   'PROJ_NAME'
    }
    LOG_LEVELS = {
        'ALL':      logging.NOTSET,
        'DEBUG':    logging.DEBUG,
        'INFO':     logging.INFO,
        'WARNING':  logging.WARNING,
        'ERROR':    logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'NONE':     -1
    }

# Execute on module load then discard. We don't want or need it in memory,
# and there's no reason to ever invoke it again.
_init_module()
del _init_module
