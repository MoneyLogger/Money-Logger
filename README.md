# 💰 Money Logger - Personal Finance Management System

A modern, responsive web application built with Django for tracking personal income and expenses with beautiful analytics and insights.

## 🚀 Features

### Core Functionality
- **User Authentication**: Secure login/logout system
- **Transaction Management**: Add, view, and filter income/expense/switch transactions
- **Money Transfer System**: Switch money between UPI Cash and Hand Cash
- **Balance Validation**: Prevents overspending with real-time balance checks
- **Real-time Dashboard**: Overview of financial status with summary cards
- **Advanced Analytics**: Monthly trends, category breakdowns, and interactive charts
- **Survival Dashboard**: Financial health monitoring with AI-powered insights
- **Payment Method Tracking**: Separate tracking for UPI Cash and Hand Cash balances
- **Multi-Filter System**: Filter by date, category, transaction type, and payment method
- **Responsive Design**: Optimized for mobile, tablet, and desktop devices

### Key Highlights
- **Modern UI/UX**: Clean, professional interface with glassmorphism effects
- **Interactive Charts**: Daily trends, monthly comparisons, and category distributions
- **Smart Filtering**: Date, category, transaction type (Income/Expense/Switch), and payment method filtering
- **Interactive Transaction Rows**: Click any transaction to exclude from totals and see recalculated balances
- **Interactive Category Analysis**: Click categories to toggle visibility and recalculate totals
- **Money Transfer Feature**: Seamlessly switch funds between UPI and Hand Cash without affecting totals
- **Balance Validation**: Real-time checks prevent overspending beyond available balance
- **AI-Powered Insights**: Intelligent spending analysis and financial recommendations
- **Weekly Spending Tracker**: Visual breakdown of daily expenses for the current week
- **Dynamic Spending Warnings**: Personalized alerts based on your average daily spending (not fixed amounts)
- **Survival Analytics**: Month-end balance prediction and financial health scoring
- **Payment Method Balances**: Separate balance tracking for UPI and Hand Cash
- **Real-time Warnings**: Proactive alerts for financial risks and spending patterns
- **Mobile-First**: Touch-friendly design with responsive layouts
- **Data Visualization**: Chart.js integration for beautiful financial insights

## 🏗️ Project Structure

```
money_log/
├── money_log/                 # Main project directory
│   ├── settings.py           # Django settings and configuration
│   ├── urls.py              # Main URL routing
│   └── wsgi.py              # WSGI configuration
├── accounts/                 # User management app
│   ├── models.py            # Custom User and UserProfile models
│   ├── admin.py             # Admin interface configuration
│   └── views.py             # Authentication views
├── dashboard/                # Main dashboard app
│   ├── views.py             # Dashboard and analytics views
│   ├── urls.py              # Dashboard URL patterns
│   └── templates/           # Dashboard templates
├── ledger/                   # Transaction management app
│   ├── models.py            # Transaction model
│   ├── forms.py             # Transaction forms
│   ├── views.py             # Transaction CRUD views
│   ├── admin.py             # Transaction admin interface
│   └── templates/           # Transaction templates
└── templates/                # Global templates
    ├── accounts/            # Authentication templates
    ├── dashboard/           # Dashboard templates
    └── ledger/              # Transaction templates
```

## 🔧 Technology Stack

### Backend
- **Django 5.2.10**: Web framework
- **SQLite**: Database (development)
- **Python 3.x**: Programming language

### Frontend
- **HTML5/CSS3**: Structure and styling
- **JavaScript**: Interactive functionality
- **Chart.js**: Data visualization
- **Inter Font**: Modern typography

### Key Libraries
- **django.contrib.humanize**: Number formatting with commas
- **python-dotenv**: Environment variable management

## 📊 Database Schema

### User Model (Custom)
```python
class User(AbstractUser):
    # Extends Django's built-in User model
    # Fields: username, email, password, first_name, last_name, etc.
```

### Transaction Model
```python
class Transaction(models.Model):
    user = ForeignKey(User)                    # Transaction owner
    transaction_type = CharField               # 'INCOME', 'EXPENSE', or 'SWITCH'
    money_type = CharField                     # 'UPI CASH' or 'HAND CASH'
    switch_direction = CharField               # 'UPI_TO_HAND' or 'HAND_TO_UPI' (for switches)
    amount = DecimalField(max_digits=12)       # Transaction amount
    category = CharField(max_length=50)        # Transaction category
    description = CharField(max_length=200)    # Optional description
    date = DateField()                         # Transaction date
    created_at = DateTimeField(auto_now_add=True)  # Creation timestamp
```

### UserProfile Model
```python
class UserProfile(models.Model):
    user = OneToOneField(User)
    phone_plain = CharField                    # Phone number
    address_plain = TextField                  # Address
    # Includes encrypted fields for sensitive data
```

## 🔄 Application Workflow

### 1. User Authentication Flow
```
User Registration/Login → Authentication → Dashboard Access
```

### 2. Transaction Management Flow
```
Add Transaction → Form Validation → Database Storage → Dashboard Update
```

### 3. Analytics Generation Flow
```
Transaction Data → Date Filtering → Aggregation → Chart Generation → Display
```

### 4. Dashboard Data Flow
```
User Login → Fetch Transactions → Calculate Summaries → Render Dashboard
```

## 🎯 Core Features Breakdown

### Dashboard (`dashboard/views.py`)
- **Summary Cards**: Total income, expenses, and balance
- **Payment Method Balances**: Separate UPI Cash and Hand Cash balance display with switch tracking
- **Interactive Transaction Rows**: Click any row to exclude from totals and see recalculated balances
- **Multi-Filter System**: Date, category, transaction type (Income/Expense/Switch), and payment method filters
- **Financial Health Warnings**: Real-time alerts for spending risks with personalized thresholds
- **Recent Transactions**: Paginated transaction list with inline filtering
- **AJAX Pagination**: Smooth page transitions with preserved filters
- **Balance Validation**: Prevents transactions exceeding available funds

### Survival Dashboard (`dashboard/views.py - survival_dashboard`)
- **Financial Health Score**: 0-100 scoring system with color-coded status
- **Wealth Tracking**: Available funds across payment methods
- **Weekly Spending Analysis**: Visual breakdown of daily expenses for current week
- **Today's Spending Tracker**: Real-time tracking of current day expenses
- **Month Survival Analysis**: Prediction of month-end financial status
- **AI Insights**: Intelligent spending analysis and recommendations
- **Cashflow Forecasting**: End-of-month balance predictions
- **Dynamic Warnings**: Personalized alerts based on your average daily spending (not fixed amounts)

### Analytics (`dashboard/views.py - analytics`)
- **Month Navigation**: Previous/next month browsing
- **Daily Trends**: Line charts showing daily income/expense patterns
- **Monthly Overview**: Bar charts for yearly monthly comparison
- **Interactive Category Analysis**: Clickable pie charts and tables
- **Category Toggle Feature**: Click categories to exclude from totals
- **Real-time Total Calculation**: Dynamic total updates when categories are toggled
- **Data Aggregation**: Complex database queries for insights

### Transaction Management (`ledger/views.py`)
- **Add Transactions**: Form-based transaction creation with validation
- **Switch Money**: Transfer funds between UPI Cash and Hand Cash
- **Balance Validation**: Real-time checks prevent overspending
- **Form Validation**: Server-side validation and error handling
- **User Association**: Automatic user linking for transactions
- **Insufficient Balance Alerts**: Clear error messages showing available vs required amounts

## 🎨 UI/UX Design Philosophy

### Design Principles
- **Mobile-First**: Responsive design starting from mobile
- **Modern Aesthetics**: Clean, professional appearance
- **User-Friendly**: Intuitive navigation and interactions
- **Accessibility**: Proper labels, focus states, and semantic HTML

### Color Scheme
- **Primary**: Blue gradient (#4facfe to #00f2fe)
- **Success**: Green (#2ecc71) for income
- **Danger**: Red (#e74c3c) for expenses
- **Neutral**: Gray tones for text and backgrounds

### Responsive Breakpoints
- **Mobile**: ≤ 480px (Ultra-compact layout)
- **Tablet**: ≤ 768px (Compact layout)
- **Desktop**: ≥ 1024px (Spacious layout)
- **Large Desktop**: ≥ 1440px (Ultra-wide support)

## 📱 Mobile Optimization

### Key Mobile Features
- **Touch-Friendly**: Large buttons and input fields
- **iOS Compatibility**: 16px font size prevents zoom
- **Horizontal Scrolling**: Tables scroll smoothly on mobile
- **Stacked Layouts**: Forms and navigation stack vertically
- **Optimized Charts**: Responsive chart sizing

## 📈 Analytics Features

### Chart Types
1. **Daily Trend Chart**: Line chart showing daily income/expense
2. **Monthly Bar Chart**: Yearly overview with monthly comparisons
3. **Interactive Category Pie Charts**: Clickable charts for income/expense categories
4. **Category Breakdown Tables**: Interactive tables with total calculations

### Data Insights
- **Financial Summaries**: Overall and monthly totals
- **Payment Method Tracking**: Separate balances for UPI and Hand Cash with switch tracking
- **Interactive Transaction Analysis**: Click any transaction row to exclude from totals
- **Interactive Category Analysis**: Toggle categories to see impact on totals
- **Weekly Spending Breakdown**: Daily expense tracking for current week
- **AI-Powered Analytics**: Month-over-month comparisons and spending insights
- **Category Breakdowns**: Spending patterns by category with spike detection
- **Trend Analysis**: Daily and monthly financial trends
- **Balance Tracking**: Real-time cumulative balance calculations
- **Survival Metrics**: Days remaining, burn rate, and financial health scoring
- **Personalized Warnings**: Dynamic alerts based on your spending patterns

## 🤖 AI-Powered Features

### Smart Insights
- **Month-over-Month Analysis**: "You're spending 35% more than last month"
- **Category Spike Detection**: "Food expense spike detected (+45%)"
- **Savings Tracking**: "This month you saved ₹3,000 more than last month"
- **Spending Pattern Recognition**: Identifies unusual spending behaviors
- **High Spending Day Analysis**: Tracks and alerts on exceptional spending days

### Financial Health Monitoring
- **Health Score Calculation**: 100-point scoring system based on spending patterns
- **Risk Assessment**: Automatic detection of financial risks
- **Survival Analysis**: Predicts if user will run out of money before month-end
- **Cashflow Forecasting**: Projects end-of-month balance based on current trends
- **Proactive Warnings**: Real-time alerts across all pages
- **Personalized Thresholds**: Warnings based on your average spending (not fixed amounts)
- **Weekly Spending Insights**: Track daily expenses throughout the week
- **Today's Spending Alerts**: Immediate notification when exceeding daily average by 50%

### Dynamic Data Processing
- **Real-time Updates**: All calculations update automatically based on current date/time
- **Month Transitions**: Seamless handling of month changes (Jan 31 → Feb 1)
- **Cumulative Balance Tracking**: Balances carry forward across months
- **Contextual Recommendations**: Personalized financial advice based on user patterns

## 🛡️ Survival Dashboard

### Core Metrics
- **Wealth**: Total available funds across all payment methods
- **Health**: Financial health score with color-coded status indicators
- **Survival**: Month-end survival prediction with risk assessment

### Advanced Analytics
- **Daily Burn Rate**: Average daily spending calculation
- **Weekly Spending Tracker**: Day-by-day expense breakdown for current week
- **Today's Expense Monitor**: Real-time tracking of current day spending
- **Projected End Balance**: Month-end balance prediction
- **Days Until Broke**: Early warning system for fund depletion
- **Payment Method Breakdown**: Detailed balance analysis by UPI/Hand Cash including switches

### AI Insights Integration
- **Spending Comparisons**: Intelligent month-over-month analysis
- **Category Intelligence**: Automatic detection of spending spikes
- **Behavioral Insights**: Pattern recognition for financial habits
- **Forecasting**: Trend-based predictions for financial planning

### Authentication
- **Login Required**: All views protected with `@login_required`
- **User Isolation**: Users only see their own transactions
- **CSRF Protection**: Forms protected against CSRF attacks

### Data Protection
- **Encrypted Fields**: Sensitive user data encryption support
- **Secure Sessions**: Django's built-in session security
- **SQL Injection Prevention**: ORM-based database queries

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- Django 5.2.10
- SQLite (included with Python)

### Installation Steps
```bash
# Clone the repository
git clone <repository-url>
cd money_log

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install django python-dotenv

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Environment Variables
Create a `.env` file in the project root:
```
SECRET_KEY=your-secret-key-here
ENABLE_ENCRYPTION=false
```

## 🔧 Configuration

### Django Settings
- **DEBUG**: Set to `False` in production
- **ALLOWED_HOSTS**: Configure for production domain
- **DATABASES**: Switch to PostgreSQL/MySQL for production
- **STATIC_FILES**: Configure static file serving

### Admin Interface
Access Django admin at `/admin/` to:
- Manage users and transactions
- View database records
- Perform administrative tasks

## 📊 Usage Examples

### Adding a Transaction
1. Navigate to "Add Transaction"
2. Select Income or Expense (radio buttons)
3. Choose Payment Method (UPI Cash or Hand Cash)
4. Enter amount, category, description
5. Choose date
6. Save transaction (validates sufficient balance for expenses)

### Switching Money Between Payment Methods
1. Click "🔄 Switch Money" from dashboard
2. Select transfer direction:
   - 💳 UPI → 💵 Hand (withdraw cash from UPI)
   - 💵 Hand → 💳 UPI (deposit cash to UPI)
3. Enter amount to transfer
4. Add optional description (e.g., "ATM withdrawal")
5. Choose date
6. Click "Switch Money" (validates sufficient balance)

### Interactive Transaction Analysis
1. On dashboard, click any transaction row
2. Row becomes grayed out with strikethrough
3. See recalculated totals excluding that transaction
4. Click again to re-include the transaction
5. Click "Reset" to clear all exclusions

### Viewing Analytics
1. Click "Analytics" from dashboard
2. Use month navigation to browse different periods
3. View interactive charts and category breakdowns
4. Click categories in pie charts or tables to toggle visibility
5. Watch totals recalculate dynamically
6. Analyze spending patterns with and without specific categories

### Using Survival Dashboard
1. Click "🛡️ Survival" from dashboard or warning alerts
2. View your financial health score and status
3. Check available funds and month-end predictions
4. Review weekly spending breakdown
5. Monitor today's spending vs daily average
6. Review AI insights for spending recommendations
7. Monitor days remaining and burn rate
8. Take action based on survival analysis

### Filtering Transactions
1. Use comprehensive filters on dashboard:
   - Date range (start and end dates)
   - Category selection
   - Transaction type (Income/Expense/Switch)
   - Payment method (UPI Cash/Hand Cash)
2. Click "Filter" to apply multiple filters simultaneously
3. Use "Reset" to clear all filters
4. Filters persist during pagination

## 🔮 Future Enhancements

### Planned Features
- **SMS Integration**: Auto-parse bank SMS notifications
- **Receipt Scanning**: OCR-based expense entry
- **Recurring Transactions**: Automated monthly bills
- **Budget Planning**: Set and track budgets
- **Export Features**: PDF/Excel export capabilities
- **Multi-currency Support**: Handle different currencies
- **Bank API Integration**: Direct bank account connection

### Technical Improvements
- **API Development**: REST API for mobile apps
- **Real-time Updates**: WebSocket integration
- **Advanced Analytics**: Machine learning insights
- **Performance Optimization**: Database indexing and caching

## 🤝 Contributing

### Development Guidelines
1. Follow Django best practices
2. Maintain responsive design principles
3. Write clean, documented code
4. Test on multiple devices
5. Ensure security best practices

### Code Style
- Use Django conventions
- Follow PEP 8 for Python code
- Use semantic HTML and CSS
- Comment complex logic

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 👨‍💻 Author

Developed with ❤️ for personal finance management.

---

**Money Logger** - Take control of your finances with beautiful, insightful analytics! 💰📊