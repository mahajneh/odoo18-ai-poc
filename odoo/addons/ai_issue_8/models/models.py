from odoo import models, fields

class CustomerLoyalty(models.Model):
    _name = 'customer.loyalty'
    partner_id = fields.Many2one('res.partner', required=True)
    points = fields.Integer(default=0)
