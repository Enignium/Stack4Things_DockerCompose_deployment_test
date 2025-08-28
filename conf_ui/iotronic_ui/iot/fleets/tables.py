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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables

from openstack_dashboard import api

LOG = logging.getLogger(__name__)


class CreateFleetLink(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Fleet")
    url = "horizon:iot:fleets:create"
    classes = ("ajax-modal",)
    icon = "plus"
    # policy_rules = (("iot", "iot:create_fleet"),)


class EditFleetLink(tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit")
    url = "horizon:iot:fleets:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    # policy_rules = (("iot", "iot:update_fleet"),)


class DeleteFleetsAction(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Fleet",
            u"Delete Fleets",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Fleet",
            u"Deleted Fleets",
            count
        )
    # policy_rules = (("iot", "iot:delete_fleet"),)

    def delete(self, request, fleet_id):
        api.iotronic.fleet_delete(request, fleet_id)


class FleetFilterAction(tables.FilterAction):

    def filter(self, table, fleets, filter_string):
        # Naive case-insensitive search.
        q = filter_string.lower()
        return [fleet for fleet in fleets
                if q in fleet.name.lower()]


class FleetsTable(tables.DataTable):
    name = tables.WrappingColumn('name', link="horizon:iot:fleets:detail",
                                 verbose_name=_('Fleet Name'))
    description = tables.Column('description', verbose_name=_('Description'))

    # Overriding get_object_id method because in IoT fleet the "id" is
    # identified by the field UUID
    def get_object_id(self, datum):
        return datum.uuid

    class Meta(object):
        name = "fleets"
        verbose_name = _("fleets")
        row_actions = (EditFleetLink, DeleteFleetsAction)
        table_actions = (FleetFilterAction, CreateFleetLink,
                         DeleteFleetsAction)



class StartOnBoard(tables.LinkAction):
    name = "start_on_board"
    verbose_name = _("Start Plugin")
    classes = ("ajax-modal",)
    action_type = "more"

    def get_link_url(self, datum):
        kwargs = self.table.request.resolver_match.kwargs
        fleet_id = kwargs.get('fleet_id')
        plugin_id = kwargs.get('plugin_id')
        board_uuid = datum.get('board_uuid') or datum.get('uuid')
        return reverse('horizon:iot:fleets:plugin_start_on_board',
                       args=(fleet_id, plugin_id, board_uuid))

class StopOnBoard(tables.LinkAction):
    name = "stop_on_board"
    verbose_name = _("Stop Plugin")
    action_type = "more"
    classes = ("ajax-modal",)

    def get_link_url(self, datum):
        kwargs = self.table.request.resolver_match.kwargs
        fleet_id = kwargs.get('fleet_id')
        plugin_id = kwargs.get('plugin_id')
        board_uuid = datum.get('board_uuid') or datum.get('uuid')
        return reverse('horizon:iot:fleets:plugin_stop_on_board',
                       args=(fleet_id, plugin_id, board_uuid))

class RemoveFromBoard(tables.LinkAction):
    name = "remove_from_board"
    verbose_name = _("Remove Plugin")
    action_type = "more"
    classes = ("ajax-modal",)

    def get_link_url(self, datum):
        kwargs = self.table.request.resolver_match.kwargs
        fleet_id = kwargs.get('fleet_id')
        plugin_id = kwargs.get('plugin_id')
        board_uuid = datum.get('board_uuid') or datum.get('uuid')
        return reverse('horizon:iot:fleets:plugin_remove_from_board',
                       args=(fleet_id, plugin_id, board_uuid))

def _get_bool(datum, key):
    """Legge un booleano da dict/oggetto."""
    if isinstance(datum, dict):
        return bool(datum.get(key, False))
    return bool(getattr(datum, key, False))


def _scope_label(datum):
    """Rende 'Board/Fleet' / 'Board' / 'Fleet' / 'Nessuna'."""
    in_board = _get_bool(datum, 'plugin_in_board')
    in_fleet = _get_bool(datum, 'plugin_in_fleet')
    if in_board and in_fleet:
        return _("Board/Fleet")
    if in_board:
        return _("Board")
    if in_fleet:
        return _("Fleet")
    return _("Nessuna")


class ReinjectOnBoard(tables.LinkAction):
    name = "reinject_on_board"
    verbose_name = _("Re-Inject Plugin")
    action_type = "more"
    classes = ("ajax-modal",)

    def get_link_url(self, datum):
        kwargs = self.table.request.resolver_match.kwargs
        fleet_id = kwargs.get('fleet_id')
        plugin_id = kwargs.get('plugin_id')
        board_uuid = datum.get('board_uuid') or datum.get('uuid')
        return reverse('horizon:iot:fleets:plugin_reinject_on_board',
                       args=(fleet_id, plugin_id, board_uuid))
    
class PluginStatusOnFleetTable(tables.DataTable):
    board_name = tables.Column('board_name', verbose_name=_('Board'))
    board_status = tables.Column('board_status', verbose_name=_('Board state'))
    plugin_status = tables.Column('plugin_status', verbose_name=_('Plugin state'))
    scope = tables.Column(_scope_label, verbose_name=_('Injected on'))
    message = tables.Column('message', verbose_name=_('Note'), empty_value='-')


    def get_object_id(self, datum):
        if isinstance(datum, dict):
            return datum.get('board_uuid') or datum.get('uuid') or datum.get('id') or datum.get('board_name') or str(datum)
        return getattr(datum, 'board_uuid', None) or getattr(datum, 'uuid', None) or getattr(datum, 'id', None) or getattr(datum, 'board_name', None) or str(datum)

    class Meta(object):
        name = "plugin_status"
        verbose_name = _("Plugin status on fleet")
        row_actions = (StartOnBoard, StopOnBoard, ReinjectOnBoard, RemoveFromBoard)
        #row_actions_verbose_name = _("Actions")

