from odoo import models, fields

class ResCompany(models.Model):
    _inherit = "res.company"

    pos_theme_color = fields.Char(string="POS Theme Color", default="#3276b1")
