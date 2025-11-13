from django import forms
from .models import OrderItem

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = [
            "system_sheet", "table_section", "fabric_name",
            "height_gabarit_mm", "width_fabric_mm",
            "gabarit_width_flag", "magnets_fixation",
        ]
