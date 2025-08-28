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
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect

from horizon import exceptions, messages
from horizon import forms
# from horizon import messages
from horizon import tables
from horizon import tabs
from horizon.utils import memoized

from openstack_dashboard.api import iotronic
from openstack_dashboard import policy

from iotronic_ui.iot.fleets import forms as project_forms
from iotronic_ui.iot.fleets import tables as project_tables
from iotronic_ui.iot.fleets import tabs as project_tabs


LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = project_tables.FleetsTable
    template_name = 'iot/fleets/index.html'
    page_title = _("Fleets")

    def get_data(self):
        fleets = []

        # Admin
        if policy.check((("iot", "iot:list_all_fleets"),), self.request):
            try:
                fleets = iotronic.fleet_list(self.request, None)

            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve fleets list.'))

        # Admin_iot_project
        elif policy.check((("iot", "iot:list_project_fleets"),),
                          self.request):
            try:
                fleets = iotronic.fleet_list(self.request, None)

            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve user fleets list.'))

        # Other users
        else:
            try:
                fleets = iotronic.fleet_list(self.request, None)

            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve user fleets list.'))

        return fleets


class CreateView(forms.ModalFormView):
    template_name = 'iot/fleets/create.html'
    modal_header = _("Create Fleet")
    form_id = "create_fleet_form"
    form_class = project_forms.CreateFleetForm
    submit_label = _("Create Fleet")
    submit_url = reverse_lazy("horizon:iot:fleets:create")
    success_url = reverse_lazy('horizon:iot:fleets:index')
    page_title = _("Create Fleet")


class UpdateView(forms.ModalFormView):
    template_name = 'iot/fleets/update.html'
    modal_header = _("Update Fleet")
    form_id = "update_fleet_form"
    form_class = project_forms.UpdateFleetForm
    submit_label = _("Update Fleet")
    submit_url = "horizon:iot:fleets:update"
    success_url = reverse_lazy('horizon:iot:fleets:index')
    page_title = _("Update Fleet")

    @memoized.memoized_method
    def get_object(self):
        try:
            return iotronic.fleet_get(self.request,
                                        self.kwargs['fleet_id'],
                                        None)
        except Exception:
            redirect = reverse("horizon:iot:fleets:index")
            exceptions.handle(self.request,
                              _('Unable to get fleet information.'),
                              redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        args = (self.get_object().uuid,)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        fleet = self.get_object()

        return {'uuid': fleet.uuid,
                'name': fleet.name,
                'description': fleet.description}


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.FleetDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ fleet.name|default:fleet.uuid }}"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        fleet = self.get_data()
        context["fleet"] = fleet
        context["url"] = reverse(self.redirect_url)
        context["actions"] = self._get_actions(fleet)

        return context

    def _get_actions(self, fleet):
        table = project_tables.FleetsTable(self.request)
        return table.render_row_actions(fleet)

    @memoized.memoized_method
    def get_data(self):
        #fleet = []
        fleet = None
        fleet_boards = []
        fleet_plugins = []
        fleet_id = self.kwargs['fleet_id']

        print("FLEET DETAIL start: fleet_id = %s",fleet_id)

        try:
            fleet = iotronic.fleet_get(self.request, fleet_id, None)
            print("fleet_get OK: uuid=%s name=%s has_info=%s",
                      getattr(fleet, 'uuid', None),
                      getattr(fleet, 'name', None),
                      hasattr(fleet, '_info'))

            boards = iotronic.fleet_get_boards(self.request, fleet_id)
            print("fleet_get_boards OK: count=%d", len(boards))
            # LOG.debug('Boards: %s', boards)

            for board in boards:
                fleet_boards.append(board._info)
            if fleet_boards:
                print("fleet_boards[0] sample=%s", fleet_boards[0])

            injections = iotronic.plugins_on_fleet(self.request, fleet_id) or []
            print("plugins_on_fleet OK: type=%s count=%d sample=%s",
                      type(injections).__name__,
                      len(injections),
                      (injections[0] if injections else "[]"))

            for inj in injections:
                fleet_plugins.append(inj)


            pids = []
            for p in fleet_plugins:
                pid = (getattr(p, 'plugin_uuid', None) or getattr(p, 'uuid', None) or
                       (p.get('plugin_uuid') if isinstance(p, dict) else None) or
                       (p.get('uuid') if isinstance(p, dict) else None))
                pids.append(pid)
            print("plugin_ids detected=%s", pids)


            fleet._info.update(dict(boards=fleet_boards,
                                    plugins=fleet_plugins))

            # LOG.debug('FLEET COMPLETE: %s', fleet)
            print("FLEET DETAIL end: fleet_id=%s boards=%d plugins=%d",
                     fleet_id, len(fleet_boards), len(fleet_plugins))

        except Exception as e:
            print("FLEET DETAIL error for fleet_id=%s", fleet_id)
            msg = ('Unable to retrieve fleet %s information') % e
            exceptions.handle(self.request, msg, ignore=True)
        return fleet

    def get_tabs(self, request, *args, **kwargs):
        fleet = self.get_data()
        return self.tab_group_class(request, fleet=fleet, **kwargs)



def _plugin_id_from_injection(inj):
    # Estrae l'ID/UUID del plugin da una injection (dict o oggetto)
    if isinstance(inj, dict):
        p = inj.get('plugin')
        if isinstance(p, dict):
            return (p.get('uuid') or p.get('id') or
                    p.get('plugin_uuid') or p.get('plugin_id'))
        # injection "piatta": ha direttamente i campi plugin_*
        return (inj.get('plugin_uuid') or inj.get('plugin_id') or
                inj.get('uuid') or inj.get('id') or inj.get('plugin'))
    # oggetto
    p = getattr(inj, 'plugin', None)
    if isinstance(p, dict):
        return (p.get('uuid') or p.get('id') or
                p.get('plugin_uuid') or p.get('plugin_id'))
    return (getattr(inj, 'plugin_uuid', None) or getattr(inj, 'plugin_id', None) or
            getattr(inj, 'uuid', None) or getattr(inj, 'id', None) or
            getattr(p, 'uuid', None) or getattr(p, 'id', None))

def _get_board_uuid(board_obj):
    info = getattr(board_obj, '_info', None)
    if isinstance(info, dict):
        return (info.get('uuid') or info.get('id') or info.get('board_uuid'))
    # fallback
    return (getattr(board_obj, 'uuid', None) or getattr(board_obj, 'id', None))


def _normalize_board_state(info):
    # prova campi comuni
    raw = (info.get('status') or info.get('board_status') or '').strip()
    alive = info.get('alive')
    # se 'alive' è esplicitamente True/False, usalo come priorità
    if isinstance(alive, bool):
        return 'online' if alive else 'offline'

    s = raw.lower().replace('-', '')         # 'on-line' -> 'online'
    s = s.split('/')[0].strip()              # 'online/ready' -> 'online'

    if s in ('online', 'enabled', 'ready', 'active', 'up', 'connected'):
        return 'online'
    if s in ('offline', 'disabled', 'down'):
        return 'offline'
    return 'unknown' if not raw else raw


class PluginStatusOnFleetView(tables.DataTableView):
    table_class = project_tables.PluginStatusOnFleetTable
    template_name = 'iot/fleets/plugin_status.html'
    page_title = _("Plugin status on fleet")

    def get_data(self):
        request = self.request
        fleet_id = self.kwargs['fleet_id']
        plugin_id = self.kwargs['plugin_id']

        rows = []
        try:
            boards = iotronic.fleet_get_boards(request, fleet_id) or []

            finj = iotronic.plugins_on_fleet(request, fleet_id) or []
            fleet_plugin_ids = {str(_plugin_id_from_injection(inj)) for inj in finj if _plugin_id_from_injection(inj)}
            plugin_in_fleet = str(plugin_id) in fleet_plugin_ids

            for b in boards:
                info = getattr(b, '_info', {}) or {}
                board_uuid = _get_board_uuid(b)
                board_name = info.get('name') or info.get('board_name') or board_uuid

                # 🔧 ricarica lo stato live della board (evita info stantio)
                try:
                    b_live = iotronic.board_get(request, board_uuid)
                    info_live = getattr(b_live, '_info', {}) or {}
                    info.update(info_live)  # preferisci i campi freschi
                except Exception:
                    pass

                board_state = _normalize_board_state(info)

                in_board = False
                try:
                    binj = iotronic.plugins_on_board(request, board_uuid) or []
                    in_board = any(str(_plugin_id_from_injection(inj)) == str(plugin_id) for inj in binj)
                except Exception as e:
                    LOG.warning("plugins_on_board fallita per board %s: %s", board_uuid, e)

                present = (plugin_in_fleet or in_board)
                plugin_state = 'present' if present else 'absent'

                rows.append({
                    'board_uuid': board_uuid,
                    'board_name': board_name,
                    'board_status': board_state,
                    'plugin_status': plugin_state,
                    'plugin_in_board': in_board,
                    'plugin_in_fleet': plugin_in_fleet,
                    'message': ''
                })
        except Exception as e:
            exceptions.handle(request, _('Unable to load plugin status: %s') % e)

        return rows




class FleetDetailView(DetailView):
    redirect_url = 'horizon:iot:fleets:index'

    def _get_actions(self, fleet):
        table = project_tables.FleetsTable(self.request)
        return table.render_row_actions(fleet)





# ACTIONS

def _back_to_status(request, fleet_id, plugin_id):
    """Redirect helper to the plugin status page."""
    return redirect(reverse('horizon:iot:fleets:plugin_status_on_fleet',
                            args=(fleet_id, plugin_id)))

def plugin_start_on_board(request, fleet_id, plugin_id, board_uuid):
    """Start plugin on a single board, then go back to the status page."""
    try:
        # stessi nomi/firma usati nei form dei Plugin
        iotronic.plugin_action(request, board_uuid, plugin_id, "PluginStart", {})
        messages.success(request, _("Plugin started on board %s.") % board_uuid)
    except Exception as e:
        exceptions.handle(request, _("Unable to start plugin on board: %s") % e)
    return _back_to_status(request, fleet_id, plugin_id)

def plugin_stop_on_board(request, fleet_id, plugin_id, board_uuid):
    """Stop plugin on a single board, then go back to the status page."""
    try:
        iotronic.plugin_action(request, board_uuid, plugin_id, "PluginStop", {})
        messages.success(request, _("Plugin stopped on board %s.") % board_uuid)
    except Exception as e:
        exceptions.handle(request, _("Unable to stop plugin on board: %s") % e)
    return _back_to_status(request, fleet_id, plugin_id)

def plugin_remove_from_board(request, fleet_id, plugin_id, board_uuid):
    """Remove plugin from a single board, then go back to the status page."""
    try:
        iotronic.plugin_remove(request, board_uuid, plugin_id)
        messages.success(request, _("Plugin removed from board %s.") % board_uuid)
    except Exception as e:
        exceptions.handle(request, _("Unable to remove plugin from board: %s") % e)
    return _back_to_status(request, fleet_id, plugin_id)

def plugin_reinject_on_board(request, fleet_id, plugin_id, board_uuid):
    """Re-inject plugin on a single board, then go back to the status page."""
    try:
        iotronic.plugin_inject(request, board_uuid, plugin_id, False) 
        messages.success(request, _("Plugin re-injected on board %s.") % board_uuid)
    except Exception as e:
        exceptions.handle(request, _("Unable to re-inject plugin on board: %s") % e)
    return _back_to_status(request, fleet_id, plugin_id)
