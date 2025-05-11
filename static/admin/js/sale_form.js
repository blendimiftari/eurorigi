/**
 * Sale form enhancements
 * Adds automatic price loading functionality to product selections
 */
document.addEventListener('DOMContentLoaded', function() {
    // Function to update product price (used if window.updateProductPrice not available)
    function updatePrice(select) {
        if (!select || !select.value) return;
        
        var productId = select.value;
        // Parse row ID for Django admin inline forms
        var idParts = select.id.split('-');
        var prefix = idParts.length >= 3 ? idParts.slice(0, -1).join('-') : select.id.replace('-product', '');
        var priceFieldId = idParts.length >= 3 ? 
            prefix + '-price_at_sale' : 
            'id_' + prefix + '-price_at_sale';
            
        var priceField = document.getElementById(priceFieldId);
        if (!priceField) return;
        
        // Only set price if field is empty or zero
        if (!priceField.value || priceField.value === '0.00' || priceField.value === '0') {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/inventory/api/product/' + productId + '/price/', true);
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    try {
                        var response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            priceField.value = parseFloat(response.price).toFixed(2);
                        }
                    } catch (e) {}
                }
            };
            xhr.send();
        }
    }
    
    // Add event listeners to all product selects
    function setupProductSelects() {
        var productSelects = document.querySelectorAll('select[id$="-product"]');
        
        for (var i = 0; i < productSelects.length; i++) {
            var select = productSelects[i];
            
            // Add change event if not already added
            if (!select.hasAttribute('data-price-handler-attached')) {
                select.setAttribute('data-price-handler-attached', 'true');
                
                select.addEventListener('change', function() {
                    // Use global function if available, otherwise use local function
                    if (typeof window.updateProductPrice === 'function') {
                        window.updateProductPrice(this);
                    } else {
                        updatePrice(this);
                    }
                });
                
                // Initialize with current value if selected
                if (select.value) {
                    if (typeof window.updateProductPrice === 'function') {
                        window.updateProductPrice(select);
                    } else {
                        updatePrice(select);
                    }
                }
            }
        }
    }
    
    // Initialize
    setTimeout(setupProductSelects, 300);
    
    // Watch for dynamic changes
    var observer = new MutationObserver(function() {
        setTimeout(setupProductSelects, 200);
    });
    
    var inlineGroups = document.querySelectorAll('.inline-group');
    for (var i = 0; i < inlineGroups.length; i++) {
        observer.observe(inlineGroups[i], { childList: true, subtree: true });
    }
}); 