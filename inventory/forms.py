from django import forms
from .models import Product, Customer, Sale, SaleItem

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'purchase_price', 'selling_price', 'stock_quantity', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'contact_info']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_info': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['created_at'] = forms.DateTimeField(
                disabled=True,
                required=False,
                widget=forms.DateTimeInput(attrs={'class': 'form-control'}),
                initial=self.instance.created_at
            )

class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer', 'is_paid']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sale_item_forms = []
        
    def add_sale_item_form(self, data=None):
        form = SaleItemForm(data)
        self.sale_item_forms.append(form)
        return form 