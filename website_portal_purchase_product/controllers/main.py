# -*- coding: utf-8 -*-
# (c) 2015 Antiun Ingeniería S.L. - Sergio Teruel
# (c) 2015 Antiun Ingeniería S.L. - Carlos Dauden
# © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
from contextlib import contextmanager
from werkzeug.datastructures import CombinedMultiDict, FileStorage
from werkzeug.exceptions import Forbidden
from openerp import _
from openerp.http import local_redirect, request, route
from openerp.addons.website_portal_purchase.controllers.main import (
    PortalPurchaseWebsiteAccount,
)
from openerp.addons.website_form.controllers.main import WebsiteForm
from ..exceptions import FormSaveError


class ProductPortalPurchaseWebsiteAccount(PortalPurchaseWebsiteAccount):
    def _purchase_product_domain(self, query=None):
        """Domain to find products or product templates.

        :param str query:
            Text filter applied by the user.
        """
        domain = [
            ("seller_ids.name", "child_of",
             request.env.user.commercial_partner_id.ids),
        ]
        if query:
            terms = query.split()
            if terms:
                for term in terms:
                    domain += [
                        "|",
                        ("name", "ilike", term),
                        ("description_sale", "ilike", term)
                    ]
        return domain

    def _purchase_product_create(self, post):
        """Create a new product.

        :param CombinedMultiDict post:
            Values as they came from the form.

        :return (product, errors):
            Tuple with product ORM record and errors as they come out from
            :meth:`~._purchase_product_update`.
        """
        product = request.env["product.template"]
        product.check_access_rights("create")

        # Create product as admin
        product = product.sudo().create({
            "name": ",".join(post.get("name")) or False,
        })

        # Continue edition as supplier user
        seller = request.env["product.supplierinfo"].create({
            "product_tmpl_id": product.id,
            "name": request.env.user.commercial_partner_id.id,
        })
        product = seller.product_tmpl_id
        errors = self._purchase_product_update(product, post)

        return product, errors

    def _purchase_product_update(self, product, post):
        """Update the product with the received form values.

        :param product.template product:
            Product record to update.

        :param CombinedMultiDict post:
            Values as they came from the form.

        :return dict:
            Mapping of form::

                {
                    'field_name': {
                        'human': 'human-readable field name',
                        'errors': [
                            'Error message',
                            ...
                        ],
                    },
                    ...
                }
        """
        errors = dict()
        supplierinfo_found = dict()
        SupplierInfo = request.env["product.supplierinfo"]
        required = self._purchase_product_required_fields()
        ignored = self._purchase_product_ignored_fields()
        ignored_if_empty = self._purchase_product_ignored_if_empty_fields()

        # Fill in false boolean fields
        for form_field in self._purchase_product_bool_fields():
            post.setdefault(form_field, "")

        try:
            with request.env.cr.savepoint():
                for form_field, value in post.iteritems():
                    if form_field in ignored:
                        continue

                    try:
                        # Support multiselect fields
                        value = ",".join(value)
                    except TypeError:
                        # Support file fields
                        # TODO Add multi images support
                        value = value[0]

                    if not value and form_field in ignored_if_empty:
                        continue

                    # Select the right supplierinfo record
                    if form_field.startswith("supplierinfo_"):
                        id_, db_field = form_field.split("_", 2)[1:]
                        id_ = int(id_)
                        try:
                            record = supplierinfo_found[id_]
                        except KeyError:
                            record = False
                            if id_:
                                record = SupplierInfo.browse(id_).exists()
                            if not record:
                                record = SupplierInfo.search(
                                    [("product_tmpl_id", "=", product.id),
                                     ("name", "=",
                                      request.env.user
                                      .commercial_partner_id.id)],
                                    limit=1,
                                )
                            supplierinfo_found[id_] = record

                    # Select the product record
                    else:
                        record, db_field = product, form_field

                    # Required fields cannot be empty
                    if form_field in required:
                        required.discard(form_field)
                        if not value:
                            self._purchase_product_add_error(
                                errors, product, form_field, db_field,
                                _("Required field"))
                            continue

                    # Try to save the converted received value
                    try:
                        with request.env.cr.savepoint():
                            self._set_field(record, db_field, value)

                    # If it fails, log the error
                    except Exception as error:
                        self._purchase_product_add_error(
                            errors, record, form_field, db_field,
                            ": ".join(a or "" for a in error.args))

                # No more required fields should remain now
                for form_field in required:
                    self._purchase_product_add_error(
                        errors, product, form_field, form_field,
                        _("Required field"))

                # Rollback if there were errors
                if errors:
                    raise FormSaveError()

        # This is just to force rollback to first savepoint
        except FormSaveError:
            pass

        return errors

    def _purchase_product_bool_fields(self):
        """Booleans get a default value of False if not received."""
        return set()

    def _purchase_product_ignored_fields(self):
        """These fields will be ignored when recieving form data."""
        return set()

    def _purchase_product_ignored_if_empty_fields(self):
        """These fields will be ignored if they are found with no value."""
        return {"image"}

    def _purchase_product_required_fields(self):
        """These fields must be filled."""
        return {"name", "type", "price"}

    def _purchase_product_add_error(self, errors, record, form_field, db_field,
                                    message):
        """Save an error while processing the form.

        :param dict errors:
            Errors dict to be modified.

        :param models.Model record:
            Will extract the human-readable field name from this record.

        :param str form_field:
            Name of the field in the form that produced the error.

        :param str db_field:
            Name of the field in the :param:`record`.

        :param str message:
            Error message.

        :return dict:
            Returns the modified :param:`errors` dict.
        """
        if form_field not in errors:
            try:
                human = (record._fields[db_field]
                         .get_description(request.env)["string"])
            except KeyError:
                human = db_field

            errors[form_field] = {
                "human": human,
                "errors": list(),
            }
        errors[form_field]["errors"].append(message)
        return errors

    def _set_field(self, record, field_name, value):
        """Set a field's value."""
        if value == "":
            value = False
        else:
            website_form = WebsiteForm()
            converter = website_form._input_filters[
                record._fields[field_name].get_description(request.env)
                ["type"]]
            value = converter(website_form, field_name, value)
        record[field_name] = value

    @route(["/my/purchase/products",
            "/my/purchase/products/page/<int:page>"],
           type='http', auth="user", website=True)
    def portal_my_purchase_products(self, page=1, date_begin=None,
                                    date_end=None, search=None, **post):
        values = self._prepare_portal_layout_values()
        url = "/my/purchase/products"
        ProductTemplate = request.env["product.template"].with_context(
            pricelist=request.website.get_current_pricelist().id)
        domain = self._purchase_product_domain(search)
        archive_groups = self._get_archive_groups(
            ProductTemplate._name, domain)
        if date_begin and date_end:
            domain += [("create_date", ">=", date_begin),
                       ("create_date", "<", date_end)]

        # Make pager
        count = ProductTemplate.search_count(domain)
        url_args = post.copy()
        url_args.update({
            "date_begin": date_begin,
            "date_end": date_end,
            "search": search,
        })
        pager = request.website.pager(
            url=url,
            url_args=url_args,
            total=count,
            page=page,
            step=self._items_per_page,
        )

        # Sarch the count to display, according to the pager data
        products = ProductTemplate.search(
            domain, limit=self._items_per_page, offset=pager["offset"])

        values.update({
            "archive_groups": archive_groups,
            "date": date_begin,
            "default_url": url,
            "pager": pager,
            "products": products,
            "search": search,
        })

        return request.render(
            "website_portal_purchase_product.portal_my_products", values)

    def _get_supplierinfo(self, product):
        return request.env['product.supplierinfo'].search([
            ('id', 'in', product.seller_ids.ids),
            ('name', 'child_of', request.env.user.commercial_partner_id.ids),
        ])

    @route(
        ['/my/purchase/products/<model("product.template"):product>',
         '/my/purchase/products/new'],
        type='http', auth="user", website=True)
    def my_purchase_product_form(self, product=None, **kwargs):
        """Display a form to edit or create a product.

        :param "new"/product.template prodcut:
            Product we are editing. If the user has no access, this will
            automatically raise a ``403 Forbidden`` error.
        """
        # Only show forms for those that can edit or create their products
        if product:
            product.check_access_rule("write")
        else:
            product = request.env["product.template"]
            product.check_access_rights("create")

        values = self._prepare_portal_layout_values()
        view = "website_portal_purchase_product.products_followup"

        # Edit mode, get POST data as multidict
        kwargs.pop("debug", None)
        if kwargs:
            post = CombinedMultiDict((
                request.httprequest.files,
                request.httprequest.values)).to_dict(False)
            post.pop("csrf_token", None)
            post.pop("debug", None)

            # Create or edit product
            try:
                with request.env.cr.savepoint():
                    values["product"], values["errors"] = (
                        (product, self._purchase_product_update(product, post))
                        if product else self._purchase_product_create(post))
                    values["supplierinfo_ids"] = self._get_supplierinfo(
                        product)

                    ok = not values["errors"]

                    # Redirect to the new product URL
                    if ok and not product:
                        return local_redirect(
                            "/my/purchase/products/{}".format(
                                values["product"].id))

                    # The edited form, if there were no errors
                    result = request.render(view, values, ok)
                    if ok:
                        return result

                    # Rollback product edition or creation
                    raise FormSaveError()

            except FormSaveError:
                # Form was rendered, transaction was rolled back, so return it
                return result

        values.update({
            "product": product or product.new(),
            "supplierinfo_ids": self._get_supplierinfo(product),
            "errors": dict(),
        })
        return request.render(view, values)

    @route(
        ["/my/purchase/products/<model('product.template'):product>/disable"],
        type="http", auth="user", website=True)
    def my_purchase_product_disable(self, product,
                                    redirect="/my/purchase/products"):
        """This product will disappear from the supplier's panel.

        They will think it was deleted, but it was just disabled.
        """
        product = product.sudo()
        product.website_published = product.active = False
        return local_redirect(redirect)

    @route()
    def account(self):
        """Display product count in account summary for suppliers."""
        response = super(ProductPortalPurchaseWebsiteAccount, self).account()
        if "supplier_order_count" in response.qcontext:
            response.qcontext["supplier_product_count"] = (
                request.env['product.template']
                .search_count(self._purchase_product_domain()))
        return response
