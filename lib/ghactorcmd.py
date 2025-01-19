#  =======================================================================
#
#  Copyright (c) 2024-2025 Workday, Inc.
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

import scr

from cmd import CommandDispatcher
from ghactor import GitHubActors

class GitHubActorCmds(GitHubActors, CommandDispatcher):

    # ===================================================================
    # Commands
    # ===================================================================

    def teams(self) -> None:
        if scr.VERBOSE:
            # Print teams and their IDs
            for team, tid in self._team_ids().items():
                print(f"{team}\t{tid}")
        else:
            # Print only team names
            for team in self._teams():
                print(team)

    # ===================================================================
    # Internal Implementation
    # ===================================================================

    def __init__(self):
        super().__init__()

# Command help text
CommandDispatcher._cmd_help['teams'] = (
    '[-v] [-t {@<file> | <team>[,<team>,...]}', [
        ("Prints all configured team names or, if no teams list is"
         + " configured, all of the teams in the project."),
        "The '-v' flag causes team IDs to be printed along with team names."
    ])
