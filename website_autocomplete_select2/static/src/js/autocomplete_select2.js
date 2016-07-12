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
    selector: ".js_autocomplete_select2",
    start: function (editable_mode) {
        if (editable_mode) {
            return;
        };
        this.$field = this.$el.find(".js_autocomplete_select2 input");
        this.bind_events();
    },
    bind_events: function(){
        var this_ = this;
        return this.autocomplete_many2one(this.$field);
    },
    autocomplete_many2one: function($field){
        $field.select2({
            tokenSeparators: [",", " ", "_"],
            maximumInputLength: 35,
            minimumInputLength: 3,
            maximumSelectionSize: 5,
            formatResult: function(term) {
                if (term.isNew) {
                    return '<span class="label label-primary">New</span> ' + _.escape(term.text);
                }
                else {
                    return _.escape(term.text);
                }
            },
            ajax: {
                url: function (){
                    return '/website/autocomplete/' + this.$field.data('model');
                },
                dataType: 'json',
                data: function(term, page) {
                    return {
                        q: term,
                        t: 'select2',
                        l: 50
                    };
                },
                results: function(data, page) {
                    var ret = [];
                    _.each(data, function(x) {
                        ret.push({ id: x.id, text: x.name, isNew: false });
                    });
                    return { results: ret };
                }
            },
            initSelection: function (element, callback) {
                callback({id: element.data('id'), text: element.data('text')});
            },
        });
    },
});

return animation.registry.website_autocomplete_select2;
});
