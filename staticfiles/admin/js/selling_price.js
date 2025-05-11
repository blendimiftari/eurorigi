document.addEventListener('DOMContentLoaded', function() {
    console.log('selling_price.js loaded successfully');

    // Select all inline forms
    const inlineForms = document.querySelectorAll('.inline-related');
    console.log('Found inline forms:', inlineForms.length);

    inlineForms.forEach((form, index) => {
        // Get the product select field
        const productSelect = form.querySelector('select[name$="-product"]');
        if (!productSelect) {
            console.warn(`No product select found in inline form ${index}`);
            return;
        }

        // Get the selling price display and price_at_sale input
        const sellingPriceDisplay = form.querySelector('.selling-price-display');
        const priceAtSaleInput = form.querySelector('input[name$="-price_at_sale"]');
        console.log(`Form ${index} - Selling price display:`, sellingPriceDisplay ? 'found' : 'not found');
        console.log(`Form ${index} - Price at sale input:`, priceAtSaleInput ? 'found' : 'not found');

        // Handle product selection change
        productSelect.addEventListener('change', function() {
            const productId = this.value;
            console.log(`Form ${index} - Product selected: ID=${productId}`);

            if (!productId) {
                // Clear fields if no product is selected
                if (sellingPriceDisplay) {
                    sellingPriceDisplay.textContent = '-';
                    sellingPriceDisplay.dataset.productId = '';
                }
                if (priceAtSaleInput) {
                    priceAtSaleInput.value = '';
                }
                console.log(`Form ${index} - Cleared fields due to no product selection`);
                return;
            }

            // Fetch the product's selling price
            console.log(`Form ${index} - Fetching price for product ID=${productId}`);
            fetch(`/inventory/product-price-lookup/?product_id=${productId}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                console.log(`Form ${index} - Fetch response status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    console.error(`Form ${index} - Error: ${data.error}`);
                    if (sellingPriceDisplay) {
                        sellingPriceDisplay.textContent = '-';
                        sellingPriceDisplay.dataset.productId = '';
                    }
                    if (priceAtSaleInput) {
                        priceAtSaleInput.value = '';
                    }
                    return;
                }

                // Update selling price display
                if (sellingPriceDisplay) {
                    sellingPriceDisplay.textContent = `$${parseFloat(data.selling_price).toFixed(2)}`;
                    sellingPriceDisplay.dataset.productId = productId;
                    console.log(`Form ${index} - Updated selling price display to $${data.selling_price}`);
                }

                // Populate price_at_sale input
                if (priceAtSaleInput) {
                    priceAtSaleInput.value = parseFloat(data.selling_price).toFixed(2);
                    console.log(`Form ${index} - Set price_at_sale input to ${priceAtSaleInput.value}`);
                }
            })
            .catch(error => {
                console.error(`Form ${index} - Fetch error:`, error);
                if (sellingPriceDisplay) {
                    sellingPriceDisplay.textContent = '-';
                    sellingPriceDisplay.dataset.productId = '';
                }
                if (priceAtSaleInput) {
                    priceAtSaleInput.value = '';
                }
            });
        });
    });
});