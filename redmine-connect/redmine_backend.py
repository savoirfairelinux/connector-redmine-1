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
from redmine import Redmine, exceptions


class redmine_backend(orm.Model):
    _name = 'redmine.backend'
    _description = 'Redmine Backend'
    _inherit = 'connector.backend'
    _backend_type = 'redmine'

    _columns = {
        'location': fields.char(
            'Location',
            size=128,
            required=True,
        ),
        'key': fields.char(
            'Key',
            size=64,
            required=True,
        ),
        'contract_ref': fields.char(
            'Contract #',
            size=64,
        ),
    }

    _sql_constraints = [(
        'redmine_backend_contract_unique',
        'unique(contract_ref)',
        _('Contract # must be unique')
    )]

    def _auth(self, cr, uid, ids, context=None):
        """ Test connection with Redmine """
        if context is None:
            context = self.pool['res.users'].context_get(cr, uid)
        # Get the location, user and password or key for Redmine
        if not ids:
            raise orm.except_orm(
                _('Internal Error'),
                _('_auth() called without any ids.')
            )
        if type(ids) is not list:
            ids = [ids]
        res = self.read(
            cr, uid, ids, [
                'location',
                'key',
            ], context=context
        )[0]
        location = res['location']
        key = res['key']
        # version = res['version']
        # impersonate = res['impersonate']

        try:
            client = Redmine(
                location,
                key=key,
            )
        except exceptions.AuthError:
            raise orm.except_orm(_('Redmine connection Error!'),
                                 _('Invalid authentications key.'))
        except exceptions.ServerError:
            raise orm.except_orm(_('Redmine connection Error!'),
                                 _('Redmine internal error.'))
        except exceptions.UnknownError:
            raise orm.except_orm(_('Redmine connection Error!'),
                                 _('Redmine returned an unknown error.'))

        return client
