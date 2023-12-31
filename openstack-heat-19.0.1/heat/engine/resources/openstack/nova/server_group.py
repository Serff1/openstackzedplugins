#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from heat.common import exception
from heat.common.i18n import _
from heat.engine import constraints
from heat.engine import properties
from heat.engine import resource
from heat.engine import support

NOVA_MICROVERSIONS = (MICROVERSION_SOFT_POLICIES, MICROVERSION_RULE) = ('2.15',
                                                                        '2.64')


class ServerGroup(resource.Resource):
    """A resource for managing a Nova server group.

    Server groups allow you to make sure instances (VM/VPS) are on the same
    hypervisor host or on a different one.
    """

    support_status = support.SupportStatus(version='2014.2')

    default_client_name = 'nova'

    entity = 'server_groups'

    PROPERTIES = (
        NAME, POLICIES, RULES
    ) = (
        'name', 'policies', 'rules'
    )

    _RULES = (MAX_SERVER_PER_HOST) = ('max_server_per_host')

    properties_schema = {
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('Server Group name.')
        ),
        POLICIES: properties.Schema(
            properties.Schema.LIST,
            _('A list of exactly one policy to apply. '
              'Defaults to anti-affinity.'),
            default=['anti-affinity'],
            constraints=[
                constraints.AllowedValues(["anti-affinity", "affinity",
                                           "soft-anti-affinity",
                                           "soft-affinity"])
            ],
            schema=properties.Schema(
                properties.Schema.STRING,
            ),
        ),
        RULES: properties.Schema(
            properties.Schema.MAP,
            _('Rules for a policy.'),
            schema={
                MAX_SERVER_PER_HOST: properties.Schema(
                    properties.Schema.NUMBER,
                    _('Maximum servers in a group on a given host. '
                      'Rule for anti-affinity policy.')
                )
            },
            support_status=support.SupportStatus(version='17.0.0'),
        ),
    }

    def validate(self):
        super(ServerGroup, self).validate()
        policies = self.properties[self.POLICIES]
        is_supported = self.client_plugin().is_version_supported(
            MICROVERSION_SOFT_POLICIES)
        if (('soft-affinity' in policies or
             'soft-anti-affinity' in policies) and not is_supported):
            msg = _('Required microversion for soft policies not supported.')
            raise exception.StackValidationFailed(message=msg)

        if self.properties[self.RULES]:
            is_supported = self.client_plugin().is_version_supported(
                MICROVERSION_RULE)
            if not is_supported:
                msg = _('Required microversion for rules not supported.')
                raise exception.StackValidationFailed(message=msg)

    def handle_create(self):
        name = self.physical_resource_name()
        policies = self.properties[self.POLICIES]
        rules = self.properties[self.RULES]
        rules_supported = self.client_plugin().is_version_supported(
            MICROVERSION_RULE)
        if rules_supported:
            server_group = self.client().server_groups.create(
                name=name, policy=policies[0], rules=rules)
        else:
            server_group = self.client().server_groups.create(
                name=name, policies=policies)
        self.resource_id_set(server_group.id)

    def needs_replace_failed(self):
        if not self.resource_id:
            return True

        with self.client_plugin().ignore_not_found:
            self._show_resource()
            return False

        return True

    def physical_resource_name(self):
        name = self.properties[self.NAME]
        if name:
            return name
        return super(ServerGroup, self).physical_resource_name()


def resource_mapping():
    return {'OS::Nova::ServerGroup': ServerGroup}
