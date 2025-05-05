// Test if the file is loading
console.log('sale_item.js is loading!');

// Wait for the window to load and Django's admin to be ready
window.addEventListener('load', function() {
    console.log('Window loaded');
    
    if (typeof window.django === 'undefined') {
        console.error('Django admin JavaScript is not loaded!');
        return;
    }

    // Use Django's jQuery
    var $ = django.jQuery;
    console.log('Django jQuery loaded:', !!$);

    // Debug function to log select elements
    function debugLogSelect(select) {
        console.log('Select element:', {
            name: select.name,
            value: select.value,
            hasHandlers: select.hasAttribute('data-price-handlers'),
            isSelect2: $(select).hasClass('select2-hidden-accessible'),
            parent: select.parentElement.className
        });
    }

    function updatePrice(productId, priceInput) {
        console.log('Attempting to update price for product:', productId);
        
        if (productId) {
            console.log('Making AJAX request for product:', productId);
            $.ajax({
                url: '/admin/inventory/product/' + productId + '/selling_price/',
                type: 'GET',
                success: function(data) {
                    console.log('Got price data:', data);
                    if (!priceInput.value) {
                        priceInput.value = data.selling_price;
                        console.log('Updated price to:', data.selling_price);
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error fetching price:', error);
                    console.error('Status:', status);
                    console.error('Response:', xhr.responseText);
                }
            });
        } else {
            priceInput.value = '';
            console.log('Cleared price input');
        }
    }

    function setupSelect2Handlers(select) {
        if (!select) {
            console.log('Select element is null or undefined');
            return;
        }

        if (select.hasAttribute('data-price-handlers')) {
            console.log('Select already has handlers:', select.name);
            return;
        }
        
        console.log('Setting up Select2 handlers for:', select.name);
        debugLogSelect(select);

        select.setAttribute('data-price-handlers', 'true');

        // Handle both Select2 and native change events
        $(select).on('select2:select change', function(e) {
            console.log('Change event detected:', {
                type: e.type,
                target: e.target.name,
                value: e.target.value
            });

            const row = this.closest('.dynamic-saleitem');
            if (row) {
                const priceInput = row.querySelector('input[name$="-price_at_sale"]');
                if (priceInput) {
                    console.log('Found price input:', priceInput.name);
                    updatePrice(this.value, priceInput);
                } else {
                    console.log('Price input not found in row');
                }
            } else {
                console.log('Row not found for select:', this.name);
            }
        });

        // If the select already has a value, update the price
        if (select.value) {
            console.log('Initial value found:', select.value);
            const row = select.closest('.dynamic-saleitem');
            if (row) {
                const priceInput = row.querySelector('input[name$="-price_at_sale"]');
                if (priceInput && !priceInput.value) {
                    updatePrice(select.value, priceInput);
                }
            }
        }
    }

    function setupAllHandlers() {
        console.log('Setting up handlers for all product selects');
        const selects = document.querySelectorAll('select[name$="-product"]:not([data-price-handlers])');
        console.log('Found', selects.length, 'unhandled product selects');
        selects.forEach(setupSelect2Handlers);
    }

    // Watch for dynamic row additions
    $(document).on('formset:added', function(event, $row, prefix) {
        console.log('New formset row added:', prefix);
        const newSelects = $row[0].querySelectorAll('select[name$="-product"]');
        console.log('Found', newSelects.length, 'selects in new row');
        newSelects.forEach(setupSelect2Handlers);
    });

    // Watch for Select2 initialization
    const observer = new MutationObserver(function(mutations) {
        let shouldSetup = false;
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1 && (
                    node.classList.contains('select2') || 
                    node.classList.contains('select2-container')
                )) {
                    shouldSetup = true;
                }
            });
        });

        if (shouldSetup) {
            console.log('Select2 elements detected, setting up handlers');
            setupAllHandlers();
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Initial setup
    console.log('Performing initial setup');
    setupAllHandlers();

    // Also listen for django.jQuery's ready event
    $(document).ready(function() {
        console.log('Django jQuery ready event fired');
        setupAllHandlers();
    });

    // Backup setup for any late-loading elements
    setTimeout(function() {
        console.log('Running backup setup');
        setupAllHandlers();
    }, 1000);
}); 