odoo.define('pos_ui_color.pos', function (require) {
    "use strict";

    var rpc = require('web.rpc');
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var PopupWidget = require('point_of_sale.popups').PopupWidget;

    // Utility to apply the CSS variable and update UI elements
    function apply_color(color) {
        if (!color) {
            return;
        }
        var root = document.documentElement;
        root.style.setProperty('--pos-primary-color', color);
        document.body.classList.add('pos-ui-colorized');
        var btn = document.querySelector('.button-color');
        if (btn) {
            btn.style.backgroundColor = color;
        }
    }

    // Extend PosModel to apply company color on start and poll for changes
    var PosModelSuper = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            PosModelSuper.initialize.call(this, session, attributes);
            var color = (this.company && this.company.pos_theme_color) || '#3276b1';
            apply_color(color);

            // Polling interval in ms
            var POLL_INTERVAL = 5000;
            setInterval(function () {
                if (!this.company) {
                    return;
                }
                rpc.query({
                    model: 'res.company',
                    method: 'read',
                    args: [[this.company.id], ['pos_theme_color']],
                }).then(function (res) {
                    if (!res || !res[0]) {
                        return;
                    }
                    var new_color = res[0].pos_theme_color || '#3276b1';
                    apply_color(new_color);
                }).catch(function () {
                    // ignore errors silently
                });
            }.bind(this), POLL_INTERVAL);
        },
    });

    // Popup for color picker
    var ColorPickerPopup = PopupWidget.extend({
        template: 'ColorPickerPopup',
        show: function (options) {
            options = options || {};
            this._super(options);
            var self = this;
            var input = this.$el.find('.pos-color-input');
            var initial = options.color || (this.pos.company && this.pos.company.pos_theme_color) || '#3276b1';
            input.val(initial);

            this.$el.find('.confirm').off('click').on('click', function () {
                var color = input.val();
                if (!color) {
                    return;
                }
                // Persist in company
                rpc.query({
                    model: 'res.company',
                    method: 'write',
                    args: [[self.pos.company.id], { 'pos_theme_color': color }],
                }).then(function () {
                    // update local company object and apply
                    self.pos.company.pos_theme_color = color;
                    apply_color(color);
                    self.gui.close_popup();
                }).catch(function (err) {
                    self.gui.show_popup('error', {
                        'title': 'Error',
                        'body': 'Failed to save color: ' + (err && err.message ? err.message : '')
                    });
                });
            });

            this.$el.find('.cancel').off('click').on('click', function () {
                self.gui.close_popup();
            });
        }
    });

    // Color button in top bar
    var ColorButton = screens.ActionButtonWidget.extend({
        template: 'ColorButton',
        button_click: function () {
            var color = (this.pos.company && this.pos.company.pos_theme_color) || '#3276b1';
            this.gui.show_popup('color_picker_popup', { color: color });
        },
    });

    // Register popup and action button
    gui.define_popup({ name: 'color_picker_popup', widget: ColorPickerPopup });
    screens.define_action_button({
        name: 'color_button',
        widget: ColorButton,
        condition: function () { return true; }
    });

    return {
        apply_color: apply_color
    };
});
