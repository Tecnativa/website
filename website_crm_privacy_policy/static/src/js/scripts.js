/**
 * Copyright 2014 Jorge Camacho <jcamacho@trey.es>
 * Copyright 2015 Antonio Espinosa <antonioea@antiun.com>
 * Copyright 2016 Vicent Cubells <vicent.cubells@tecnativa.com>
 */
odoo.define('website_crm_privacy_policy.crm_policy', function (require) {
    'use strict';

    var core = require('web.core');
    var ajax = require('web.ajax');
    var _t = core._t;

    crm_policy.registry.accept_policy = snippet_animation.Class.extend({
        selector: '.s_website_form',

        start: function() {
            var self = this;
            this.$target.find('.o_website_form_send').on('click', function (e) {
                self.accept_policy(e);
            });
        },

        // Validate form
        accept_policy: function(e) {
            e.preventDefault();  // Prevent the default submit behavior
            this.$target.find('.o_website_form_send').off();  // Prevent users from crazy clicking

            var self = this;
            if(!this.target.find('input[name="privacy_policy"]').is(':checked')) {
                e.preventDefault();  // Prevent form from submitting
                alert(_t('You must accept our Privacy Policy.'));
            }

        },
    });
});