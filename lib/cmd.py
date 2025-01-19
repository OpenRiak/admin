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

import keyword
import re
import scr
import shutil
import textwrap

# Type imports
from scr import CmdArgs, CmdName
from typing import Optional, Sequence

# ===================================================================
# Type Aliases
# ===================================================================

CmdLineHelp = str
"""
Command usage, single line, without preceeding command name.
"""

CmdHelpText = Sequence[str]
"""
Command help text, as (possibly multi-line) paragraphs.
Newlines and tabs are replaced with spaces and trailing whitespace is
stripped. Embedded spaces are `NOT` squashed, so do it yourself.
"""

CmdHelpMap  = dict[CmdName, tuple[CmdLineHelp, CmdHelpText]]

class CommandDispatcher:

    # ===================================================================
    # Command Support
    # ===================================================================

    def dispatch(self, cmd_name: CmdName, cmd_args: CmdArgs) -> None:
        """Command dispatcher."""
        fun_name = cmd_name.replace('-', '_')
        if fun_name == 'dispatch' or keyword.iskeyword(fun_name) or not \
                re.fullmatch(r'^[a-z]\w+$', fun_name, re.ASCII):
            raise CommandError(f"Illegal command '{cmd_name}'")
        inst_fun = getattr(self, fun_name, None)
        if not callable(inst_fun):
            raise CommandError(f"Invalid command '{cmd_name}'")
        if cmd_args:
            inst_fun(cmd_args)
        else:
            inst_fun()

    # undocumented, for testing pre-command processing only
    def no_op(self, args: Optional[CmdArgs] = None) -> None:
        if args:
            print(f"Invocation: no_op({args})")
        else:
            print("Invocation: no_op()")

    @staticmethod
    def cmd_help() -> str:
        cmd_map = CommandDispatcher._cmd_help
        wrapper = textwrap.TextWrapper(
            width=(shutil.get_terminal_size().columns - 2), expand_tabs=False,
            drop_whitespace=True, replace_whitespace=True,
            initial_indent='    ', subsequent_indent='    ',
            break_long_words=False, break_on_hyphens=False )
        text = ['\nCommands:\n']
        for cmd in sorted(cmd_map.keys()):
            usage, paras = cmd_map[cmd]
            text.append(f"  {cmd} {usage.strip()}")
            for para in paras:
                text.extend([ln for ln in wrapper.wrap(para)])
            text.append('')
        text.append('-')
        return '\n'.join(text)

    _cmd_help: CmdHelpMap = {}
    """
    Extending classes should add their commands' help to this map during
    module (not instance) initialization.
    """

    # ===================================================================
    # Initialization
    # ===================================================================

    def __init__(self):
        super().__init__()

class Indent:

    # ===================================================================
    # Indent Support
    # ===================================================================

    def _cur_indent(self) -> str:
        return self._spaces[:self._curind]

    def _inc_indent(self) -> str:
        i = self._indent
        c = self._curind + i
        s = self._spaces
        if len(s) < c:
            s += ' ' * (i * 4)
            self._spaces = s
        self._curind = c
        return s[:c]

    def _dec_indent(self) -> str:
        c = self._curind - self._indent
        self._curind = c
        return self._spaces[:c]

    # ===================================================================
    # Initialization
    # ===================================================================

    def __init__(self):
        """
        Consumes `int: CONFIG['indent']` if present.
        """
        super().__init__()
        indent: int = scr.CONFIG.get('indent', 2)
        self._indent: int = indent
        self._curind: int = 0
        self._spaces: str = ' ' * (indent * 4)

class CommandError(Exception):
    pass
