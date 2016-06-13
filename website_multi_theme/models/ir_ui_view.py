# -*- coding: utf-8 -*-
# © 2014 OpenERP SA
# © 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree

from openerp import models, fields, api, _
from openerp.tools import ormcache, ormcache_context

import logging
_logger = logging.getLogger(__name__)


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    website_id = fields.Many2one(
        string="Website", comodel_name='website',
        ondelete='cascade', copy=False)
    key = fields.Char(string="Key")

    _sql_constraints = [
        ('key_website_id_unique', 'unique(key, website_id)',
         _('Key must be unique per website.')),
    ]

    @api.model
    def _view_obj(self, id_or_xml_id):
        if isinstance(id_or_xml_id, basestring):
            try:
                return self.env['ir.model.data'].xmlid_to_object(
                    id_or_xml_id, raise_if_not_found=True)
            except:
                # Try to fallback on key instead of xml_id
                website_id = self.env.context.get('website_id', False)
                ids = self.search([
                    ('key', '=', id_or_xml_id),
                    ('website_id', '=', website_id),
                ])
                if not ids:
                    ids = self.search([('key', '=', id_or_xml_id)])
                if not ids:
                    raise
        elif isinstance(id_or_xml_id, (int, long)):
            return self.browse(id_or_xml_id)
        # assume it's already a view object (WTF?)
        return id_or_xml_id

    @ormcache_context(accepted_keys=('website_id',))
    def get_view_id(self, cr, uid, xml_id, context=None):
        _logger.info('IrUiView::get_view_id: xml_id = %s', xml_id)
        if (context and 'website_id' in context and
                not isinstance(xml_id, (int, long))):
            domain = [
                ('key', '=', xml_id),
                '|',
                ('website_id', '=', context['website_id']),
                ('website_id', '=', False)
            ]
            xml_ids = self.search(cr, uid, domain, order='website_id',
                                  limit=1, context=context)
            if not xml_ids:
                xml_id = self.pool['ir.model.data'].xmlid_to_res_id(
                    cr, uid, xml_id, raise_if_not_found=True)
                page = self.read(
                    cr, uid, xml_id, ['page'], context=context)['page']
                if page:
                    raise ValueError('Invalid template id: %r' % (xml_id,))
            else:
                xml_id = xml_ids[0]
        else:
            xml_id = self.pool['ir.model.data'].xmlid_to_res_id(
                cr, uid, xml_id, raise_if_not_found=True)
        _logger.info('IrUiView::get_view_id: res = %s', xml_id)
        return xml_id

    _read_template_cache = dict(accepted_keys=(
        'lang', 'inherit_branding', 'editable', 'translatable', 'website_id'
    ))

    @ormcache_context(**_read_template_cache)
    def _read_template(self, cr, uid, view_id, context=None):
        arch = self.read_combined(
            cr, uid, view_id, fields=['arch'], context=context)['arch']
        arch_tree = etree.fromstring(arch)

        if 'lang' in context:
            arch_tree = self.translate_qweb(
                cr, uid, view_id, arch_tree, context['lang'], context)

        self.distribute_branding(arch_tree)
        root = etree.Element('templates')
        root.append(arch_tree)
        arch = etree.tostring(root, encoding='utf-8', xml_declaration=True)
        return arch

    @ormcache(size=0)
    def read_template(self, cr, uid, xml_id, context=None):
        _logger.info('IrUiView::read_template: xml_id = %s', xml_id)
        if isinstance(xml_id, (int, long)):
            view_id = xml_id
        else:
            if '.' not in xml_id:
                raise ValueError('Invalid template id: %r' % (xml_id,))
            view_id = self.get_view_id(cr, uid, xml_id, context=context)
        return self._read_template(cr, uid, view_id, context=context)

    def clear_cache(self):
        self._read_template.clear_cache(self)
        self.get_view_id.clear_cache(self)

    @api.model
    def get_inheriting_views_arch(self, view_id, model):
        _logger.info('IrUiView::get_inheriting_views_arch: view_id = %s, model = %s', view_id, model)
        arch = super(IrUiView, self).get_inheriting_views_arch(view_id, model)
        if not self.env.context.get('website_id'):
            return arch
        website_id = self.env.context['website_id']
        view_ids = [v for _, v in arch]
        view_arch_to_add = {}
        keep = []
        for view_rec in self.sudo().browse(view_ids):
            # Case 1: there is no key, always keep the view
            if not view_rec.key:
                keep.append(view_rec.id)
            # Case 2: Correct website
            elif view_rec.website_id.id == website_id:
                view_arch_to_add[view_rec.key] = (
                    view_rec.website_id.id, view_rec.id)
            # Case 3: no website add it if no website
            if not view_rec.website_id:
                view_web_id, view_id = view_arch_to_add.get(
                    view_rec.key, (False, False))
                if not view_web_id:
                    view_arch_to_add[view_rec.key] = (False, view_rec.id)
                # else: do nothing, you already have the right view
            # Case 4: website is wrong: do nothing
        # Put all the view_id we keep together
        keep.extend([vid for _, vid in view_arch_to_add.values()])
        return [(xml, vid) for xml, vid in arch if vid in keep]
