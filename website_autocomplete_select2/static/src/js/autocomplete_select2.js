/* © 2015 Tecnativa, S.L.
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
 */

"use strict";
odoo.define("website_autocomplete_select2.loader",
function(require){

var animation = require("web_editor.snippets.animation");
var $ = require("$");

animation.registry.website_autocomplete_select2 =
animation.Class.extend({
    selector: ".o_autocomplete_fields",
    start: function (editable_mode) {
        if (editable_mode) {
            return;
        };
        this.$min_qty_input = this.$el.find("#min_qty_delivery_free");
        this.bind_events();
    },
    bind_events: function () {
        var this_ = this;
        this.$el.on("change", "input[type='radio']", function (event) {
            return this_.change_input(event);
        });
    },
    change_input: function(ev){
        if (this.$el.find("input[value=min_qty_free]:radio").is(":checked")) {
            this.$min_qty_input.removeClass('hidden');
        } else {
            this.$min_qty_input.addClass('hidden');
        };
    },
});

return animation.registry.website_autocomplete_select2;
});
