# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Savoir-faire Linux (<http://www.savoirfairelinux.com>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tests import common
from openerp.osv import orm


URL = 'http://localhost:3000'
REST_KEY = '39730056c1df6fb97b4fa5b9eb4bd37221ca1223'


class test_import_time_entries(common.TransactionCase):
    """
    This test will work with a Redmine server running on local host
    and the following records in its database:

    A custom field on project:
        - name: contract_ref_field

    a user:
        - login: user_1

    first project:
        - contract_ref_field: 'abcd'

    second project:
        - contract_ref_field: 'efgh'

    4 time entries for the user:
        project    date         hours
        abcd      '2014-01-01'  10
        efgh      '2014-01-02'  8
        abcd      '2014-01-04'  5
        abcd      '2014-01-07'  15

    Other projects, users, time entries to check that only these 4 time entries
    will be imported to the Odoo timesheet

    To run the tests, you will need to change the URL and the REST API key
    on the top of the file.
    """
    def setUp(self):
        super(test_import_time_entries, self).setUp()
        self.backend_model = self.registry('redmine.backend')
        self.user_model = self.registry("res.users")
        self.employee_model = self.registry('hr.employee')
        self.timesheet_model = self.registry('hr_timesheet_sheet.sheet')
        self.account_model = self.registry('account.analytic.account')
        self.context = self.user_model.context_get(self.cr, self.uid)
        cr, uid, context = self.cr, self.uid, self.context

        self.user_id = self.user_model.create(
            cr, uid, {
                'name': 'User 1',
                'login': 'user_1',
            }, context=context)

        journal_id = self.registry('ir.model.data').get_object_reference(
            cr, uid, 'hr_timesheet', 'analytic_journal')[1]

        self.account_id = self.account_model.create(cr, uid, {
            'type': 'contract',
            'name': 'Test Redmine',
            'code': 'abcd',
        }, context=context)

        self.account_2_id = self.account_model.create(cr, uid, {
            'type': 'contract',
            'name': 'Test Redmine',
            'code': 'efgh',
        }, context=context)

        self.employee_id = self.employee_model.create(
            cr, uid, {
                'name': 'Employee 1',
                'user_id': self.user_id,
                'journal_id': journal_id,
            }, context=context)

        self.timesheet_id = self.timesheet_model.create(
            cr, uid, {
                'employee_id': self.employee_id,
                'date_from': '2015-01-01',
                'date_to': '2015-01-07',
            }, context=context)

        self.timesheet_2_id = self.timesheet_model.create(
            cr, uid, {
                'employee_id': self.employee_id,
                'date_from': '2014-01-01',
                'date_to': '2014-01-07',
            }, context=context)

        backend_id = self.backend_model.create(cr, uid, {
            'name': 'redmine_test',
            'location': URL,
            'key': REST_KEY,
            'version': '1.3',
            'contract_ref': 'contract_ref_field',
        }, context=context)

        self.backend = self.backend_model.browse(
            cr, uid, backend_id, context=context)

    def test_get_user(self):
        cr, uid, context = self.cr, self.uid, self.context

        odoo_user = self.user_model.browse(
            cr, uid, self.user_id, context=context)
        redmine_user = self.backend.getUser(odoo_user.login)

        self.assertEqual(redmine_user.login, odoo_user.login)

    def test_get_user_not_existing(self):
        self.assertRaises(
            orm.except_orm, self.backend.getUser, 'user_not_exists')

    def test_no_time_entries_found(self):
        self.assertRaises(
            orm.except_orm, self.backend.getTimeEntries, self.timesheet_2_id)

    def test_import_time_entries(self):
        time_entries = self.backend.getTimeEntries(self.timesheet_id)
        number_of_hours = sum(entry.hours for entry in time_entries)
        self.assertEqual(number_of_hours, 38)

    def validate_timesheets(self):
        cr, uid, context = self.cr, self.uid, self.context

        timesheets = self.timesheet_model.browse(
            cr, uid, self.timesheet_id, context=context).timesheet_ids

        self.assertEqual(len(timesheets), 4)

        timesheets.sort(key=lambda t: t.date)

        self.assertEqual(timesheets[0].date, '2015-01-01')
        self.assertEqual(timesheets[1].date, '2015-01-02')
        self.assertEqual(timesheets[2].date, '2015-01-04')
        self.assertEqual(timesheets[3].date, '2015-01-07')

        self.assertEqual(timesheets[0].unit_amount, 10)
        self.assertEqual(timesheets[1].unit_amount, 8)
        self.assertEqual(timesheets[2].unit_amount, 5)
        self.assertEqual(timesheets[3].unit_amount, 15)

        self.assertEqual(timesheets[0].account_id.id, self.account_id)
        self.assertEqual(timesheets[1].account_id.id, self.account_2_id)
        self.assertEqual(timesheets[2].account_id.id, self.account_id)
        self.assertEqual(timesheets[3].account_id.id, self.account_id)

    def test_map_time_entries(self):
        time_entries = self.backend.getTimeEntries(self.timesheet_id)
        self.backend.mapTimeEntries(time_entries, self.timesheet_id)

        self.validate_timesheets()

    def test_import_from_redmine(self):
        cr, uid, context = self.cr, self.uid, self.context

        sheet = self.timesheet_model.browse(
            cr, uid, self.timesheet_id, context=context)

        sheet.import_from_redmine()
        self.validate_timesheets()

        sheet.import_from_redmine()
        self.validate_timesheets()
