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

from cmd import CommandDispatcher, CommandError
from ghrepo import GitHubRepos

class GitHubRepoCmds(GitHubRepos, CommandDispatcher):

    # ===================================================================
    # Commands
    # ===================================================================

    def branches(self) -> None:
        repos = self._repos()
        if len(repos) != 1:
            raise CommandError(f"specify exactly one repo")
        for branch in self._branches(repos[0]):
            print(branch)

    def branch_urls(self) -> None:
        orgurl = f"https://github.com/{self._org}"
        for repo in self._repos():
            if branches := self._branches(repo):
                treeurl = f"{orgurl}/{repo}/tree/"
                for branch in branches:
                    print(treeurl + branch)

    def forks(self) -> None:
        for repo in self._repos():
            up, dn = self._forks(repo)
            print(repo + ':')
            print(f"  parent: {up}")
            if dn:
                if len(dn) == 1:
                    print("  forks:  " + dn[0])
                else:
                    print("  forks:")
                    for fk in sorted(dn, key=str.casefold):
                        print(f"    {fk}")
            else:
                print("  forks:  None")

    def repos(self) -> None:
        for repo in self._repos():
            print(repo)

    # ===================================================================
    # Internal
    # ===================================================================

    def __init__(self):
        super().__init__()

# Command help text
CommandDispatcher._cmd_help['branches'] = (
    '-r <repo>  [-t {all | <team>,...}]', [
        ("Prints the names of the repo's branches that are prefixed with the"
         + " specified team name(s). If no teams are specified, the teams"
         + " returned by the 'teams' command are used to construct the filter."
         + " The special team 'all' turns off filtering and prints all branch"
         + " names in the repo.")
    ])
CommandDispatcher._cmd_help['branch-urls'] = (
    '[-r {@<file> | <repo>[,<repo>,...]}] [-t {all | <team>,...}]', [
        ("For each specified or configured repository, prints the URLs of each"
         + " repo's branches that are prefixed with the specified team name(s)."
         + " If no teams are specified, the teams returned by the 'teams'"
         + " command are used to construct the filter."
         + " The special team 'all' turns off filtering and prints all branch"
         + " names in the repo(s).")
    ])
CommandDispatcher._cmd_help['forks'] = (
    '[-r {@<file> | <repo>[,<repo>,...]}]', [
        ("For each specified or configured repository, prints the names of"
         + " the repo's parent (upstream) repository if it is a fork, and the"
         + " names of its child (downstream) forks.")
    ])
CommandDispatcher._cmd_help['repos'] = (
    '[-r {@<file> | <repo>[,<repo>,...]}]', [
        ("Prints the specified or all configured repository names or, if no"
         + " repository list is specified or configured, all of the"
         + " repositories in the project.")
    ])
