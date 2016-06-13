# -*- coding: utf-8 -*-
# © 2014 OpenERP SA
# © 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Multi Website Theme",
    "summary": "Build and manage multiple Websites themes",
    "version": "8.0.1.0.0",
    "category": "Website",
    "website": "http://www.tecnativa.com",
    "author": "OpenERP SA, "
              "Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "website"
    ],
    "installable": True,
    "data": [
        "data/data.xml",
        "security/ir.model.access.csv",
        "views/res_config.xml",
        "views/website_views.xml",
        "views/website_templates.xml",
    ],
    "demo": [
        "demo/website.xml",
        "demo/template.xml",
    ],
}
