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

import ghrule
import json
import scr
import sys

from cmd import CommandDispatcher, CommandError
from gh import JSON, NameIds
from ghrule import GitHubRules, Rule, Rules
from jsoncmd import JsonCommand
from scr import Name

from typing import Sequence, TextIO, Union

class GitHubRuleCmds(GitHubRules, CommandDispatcher, JsonCommand):

    # ===================================================================
    # Commands
    # ===================================================================

    def get_repo_rules(self) -> None:
        map_actors: bool = self._map_actors
        for repo in self._repos():
            if rules := self._repo_rules(repo):
                if out_file := self._json:
                    with open(out_file, 'wt') as fd:
                        self._print_rules(
                            rules, map_actors=map_actors, stream=fd)
                else:
                    self._print_rules(rules, map_actors=map_actors)
            else:
                print(f"{self._org}/{repo}: no rules")

    def set_default_rules(self) -> None:
        rules: Rules = self._default_repo_rules()
        proj = self._org
        for repo in self._repos():
            rname= f"{proj}/{repo}"
            print(f"{rname} ...")
            rpath: str = f"/repos/{rname}/rulesets"
            existing: NameIds = self._repo_rule_ids(repo)
            for rule in rules:
                if rid := existing.get(rule['name']):
                    # Update
                    path = f"{rpath}/{rid}"
                    self._send(path, 'PUT', rule)
                else:
                    # Create
                    self._send(rpath, 'POST', rule, ok=(201,))

    def set_repo_rules(self) -> None:
        if not (file := self._json):
            raise CommandError("missing JSON file specification")
        jsin: list[JSON]
        with open(file, 'rt') as fd:
            jsin = json.load(fd)
        jsok: list[JSON] = [self._sanitized_rule(r) for r in jsin]
        proj_nocase = self._org.casefold()
        target_repos: set[Name] = set()
        target_rules: dict[Name, list[JSON]] = {}
        # GH doesn't want the source info, but we want the repos
        for rec in jsok:
            if rec.pop('source_type') != 'Repository':
                # Only other type is 'Organization', and we don't have them
                continue
            source = rec['source']
            fields = source.split('/')
            if len(fields) != 2 or fields[0].casefold() != proj_nocase:
                # Not ours???
                raise CommandError(f"invalid source repo: '{source}'")
            repo = fields[1]
            target_repos.add(repo)
            if recs := target_rules.get(repo):
                recs.append(rec)
            else:
                target_rules[repo] = [rec]
        target_repos: Sequence[Name] = tuple(target_repos)
        # Proj/Repo => rules
        existing: dict[Name, list[Rule]] = {}
        for repo in target_repos:
            existing[repo] = self._repo_rules(repo)
        for repo, recs in target_rules.items():
            xrecs: list[Rule] = existing[repo]
            for rec in recs:
                source = rec.pop('source')
                if not (rid := rec.pop('id', None)):
                    name = rec['name']
                    for xrec in xrecs:
                        if xrec['name'] == name:
                            rid = xrec['id']
                            break
                if rid:
                    # Update - on success, we're done with this one
                    path = f"/repos/{source}/rulesets/{rid}"
                    self._send(path, 'PUT', rec)
                else:
                    # Create - on success, add it to the existing ones in
                    # case there's a duplicate in the file
                    path = f"/repos/{source}/rulesets"
                    res = self._send(path, 'POST', rec, ok=(201,))
                    jsout = json.load(res)
                    # populate missing fields
                    for key in 'id', 'source', 'source_type':
                        rec[key] = jsout[key]
                    xrecs.append(rec)

    # ===================================================================
    # Internal
    # ===================================================================

    def _print_rules(self,
            rules: Rules, map_actors: bool = False,
            stream: TextIO = sys.stdout) -> None:
        rule_keys: tuple[str, ...] = \
            ghrule._all_rule_keys if scr.VERBOSE \
            else ghrule._get_rule_keys
        s = self._cur_indent()
        stream.write(f'{s}[')
        self._inc_indent()
        prv = False
        for rule in rules:
            if prv:
                stream.write(',')
            else:
                prv = True
            self._print_rule(rule, rule_keys, stream, map_actors)
        s = self._dec_indent()
        stream.write(f'\n{s}]\n')

    def _print_rule(self,
            rule: Rule, rule_keys: Sequence[str],
            stream: TextIO, map_actors: bool = False) -> None:
        s = self._cur_indent()
        stream.write(f"\n{s}{{")
        s = self._inc_indent()
        prv: bool = False
        for key, val in scr.dict_with(rule, rule_keys).items():
            if prv:
                stream.write(',')
            else:
                prv = True
            if key == 'bypass_actors':
                self._print_rule_actors(key, val, stream, map_actors)
            elif key == 'conditions':
                self._print_rule_cond(key, val, stream)
            elif key == 'rules':
                self._print_rule_rules(key, val, stream)
            elif key == '_links':
                val = val['html']['href']
                stream.write(f'\n{s}"url": "{val}"')
            else:
                # val is a simple value
                if isinstance(val, str):
                    val = '"' + val + '"'
                stream.write(f'\n{s}"{key}": {val}')
        s = self._dec_indent()
        stream.write(f'\n{s}}}')

    def _print_rule_actors(self,
            key: str, vals: list[dict[str, Union[int, str]]],
            stream: TextIO, map_actors: bool) -> None:
        if not map_actors:
            # Unless actors are being mapped behavior is same as for a 'rule'
            return self._print_rule_rules(key, vals, stream)
        team_id_names = self._team_ni_cache()[1]
        s = self._cur_indent()
        stream.write(f'\n{s}"{key}": [')
        s = self._inc_indent()
        prv: bool = False
        for val in vals:
            if prv:
                stream.write(',')
            else:
                prv = True
            if val['actor_type'] == 'Team':
                team = team_id_names[val['actor_id']]
                val['actor_name'] = team
                val = dict(sorted(val.items()))
            stream.write(f'\n{s}')
            json.dump(val, stream)
        s = self._dec_indent()
        stream.write(f'\n{s}]')

    def _print_rule_cond(self,
            key: str, val: dict[str, dict[str, list[str]]],
            stream: TextIO) -> None:
        s = self._cur_indent()
        stream.write(f'\n{s}"{key}": {{')
        s = self._inc_indent()
        p1: bool = False
        for k1, v1 in val.items():
            if p1:
                stream.write(',')
            else:
                p1 = True
            # v1 should be a dict
            stream.write(f'\n{s}"{k1}": {{')
            s = self._inc_indent()
            p2: bool = False
            for k2, v2 in v1.items():
                if p2:
                    stream.write(',')
                else:
                    p2 = True
                # v2 is a list
                if v2:
                    stream.write(f'\n{s}"{k2}": [')
                    s = self._inc_indent()
                    p3: bool = False
                    for v3 in v2:
                        if p3:
                            stream.write(',')
                        else:
                            p3 = True
                        stream.write(f'\n{s}"{v3}"')
                    s = self._dec_indent()
                    stream.write(f'\n{s}]')
                else:
                    stream.write(f'\n{s}"{k2}": {v2}')
            s = self._dec_indent()
            stream.write(f'\n{s}}}')
        s = self._dec_indent()
        stream.write(f'\n{s}}}')

    def _print_rule_rules(self,
            key: str, vals: list[dict[str, Union[int, str]]],
            stream: TextIO) -> None:
        s = self._cur_indent()
        stream.write(f'\n{s}"{key}": [')
        s = self._inc_indent()
        prv: bool = False
        for val in vals:
            if prv:
                stream.write(',')
            else:
                prv = True
            stream.write(f'\n{s}')
            json.dump(val, stream)
        s = self._dec_indent()
        stream.write(f'\n{s}]')

    def __init__(self):
        super().__init__()

# Command help text
CommandDispatcher._cmd_help['get-repo-rules'] = (
    '[-m] [-v] [-j OutFile] [-r {@<file> | <repo>[,<repo>,...]}]', [
        "Prints JSON permission rules for the specified or configured repos.",
        "The '-j' option causes output to be written to the specified file.",
        "The '-m' flag causes actor IDs to be de-referenced into actor names.",
        ("The '-v' flag causes source and timestamp information to be"
         + " appended to the output."),
        ("NOTE: Use of the '-m' and/or '-v' flags results in JSON that is not"
         + " conformant with the GH schema and MAY NOT be accepted in a"
         + " subsequent external update operation as-is.")
    ])
CommandDispatcher._cmd_help['set-default-rules'] = (
    '[-r {@<file> | <repo>[,<repo>,...]}]', [
        ("Sets (or updates) default permission rules for the specified or"
         + " configured repos."),
        "The per-repo rules are defined in '<etc-dir>/default-rules.json'."
    ])
CommandDispatcher._cmd_help['set-repo-rules'] = (
    '-j JsonFile', [
        ("Sets permission rules from the specified input JSON file. Additions"
         + " to the input file made by the get-repo-rules '-m' and 'v' flags"
         + " are reverted before updating server rules.")
    ])
