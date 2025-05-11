/**
 * SaleItem price auto-loader
 * Automatically populates price_at_sale field when a product is selected
 */
document.addEventListener('DOMContentLoaded', function() {
    // Function to update price when product is selected
    function updateProductPrice(select) {
        if (!select || !select.value) return;
        
        var productId = select.value;
        
        // Parse row ID - Django uses format like id_items-0-product for inlines
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
    
    // Add change event listeners to all product select fields
    function setupEventListeners() {
        var productSelects = document.querySelectorAll('select[id$="-product"]');
        
        for (var i = 0; i < productSelects.length; i++) {
            // Add change event listener
            productSelects[i].addEventListener('change', function() {
                updateProductPrice(this);
            });
            
            // Initialize with current value if not empty
            if (productSelects[i].value) {
                updateProductPrice(productSelects[i]);
            }
        }
    }
    
    // Initial setup
    setTimeout(setupEventListeners, 300);
    
    // Make the function globally available
    window.updateProductPrice = updateProductPrice;
    
    // Watch for dynamically added rows in tabular inlines
    var observer = new MutationObserver(function() {
        setTimeout(setupEventListeners, 100);
    });
    
    // Start observing for added inline rows
    var inlineGroups = document.querySelectorAll('.inline-group');
    for (var i = 0; i < inlineGroups.length; i++) {
        observer.observe(inlineGroups[i], { childList: true, subtree: true });
    }
});
