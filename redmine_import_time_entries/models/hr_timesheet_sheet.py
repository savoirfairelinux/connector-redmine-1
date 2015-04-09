# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 - Present Savoir-faire Linux
#    (<http://www.savoirfairelinux.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm
from openerp.tools.translate import _


class hr_timesheet_sheet(orm.Model):
    _inherit = 'hr_timesheet_sheet.sheet'

    def import_from_redmine(self, cr, uid, ids, context=None):
        timesheet_model = self.pool['hr.analytic.timesheet']
        backend_obj = self.pool['redmine.backend']
        backend_ids = backend_obj.search(
            cr, uid, [('contract_ref', '!=', False)], context=context)
        if not backend_ids:
            raise orm.except_orm(
                _('Error'),
                _('The Redmine connector is either missing or not '
                    'configured to import timesheets.'))

        backend = backend_obj.browse(cr, uid, backend_ids[0], context=context)

        for sheet in self.browse(cr, uid, ids, context=context):

            if sheet.state in ['confirm', 'done']:
                raise orm.except_orm(
                    _('Error'),
                    _('You can not import time entries from Redmine in '
                        'a confirmed timesheet'))

            # Unlink previously imported timesheets
            to_unlink_ids = [
                ts.id for ts in sheet.timesheet_ids if ts.imported_from_redmine
            ]

            timesheet_model.unlink(cr, uid, to_unlink_ids, context=context)

            time_entries = backend.getTimeEntries(sheet.id)
            backend.mapTimeEntries(time_entries, sheet.id)
