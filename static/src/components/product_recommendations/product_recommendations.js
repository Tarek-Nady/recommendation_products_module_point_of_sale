/** @odoo-module */

import {AbstractAwaitablePopup} from "@point_of_sale/app/popup/abstract_awaitable_popup";
import {usePos} from "@point_of_sale/app/store/pos_hook";
import {_t} from "@web/core/l10n/translation";
import {useState} from "@odoo/owl";

export class ProductRecommendationPopup extends AbstractAwaitablePopup {
    static template = "pos_product_recommendations.ProductRecommendationPopup";
    static defaultProps = {confirmKey: false};

    setup() {
        super.setup();
        this.pos = usePos();
        this.recommendations = this.props.recommendations || {
            similar_products: [],
            frequently_bought: [],
            popular_products: []
        };

        this.mainProduct = this.props.product;
        this.state = useState({
            quantities: {}
        });
    }

    async addRecommendedProduct(productData) {
        try {
            // Increment view count
            await this.env.services.orm.call(
                'product.product',
                'increment_view_count',
                [[productData.id], 'recommendation']  // Note the array syntax for the ID
            );

            // Add product to order
            const product = this.pos.db.get_product_by_id(productData.id);
            if (product) {
                await this.pos.addProductToCurrentOrder(product);
            }
        } catch (error) {
            console.error('Error adding recommended product:', error);
        }
    }

    getSimilarProducts() {
        return this.recommendations.similar_products || [];
    }

    getFrequentlyBoughtTogether() {
        return this.recommendations.frequently_bought || [];
    }

    getPopularProducts() {
        return this.recommendations.popular_products || [];
    }

    formatPopularityScore(score) {
        return Math.round(score || 0);
    }
}