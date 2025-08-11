# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

# from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import tabs
from openstack_dashboard.api import iotronic
from horizon import tables
from iotronic_ui.iot.fleets import tables as fleet_tables

LOG = logging.getLogger(__name__)


class OverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "overview"
    template_name = ("iot/fleets/_detail_overview.html")

    def get_context_data(self, request):
        fleet = self.tab_group.kwargs['fleet']


        boards = fleet._info.get('boards', [])
        if not boards:
            try:
                board_objs = iotronic.fleet_get_boards(request, fleet.uuid)
                boards = [b._info for b in board_objs]
                fleet._info['boards'] = boards
            except Exception as e:
                LOG.warning("Unable to load boards for fleet %s: %s", fleet.uuid, e)
                boards = []


        plugins = fleet._info.get('plugins', [])
        if not plugins:
            try:
                plugin_objs = iotronic.plugins_on_fleet(request, fleet.uuid)
                plugins = plugin_objs
                fleet._info['plugins'] = plugins
            except Exception as e:
                LOG.warning("Unable to load plugins for fleet %s: %s", fleet.uuid, e)
                plugins = []

        return {
            "fleet": fleet,
            "boards": boards,
            "plugins": plugins,
            "is_superuser": request.user.is_superuser
        }



class FleetDetailTabs(tabs.TabGroup):
    slug = "fleet_details"
    # tabs = (OverviewTab, LogTab, ConsoleTab, AuditTab)
    tabs = (OverviewTab,)
    sticky = True
