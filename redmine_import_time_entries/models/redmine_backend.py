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

from openerp.osv import orm, fields
from openerp.tools.translate import _
from redmine import exceptions


class redmine_backend(orm.Model):
    _inherit = 'redmine.backend'

    _columns = {
        'contract_ref': fields.char(
            'Contract # field name',
            help="The field in Redmine used to relate a project in Redmine "
            "to a project in Odoo. Each redmine project must have a unique "
            "value for this attribute."
        ),
    }

    def get_analytic_account_id(
        self, cr, uid, ids, project, redmine, context=None
    ):
        """
        Get the Odoo analytic account related to a Redmine project.
        :param project: Redmine project
        :return: Analytic account id
        """
        account_model = self.pool['account.analytic.account']

        backend = self.browse(cr, uid, ids[0], context=context)
        custom_field = backend.contract_ref

        project = redmine.project.get(project.id)

        ref = next((
            field.value for field in project.custom_fields
            if field.name == custom_field), False)

        if not ref:
            raise orm.except_orm(
                _('Error'),
                _('The field %s is not set in Redmine for project %s ') %
                (custom_field, project.name))

        account_ids = account_model.search(cr, uid, [
            ('type', '=', 'contract'),
            ('code', '=', ref),
        ], context=context)

        if not account_ids:
            raise orm.except_orm(
                _('Error'),
                _('No analytic account found for the Redmine project '
                    '%s - %s') % (ref, project.name))

        return account_ids[0]

    def check_contract_ref(self, cr, uid, ids, context=None):
        """
        Check if the contract_ref field exists in redmine
        """
        if context is None:
            context = self.pool['res.users'].context_get(cr, uid)
        redmine = self._auth(cr, uid, ids, context=context)
        res = self.read(
            cr, uid, ids, [
                'contract_ref',
            ], context=context
        )[0]
        contract_ref = res['contract_ref']

        try:
            projects = redmine.project.all()
            exist = False

            for cs in projects[0].custom_fields:
                if cs.__getattr__('name') == contract_ref:
                    exist = True

            if exist is True:
                raise orm.except_orm(_('Connection test succeeded!'),
                                     _('Everything seems properly set up!'))
            else:
                raise orm.except_orm(
                    _('Redmine backend configuration error!'),
                    _("The contract # field name doesn't exist.")
                )

        except exceptions.ResourceError:
            raise orm.except_orm(_('Redmine connection Error!'),
                                 _('Unsupported Redmine resource exception.'))
        except exceptions.ResourceNotFoundError:
            raise orm.except_orm(_('Redmine connection Error!'),
                                 _("Requested resource doesn't exist."))

    def getTimeEntries(self, cr, uid, ids, timesheet_sheet_id, context=None):
        """
        Get all redmine time entries related to a given odoo timesheet
        """
        backend = self.browse(cr, uid, ids[0], context=context)

        timesheet = self.pool['hr_timesheet_sheet.sheet'].browse(
            cr, uid, timesheet_sheet_id, context=context)

        employee = timesheet.employee_id

        if not employee.user_id:
            raise orm.except_orm(
                _('Error'),
                _('No user defined for employee %s') % employee.name)

        redmine = self._auth(cr, uid, ids, context=context)

        redmine_user = backend.getUser(
            login=employee.user_id.login, redmine=redmine)

        filters = {
            'user_id': redmine_user.id,
            'from_date': timesheet.date_from,
            'to_date': timesheet.date_to,
        }

        time_entries = redmine.time_entry.filter(**filters)

        if not time_entries:
            filters['employee'] = employee.name
            raise orm.except_orm(
                _('Warning'),
                _('No time entries found for employee %(employee)s '
                    'in the period from %(from_date)s to %(to_date)s.') %
                filters)

        return time_entries

    def mapTimeEntries(
        self, cr, uid, ids, time_entries, timesheet_sheet_id, context=None
    ):
        """
        Map Redmine time entries to odoo timesheet records
        """
        backend = self.browse(cr, uid, ids[0], context=context)
        redmine = self._auth(cr, uid, ids, context=context)
        timesheet = self.pool['hr_timesheet_sheet.sheet'].browse(
            cr, uid, timesheet_sheet_id, context=context)

        ts_record_model = self.pool['hr.analytic.timesheet']

        employee = timesheet.employee_id

        project_mapping = {}

        ts_defaults = {
            'user_id': employee.user_id.id,
            'journal_id': employee.journal_id.id,
            'imported_from_redmine': True,
        }

        for entry in time_entries:

            entry_fields = dir(entry)
            issue = 'issue' in entry_fields and redmine.issue.get(
                entry.issue.id)

            entry_name = backend.name

            if issue:
                entry_name += ' Issue #%s - %s' % (issue.id, issue.subject)

            project = entry.project
            if project.id not in project_mapping:
                project_mapping[project.id] = backend.get_analytic_account_id(
                    project, redmine)

            ts_defaults.update({
                'date': entry.spent_on,
                'name': entry_name,
                'account_id': project_mapping[project.id],
                'unit_amount': entry.hours,
            })

            ts_record_model.create(cr, uid, ts_defaults, context=context)
