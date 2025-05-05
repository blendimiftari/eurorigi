# EuroRigi - Inventory Management System

A comprehensive inventory management system built with Django, featuring:

- Product management with stock tracking
- Sales and profit analytics
- Customer management
- Stock transaction history
- Interactive dashboard with Chart.js visualizations
- Stock level monitoring and alerts
- Sales returns handling

## Features

- **Dashboard Analytics:**
  - Stock levels visualization
  - Top selling products
  - Sales and profit trends
  - Stock status distribution
  - New customer acquisition tracking
  - Sales by category analysis

- **Inventory Management:**
  - Product stock tracking
  - Automatic stock updates on sales
  - Stock transaction history
  - Low stock alerts

- **Sales Management:**
  - Sales recording and tracking
  - Sales returns processing
  - Profit calculation
  - Customer purchase history

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/eurorigi.git
cd eurorigi
```

2. Create a virtual environment and activate it:
```bash
python -m venv env
source env/bin/activate  # On Windows use: env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Apply database migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Usage

1. Access the admin interface at `http://localhost:8000/admin/`
2. Log in with your superuser credentials
3. Start managing your inventory:
   - Add products and categories
   - Record sales
   - Monitor stock levels
   - View analytics dashboard

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 