# -*- coding: utf-8 -*-
# © 2014 OpenERP SA
# © 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

import werkzeug

from openerp.addons.web import http
from openerp.http import request
from openerp.addons.website.controllers.main import Website

import logging
_logger = logging.getLogger(__name__)


class WebsiteMultiTheme(Website):

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        _logger.info('WebsiteMultiTheme::index')
        main_menu = request.website.menu_id
        first_menu = main_menu.child_id and main_menu.child_id[0]
        if first_menu:
            _logger.info('WebsiteMultiTheme::index: first_menu url = %s', first_menu.url)
            if not (first_menu.url.startswith(('/page/', '/?', '/#')) or
                    (first_menu.url == '/')):
                return request.redirect(first_menu.url)
            if first_menu.url.startswith('/page/'):
                return request.env['ir.http'].reroute(first_menu.url)
        return super(WebsiteMultiTheme, self).index(**kw)

    @http.route('/website/add/<path:path>',
                type='http', auth="user", website=True)
    def pagenew(self, path, noredirect=False, add_menu=None):
        xml_id = request.env['website'].new_page(path)
        if add_menu:
            request.env['website.menu'].create({
                'name': path,
                'url': '/page/' + xml_id,
                'parent_id': request.website.menu_id.id,
                'website_id': request.website.id
            })
        # Reverse action in order to allow shortcut for /page/<website_xml_id>
        url = "/page/" + re.sub(r"^website\.", '', xml_id)
        if noredirect:
            return werkzeug.wrappers.Response(url, mimetype='text/plain')
        return werkzeug.utils.redirect(url)
