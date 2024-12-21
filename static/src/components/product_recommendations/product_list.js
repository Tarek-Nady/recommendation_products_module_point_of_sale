/** @odoo-module */

import { ProductsWidget } from "@point_of_sale/app/screens/product_screen/product_list/product_list";
import { ProductRecommendationPopup } from "./product_recommendations";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";

patch(ProductCard, {
    props: {
        ...ProductCard.props,
        productRecommendation: { type: Boolean, optional: true },
        onProductRecommendationClick: { type: Function, optional: true },
    },
});

patch(ProductsWidget.prototype, {
    async onProductRecommendationClick(product) {
        try {
            const recommendations = await this.orm.call(
                'pos.product.recommendation',
                'get_all_recommendations',
                [product.id]
            );

            // Process each section
            for (const section in recommendations) {
                recommendations[section] = recommendations[section]
                    .filter(prod => this.pos.db.get_product_by_id(prod.id))
                    .map(prod => ({
                        ...prod,
                        lst_price: Number(prod.lst_price),
                        popularity_score: prod.popularity_score || 0,
                        sales_count: prod.sales_count || 0,
                        view_count: prod.view_count || 0
                    }));
            }

            // Show popup with recommendations
            await this.popup.add(ProductRecommendationPopup, {
                recommendations: recommendations,
                product: product
            });
        } catch (error) {
            console.error('Failed to load recommendations:', error);
            await this.popup.add(ErrorPopup, {
                title: _t("Error"),
                body: _t("Failed to load product recommendations."),
            });
        }
    }
});