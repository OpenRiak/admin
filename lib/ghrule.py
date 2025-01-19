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

import json
import scr

from gh import JSON, NameIds, ObjID, Rule, Rules
from ghactor import GitHubActors
from ghrepo import GitHubRepos
from scr import Name

from typing import Union

# ===================================================================
# Type Aliases
# ===================================================================

class GitHubRules(GitHubRepos, GitHubActors):

    # ===================================================================
    # Operations
    # ===================================================================

    def _default_repo_rules(self) -> Rules:
        with open(scr.resolve_conf_path('{{etc}}/default-rules.json')) as fd:
            recs: list[JSON] = json.load(fd)
        rules: list[Rule] = []
        for rec in recs:
            rec.pop('comment', None)
            if rec:
                rules.append(self._unmap_rule_actors(rec))
        return rules

    def _repo_rule_ids(self, repo: Name) -> NameIds:
        return {r['name']: r['id'] for r in self._repo_rules(repo)}

    def _repo_rules(self, repo: Name) -> list[Rule]:
        path = f"/repos/{self._org}/{repo}/rulesets"
        rules: list[Rule] = []
        for rec in self._paged_recs(path):
            rp = f"{path}/{rec['id']}"
            res = self._recv(rp, 'GET')
            rules.append(json.load(res))
        return rules

    def _sanitized_rule(self, rule: Rule) -> Rule:
        return self._unmap_rule_actors(
                {k: rule[k] for k in _get_rule_keys})

    def _map_rule_actors(self, rule: Rule) -> Rule:
        # Add ID => name mappings in place
        actor: dict[str, Union[ObjID, Name]]
        for actor in rule['bypass_actors']:
            if 'actor_name' not in actor:
                actor['actor_name'] = self._actor_name(
                        actor['actor_id'], actor['actor_type'])
        return rule

    def _unmap_rule_actors(self, rule: Rule) -> Rule:
        # Filter/revert added ID => name mappings in place
        actor: dict[str, Union[ObjID, Name]]
        for actor in rule['bypass_actors']:
            if name := actor.pop('actor_name', None):
                if 'actor_id' not in actor:
                    actor['actor_id'] = \
                        self._actor_id(name, actor['actor_type'])
        return rule

    # ===================================================================
    # Internal
    # ===================================================================

    def __init__(self):
        super().__init__()

_req_rule_keys: tuple[str, ...] = (
    'name', 'enforcement', 'target', 'bypass_actors', 'conditions', 'rules')
_get_rule_keys: tuple[str, ...] = (
    'id', 'source', 'source_type') + _req_rule_keys
_all_rule_keys: tuple[str, ...] = _get_rule_keys + (
    'created_at', 'updated_at', '_links')
