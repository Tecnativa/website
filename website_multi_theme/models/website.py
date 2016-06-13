# -*- coding: utf-8 -*-
# © 2014 OpenERP SA
# © 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api
from openerp.addons.website.models.website import slugify
from openerp.addons.web.http import request
from werkzeug.exceptions import NotFound

import logging
_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = "website"

    def _default_user_id_get(self):
        return self.env['ir.model.data'].sudo().xmlid_to_res_id(
            'base.public_user')

    css_class = fields.Char(
        string="Body CSS class", readonly=True,
        compute="_compute_css_class")
    theme_id = fields.Many2one(string="Theme", comodel_name='website.theme')
    menu_id = fields.Many2one(
        string="Main Menu", comodel_name='website.menu', readonly=True,
        compute="_compute_menu_id")
    menu_ids = fields.One2many(
        string="Menus", comodel_name='website.menu', readonly=True,
        inverse_name='website_id')
    user_id = fields.Many2one(default=lambda self: self._default_user_id_get())

    @api.depends('menu_ids')
    def _compute_menu_id(self):
        for website in self:
            main_menu = website.menu_ids.filtered(
                lambda r: r.parent_id is False)
            website.menu_id = main_menu[0] if main_menu else False

    @api.depends('theme_id')
    def _compute_css_class(self):
        for website in self:
            website.css_class = website.theme_id.css_slug

    def _new_page_name(self, name):
        # completely arbitrary max_length
        return slugify(name, max_length=50)

    def _new_page_set(self, page, page_name, template, ispage=True):
        return page.write({
            'arch': page.arch.replace(template, page.key),
            'name': page_name,
            'page': ispage,
        })

    @api.model
    def new_page(self, name, template='website.default_page', ispage=True):
        # NOTE: This override brokes inherit chain
        template_module, template_name = template.split('.')
        page_name = self._new_page_name(name)
        page_xmlid = "%s.%s" % (template_module, page_name)
        try:
            # existing page
            self.env['ir.model.data'].xmlid_lookup(page_xmlid)
        except ValueError:
            # new page
            template_obj = self.env['ir.model.data'].xmlid_to_object(template)
            page = template_obj.copy({
                'website_id': self.env.context.get('website_id'),
                'key': page_xmlid
            })
            self._new_page_set(page, page_name, template, ispage=ispage)
            # Do not create External XML ID because there could be only one
            # page per website
        return page_xmlid

    @api.model
    def get_current_website(self):
        _logger.info('Website::get_current_website: self = %s', self)
        host = request.httprequest.environ.get('HTTP_HOST', '')
        domain_name = host.split(':')[0]
        website = self.sudo().search([('name', '=', domain_name)])
        if not website:
            website = self.sudo().search([], limit=1)
        request.context['website_id'] = website.id
        _logger.info('Website::get_current_website: website = %s', website)
        return website

    @api.multi
    def get_template(self, template):
        _logger.info('Website::get_template: template = %s', template)
        if not isinstance(template, (int, long)) and '.' not in template:
            template = 'website.%s' % template
        view_id = self.env['ir.ui.view'].get_view_id(template)
        if not view_id:
            _logger.info('Website::get_template: NotFound')
            raise NotFound
        _logger.info('Website::get_template: Found ID = %s', view_id)
        return self.env['ir.ui.view'].browse(view_id)
