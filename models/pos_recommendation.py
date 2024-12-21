from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class POSProductRecommendation(models.Model):
    _name = 'pos.product.recommendation'
    _description = 'POS Product Recommendations'

    name = fields.Char(related='product_id.name', string='Product Name', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    recommended_product_ids = fields.Many2many('product.product', string='Recommended Products')
    recommendation_date = fields.Datetime('Last Updated', default=fields.Datetime.now)
    category_id = fields.Many2one(related='product_id.categ_id', string='Category', store=True)
    price = fields.Float(related='product_id.list_price', string='Price', store=True)

    def action_get_recommendations(self):
        """Button action to get recommendations"""
        for rec in self:
            # Get the raw product records instead of formatted dictionaries
            recommended_products = self._get_recommended_product_records(rec.product_id.id)
            if recommended_products:
                rec.recommended_product_ids = [(6, 0, recommended_products.ids)]
        return True

    def _get_recommended_product_records(self, product_id):
        """Get recommendation records (not formatted)"""
        if not product_id:
            return []

        current_product = self.env['product.product'].browse(product_id)
        if not current_product:
            return []

        category_id = current_product.categ_id.id
        current_price = float(current_product.list_price)

        min_price = current_price * 0.8
        max_price = current_price * 1.2

        return self.env['product.product'].search([
            ('id', '!=', int(product_id)),
            ('categ_id', '=', category_id),
            ('list_price', '>=', min_price),
            ('list_price', '<=', max_price),
            ('available_in_pos', '=', True),
            ('active', '=', True)
        ], limit=5)

    @api.model
    def get_basic_recommendations(self, product_id):
        """Get formatted recommendations for POS"""
        recommended_products = self._get_recommended_product_records(product_id)

        # Format the data for POS
        return [{
            'id': product.id,
            'display_name': product.display_name,
            'lst_price': float(product.lst_price),
            'image_url': f'/web/image?model=product.product&id={product.id}&field=image_128'
        } for product in recommended_products]

    @api.model
    def get_frequently_bought_together(self, product_id, limit=5, days=30):
        """Get products frequently bought together with given product"""
        if not product_id:
            return []

        date_limit = fields.Datetime.now() - timedelta(days=days)

        # Get relationships sorted by frequency
        relationships = self.env['pos.product.relationship'].search([
            ('product_id', '=', product_id),
            ('last_bought', '>=', date_limit),
            ('related_product_id.available_in_pos', '=', True),
            ('related_product_id.active', '=', True)
        ], order='frequency desc', limit=limit)

        # Format the results
        return [{
            'id': rel.related_product_id.id,
            'display_name': rel.related_product_id.display_name,
            'lst_price': float(rel.related_product_id.lst_price),
            'image_url': f'/web/image?model=product.product&id={rel.related_product_id.id}&field=image_128',
            'frequency': rel.frequency
        } for rel in relationships]

    @api.model
    def get_popular_products(self, limit=5):
        """Get popular products based on popularity score"""
        templates = self.env['product.template'].search([
            ('available_in_pos', '=', True),
            ('active', '=', True)
        ], order='popularity_score desc', limit=limit)

        products = templates.mapped('product_variant_ids')[0:limit]  # Get first variant of each template

        return [{
            'id': product.id,
            'display_name': product.display_name,
            'lst_price': float(product.lst_price),
            'image_url': f'/web/image?model=product.product&id={product.id}&field=image_128',
            'sales_count': product.sales_count_30,
            'view_count': product.product_tmpl_id.view_count,
            'popularity_score': round(product.product_tmpl_id.popularity_score * 100, 1)
        } for product in products]

    @api.model
    def get_all_recommendations(self, product_id):
        """Get all types of recommendations"""
        return {
            'similar_products': self.get_basic_recommendations(product_id),
            'frequently_bought': self.get_frequently_bought_together(product_id),
            'popular_products': self.get_popular_products()
        }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    view_count = fields.Integer(string='View Count', default=0)
    sales_count_30 = fields.Integer(string='30 Days Sales Count', compute='_compute_sales_count_30', store=True)
    popularity_score = fields.Float(string='Popularity Score', compute='_compute_popularity_score', store=True)

    @api.depends('product_variant_ids.sales_count_30')
    def _compute_sales_count_30(self):
        for template in self:
            template.sales_count_30 = sum(template.product_variant_ids.mapped('sales_count_30'))

    @api.depends('sales_count_30', 'view_count')
    def _compute_popularity_score(self):
        templates = self.search([])
        max_sales = max(templates.mapped('sales_count_30') or [1])
        max_views = max(templates.mapped('view_count') or [1])

        for template in self:
            normalized_sales = (template.sales_count_30 / max_sales) if max_sales else 0
            normalized_views = (template.view_count / max_views) if max_views else 0
            template.popularity_score = (normalized_sales * 0.7) + (normalized_views * 0.3)

class ProductProduct(models.Model):
        _inherit = 'product.product'

        view_count = fields.Integer(string='View Count', default=0)
        detail_view_count = fields.Integer('Detail Views', default=0)
        cart_view_count = fields.Integer('Cart Views', default=0)
        recommendation_view_count = fields.Integer('Recommendation Views', default=0)
        sales_count_30 = fields.Integer(string='30 Days Sales Count', compute='_compute_sales_count_30')
        popularity_score = fields.Float(string='Popularity Score', compute='_compute_popularity_score')

        def _compute_sales_count_30(self):
            """Compute sales count for last 30 days"""
            date_30_days_ago = fields.Datetime.now() - timedelta(days=30)
            for product in self:
                domain = [
                    ('product_id', '=', product.id),
                    ('order_id.date_order', '>=', date_30_days_ago),
                    ('order_id.state', 'in', ['paid', 'done'])
                ]
                lines = self.env['pos.order.line'].search(domain)
                product.sales_count_30 = sum(lines.mapped('qty'))

        def _compute_popularity_score(self):
            """Compute popularity score based on sales and views"""
            for product in self:
                # Score = (70% of normalized sales) + (30% of normalized views)
                max_sales = max(self.search([]).mapped('sales_count_30') or [1])
                max_views = max(self.search([]).mapped('view_count') or [1])

                normalized_sales = (product.sales_count_30 / max_sales) if max_sales else 0
                normalized_views = (product.view_count / max_views) if max_views else 0

                product.popularity_score = (normalized_sales * 0.7) + (normalized_views * 0.3)

        def increment_view_count(self, view_type='general'):

            self.ensure_one()
            if view_type == 'recommendation':
                # You could add specific logic for recommendation views
                pass
            elif view_type == 'cart':
                # You could add specific logic for cart views
                pass

            # Increment the general view count
            self.product_tmpl_id.write({
                'view_count': self.product_tmpl_id.view_count + 1
            })
            return True


class ProductRelationship(models.Model):
    _name = 'pos.product.relationship'
    _description = 'POS Product Relationships'
    _indexes = [
        ('product_id', 'last_bought'),  # Add index for faster searches
    ]
    product_id = fields.Many2one('product.product', string='Product', required=True)
    related_product_id = fields.Many2one('product.product', string='Related Product')
    frequency = fields.Integer(string='Purchase Frequency', default=1)
    last_bought = fields.Datetime(string='Last Bought Together', default=fields.Datetime.now)

    _sql_constraints = [
        ('unique_product_relation',
         'UNIQUE(product_id, related_product_id)',
         'Product Relationship must be unique')
    ]

    @api.model
    def cleanup_old_relationships(self, days=90):
        """Remove relationships older than X days"""
        date_limit = fields.Datetime.now() - timedelta(days=days)
        old_relations = self.search([
            ('last_bought', '<', date_limit)
        ])
        old_relations.unlink()


class POSOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def get_product_combinations(self):
        combinations = []
        order_lines = self.order_id.lines
        products = order_lines.mapped('product_id')
        if len(products) <= 1:
            return combinations
        for line in order_lines:
            other_products = order_lines.filtered(lambda l: l.id != line.id).mapped('product_id')
            for other_product in other_products:
                combinations.append((line.product_id, other_product))
        return combinations


class POSOrder(models.Model):
    _inherit = 'pos.order'

    def update_product_relationships(self):
        ProductRel = self.env['pos.product.relationship']

        for line in self.lines:
            combinations = line.get_product_combinations()
            _logger.info('Product Combinations: %s', combinations)  # Add this line
            for prod1, prod2 in combinations:
                relation = ProductRel.search([('product_id', '=', prod1.id), ('related_product_id', '=', prod2.id)],
                                             limit=1)
                _logger.info('Found Relation: %s', relation)
                if relation:
                    relation.write({
                        'frequency': relation.frequency + 1,
                        'last_bought': fields.Datetime.now(),
                    })
                else:
                    ProductRel.create({
                        'product_id': prod1.id,
                        'related_product_id': prod2.id,
                    })

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        self.update_product_relationships()
        return res
