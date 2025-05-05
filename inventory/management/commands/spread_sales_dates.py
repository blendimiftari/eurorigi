from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from inventory.models import Sale

class Command(BaseCommand):
    help = 'Spread existing sales across the last 90 days'

    def handle(self, *args, **kwargs):
        self.stdout.write('Spreading sales dates...')
        
        # Get all sales
        sales = Sale.objects.all()
        total_sales = sales.count()
        
        if total_sales == 0:
            self.stdout.write(self.style.WARNING('No sales found to update'))
            return
            
        # Calculate date ranges
        end_date = timezone.now()
        start_date = end_date - timedelta(days=90)
        
        # Update sales dates
        for sale in sales:
            # Determine which period this sale belongs to based on its position
            days_ago = random.randint(0, 90)
            new_date = end_date - timedelta(days=days_ago)
            
            # Update the sale date
            sale.date = new_date
            sale.save()
            
            self.stdout.write(f'Updated sale #{sale.id} to date: {new_date.strftime("%Y-%m-%d")}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully spread {total_sales} sales across 90 days')) 