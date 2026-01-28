{
    "name": "POS UI Color",
    "version": "1.0.0",
    "summary": "Add a color picker to POS that changes the POS UI primary color across sessions",
    "category": "Point of Sale",
    "author": "mahajneh",
    "website": "",
    "depends": ["point_of_sale", "base"],
    "data": [
        "views/res_company_views.xml"
    ],
    "assets": {
        "point_of_sale.assets": [
            "pos_ui_color/static/src/js/pos_ui_color.js",
            "pos_ui_color/static/src/xml/pos_ui_color.xml",
            "pos_ui_color/static/src/css/pos_ui_color.css"
        ]
    },
    "installable": true,
    "application": false,
    "license": "LGPL-3"
}