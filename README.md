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

1. Manually go the start.bat file that's located on the project root folder, right click and press `Send to -> Desktop`
2. First step creates a shortcut on the Desktop, now you can start the app by double-clicking on the shortcut 
3. Optional: change icon, select the icon that is located on the media folder inside the project root folder)
4. Log in with your superuser credentials
5. Start managing your inventory:
   - Add products and categories
   - Record sales
   - Monitor stock levels
   - View analytics dashboard


## License

This project is licensed under the MIT License - see the LICENSE file for details. 