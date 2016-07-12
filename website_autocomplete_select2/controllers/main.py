# -*- coding: utf-8 -*-
# © 2016 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import simplejson
from openerp.addons.web import http
from openerp.addons.web.http import request


class WebsiteAutoccompleteFieldSelect2(http.Controller):

    @http.route(
        '/website/autocomplete/<string:model_name>',
        type='http', auth="user", methods=['GET'], website=True)
    def get_request_data(
            self, q='', l=25, t='texttext', model_name='', **post):
        data = request.env[model_name].sudo().search_read(
            domain=[('name', 'ilike', (q or ''))],
            fields=['id', 'name'],
            limit=int(l),
        )
        return simplejson.dumps(data)
