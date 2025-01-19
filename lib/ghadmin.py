#  =======================================================================
#
#  Copyright (c) 2022-2025 Workday, Inc.
#
#  This file is provided to you under the Apache License,
#  Version 2.0 (the "License"); you may not use this file
#  except in compliance with the License.  You may obtain
#  a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#
#  =======================================================================
#
# Support for admin script(s).
#
# Very much work-in-progress, you almost certainly have to get into the code
# to add the functionality you want.
#

import argparse
import gh
import json
import os
import pprint
import scr
import sys

from cmd import CommandDispatcher
from ghactorcmd import GitHubActorCmds
from ghrepocmd import GitHubRepoCmds
from ghrulecmd import GitHubRuleCmds
from scr import Config

from typing import NoReturn, Optional

class GhAdminCmds(GitHubActorCmds, GitHubRepoCmds, GitHubRuleCmds):
    def __init__(self):
        super().__init__()

# ===================================================================
# Internal
# ===================================================================

# Name sequences to cache that can be either a file or list from config
_cache_seqs: tuple[str, ...] = ('repos', 'teams')

# Config values to cache as-is
_cache_asis: tuple[str, ...] = ('indent', 'json', 'map_actors')

_cfg_schema: scr.FsPath = 'gh-admin.config.schema.json'

# ===================================================================
# Main
# ===================================================================

def main() -> NoReturn:
    try:
        conf: Config = _init_config()
        cmd = conf['cmd']
        if cmd == 'dump-config':
            pprint.pprint(conf)
        else:
            scr.CONFIG = conf
            gh = GhAdminCmds()
            gh.dispatch(cmd, conf['args'])
    except Exception as exc:
        scr.exc_exit(exc)

def _init_config() -> Config:
    defaults: Config = _schema_defaults()
    args: Config = _parse_config(defaults)
    # Set these first so they're in effect for all remaining processing.
    scr.DEBUG = args['debug']
    scr.VERBOSE = (scr.DEBUG or args['verbose'])
    # Load the specified or default config file.
    conf_json: Optional[str] = None
    if cf := args['conf']:
        # if specified it's been confirmed to exist
        conf_json = scr.read_file(cf)
    else:
        # default paths may not exist
        cf = defaults['config']
        for cf in os.path.join(scr.CUR_DIR, cf), os.path.join(scr.ETC_DIR, cf):
            if os.path.isfile(cf):
                if scr.DEBUG:
                    print(f"Loading config from '{cf}'", file=sys.stderr)
                conf_json = scr.read_file(cf)
                break
    conf = json.loads(conf_json) if conf_json else {}
    # Next setup etc redirection, if any, so scr.resolve_conf_path() works.
    # This can only come from a config file, not the command line args.
    if etc := conf.get('etc-dir'):
        scr.ETC_DIR = scr.ReadableDir(etc)
        if scr.DEBUG:
            print(f"Using alternate etc dir: '{scr.ETC_DIR}'", file=sys.stderr)
    # Set up logging with command-line level, if specified.
    if ll := args.get('log'):
        conf['log-level'] = ll
    scr.init_log(
        conf.get('log-level', defaults['log-level']),
        conf.get('log-dir'), conf.get('log-name'))
    # There MUST be a credentials file, whether specified or default.
    if not (af := args['auth']):
        if not (af := conf.pop('creds', None)):
            af = defaults['creds']
    conf['auth'] = gh.read_auth_token(scr.resolve_conf_path(af))
    # Always present.
    conf['cmd'] = args['cmd']
    conf['args'] = args['args']
    # One last default.
    if not (proj := conf.pop('project', None)):
        proj = defaults['project']
    scr.PROJ_NAME = proj
    # Remaining command-line args and overrides
    for name in (_cache_asis + _cache_seqs):
        if val := args.get(name, None):
            conf[name] = val
    return conf

def _parse_config(defaults: Config) -> Config:
    p: argparse.ArgumentParser = argparse.ArgumentParser(
        description='Administer GitHub repositories',
        epilog=CommandDispatcher.cmd_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        'cmd', metavar='command',
        help='Command to execute.')
    p.add_argument(
        'args', metavar='param', nargs='*',
        help='Command parameter(s).')
    s = os.path.join(scr.SCH_DIR, _cfg_schema)
    c = scr.CUR_DIR
    l = len(c)
    if os.path.commonpath((s, c)) == c:
        s = '.' + s[l:]
    e = scr.ETC_DIR
    if os.path.commonpath((e, c)) == c:
        e = '.' + e[l:]
    c = defaults['config']
    p.add_argument(
        '-c', '--conf', metavar='File', type=scr.ReadableFile,
        help=f"""Config file to read, conforming to schema '{s}'.
        Some options are only available with a config file.
        Default: './{c}' or '{os.path.join(e, c)}'""")
    p.add_argument(
        '-a', '--auth', metavar='File', type=scr.ReadableFile,
        help=f"Credentials file to read. Default: {defaults['creds']}")
    s = [l.lower() for l in scr.LOG_LEVELS.keys()]
    p.add_argument(
        '-l', '--level', metavar='Lvl', choices=s,
        help=f"""Log level, one of [{', '.join(s)}].
        Default: {defaults['log-level'].lower()}""")
    p.add_argument(
        '-d', '--debug', action='store_true',
        help="""Print some additional info from certain operations.
        On exception print stack trace. Debug output is always to stderr, so
        it doesn't interfere with stdout redirection.
        Note that this does NOT force any change in --level.
        Implies --verbose.""")
    p.add_argument(
        '-r', '--repos', metavar='...', type=scr.NamesListOrFile,
        help="""Specify one or more repos explicitly, overriding config file
        or defaults.
        If the argument is prefixed with '@' the value following the prefix
        must refer to an existing readable file, which is read and parsed as
        if its contents were entered on the command line as a quoted string.
        The parameter value is parsed as a comma-or-whitespace-delimited list
        of repo names, de-duplicated after parsing.""")
    p.add_argument(
        '-t', '--teams', metavar='...', type=scr.NamesListOrFile,
        help="""Specify one or more teams explicitly, overriding config file
        or defaults.
        If the argument is prefixed with '@' the value following the prefix
        must refer to an existing readable file, which is read and parsed as
        if its contents were entered on the command line as a quoted string.
        The parameter value is parsed as a comma-or-whitespace-delimited list
        of team names, de-duplicated after parsing.""")
    indent  = defaults['indent']
    indmin = defaults['min_indent']
    indmax = defaults['max_indent']
    s = f"{indmin}-{indmax}"
    p.add_argument(
        '-i', '--indent', metavar=s, type=int,
        choices=range(indmin, indmax+1), default=indent,
        help=f"""Indent spaces for output, primarily JSON.
        Valid range is {s}. Default: {indent}""")
    p.add_argument(
        '-j', '--json', metavar='File', type=scr.PossibleFile,
        help='JSON file to read or write for commands recognizing it.')
    p.add_argument(
        '-m', '--map', dest='map_actors', action='store_true',
        help='Map numeric IDs to names for commands recognizing it.')
    p.add_argument(
        '-v', '--verbose', action='store_true',
        help="""Make certain operations more verbose.
        The effect of this flag varies by operation, refer to command help
        for details.""")
    return vars(p.parse_args())

def _schema_defaults() -> Config:
    schema = os.path.join(scr.SCH_DIR, _cfg_schema)
    with open(schema, 'rt') as fd:
        schema = json.load(fd)
    defaults = {'config': schema['default']}
    props = schema['properties']
    for name in 'creds', 'log-level', 'project':
        defaults[name] = props[name]['default']
    indent = props['indent']
    defaults['indent'] = indent['default']
    defaults['min_indent'] = indent['minimum']
    defaults['max_indent'] = indent['maximum']
    return defaults
