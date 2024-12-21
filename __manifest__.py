{
    'name': 'Point of Sale Offline',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Handle offline operations in POS',
    'description':"""
        this module adds offline capabilities to POS
        - offline visit creation
        - offline customer creation
        - Data synchronization
    """,
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_recommendation_views.xml',
    ],
    'assets':{
        #tell odoo where javascript files to load
        'point_of_sale._assets_pos':[
            'point_of_sale_offline/static/src/components/product_recommendations/product_list.js',
            'point_of_sale_offline/static/src/components/**/*.js',
            'point_of_sale_offline/static/src/components/**/*.xml',
            'point_of_sale_offline/static/src/components/**/*.scss',
        ]
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}