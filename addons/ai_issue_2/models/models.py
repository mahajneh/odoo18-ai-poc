from odoo import models, fields

class CustomerLoyalty(models.Model):
    _name = 'customer.loyalty'
    _description = 'Customer Loyalty Points'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    points = fields.Integer(string='Loyalty Points', default=0)