# -*- coding: utf-8 -*-
# © 2014 OpenERP SA
# © 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models
from openerp.addons.web.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _auth_method_public(self):
        res = super(IrHttp, self)._auth_method_public()
        if not request.session.uid:
            website = request.env['website'].get_current_website()
            if website:
                request.uid = website.user_id.id
        return res
