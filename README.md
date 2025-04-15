# InsurIQ - Insurance Settlement Prediction Platform

![InsurIQ Logo](api/static/images/favicon-96x96.png)

## Overview

InsurIQ is a comprehensive platform that provides insurance settlement predictions through machine learning. Built with a modern microservices architecture, the application combines the power of Django for the web application and FastAPI for the machine learning service.

The platform offers role-based access control with different features for:
- **End Users**: Make and view settlement predictions
- **AI Engineers**: Manage and train ML models
- **Finance Team**: Handle invoices and payments
- **Administrators**: Manage users and system settings

## Features

- **User Authentication**: Secure JWT-based authentication system
- **Role-Based Access Control**: Different interfaces and permissions based on user roles
- **ML Prediction Service**: Advanced machine learning models for accurate settlement predictions
- **Responsive Dashboard**: Customized dashboard based on user role
- **User Management**: Admin interface for managing users and roles
- **Payment Integration**: Secure payment processing with Stripe
- **Invoice Management**: Create, download, and track invoice status
- **API Access**: Comprehensive REST API for integration with other systems
- **Feedback System**: User feedback to improve prediction accuracy
- **Analytics Dashboard**: Insights into system usage and performance

## Technology Stack

- **Backend**: Django, FastAPI
- **Frontend**: Bootstrap, HTML/CSS, JavaScript
- **Database**: PostgreSQL
- **Authentication**: JWT (JSON Web Tokens)
- **Containerization**: Docker, Docker Compose
- **ML Framework**: Scikit-learn, XGBoost, TensorFlow, Keras
- **Payment Processing**: Stripe API
- **PDF Generation**: ReportLab
- **Documentation**: Swagger/OpenAPI (FastAPI)

## Project Structure

```
.
├── api/                      # Django app for web interface
│   ├── management/           # Custom Django management commands
│   ├── migrations/           # Database migrations
│   ├── static/               # Static assets (CSS, JS, images)
│   ├── templates/            # HTML templates
│   └── ...                   # Django app files
├── desd/                     # Django project settings
├── FastAPI/                  # ML microservice
│   ├── active_model.pkl      # Current active ML model
│   ├── main.py               # FastAPI application
│   └── ...                   # ML service files
├── media/                    # User-uploaded files
│   └── ml_models/            # Uploaded ML models
├── utils/                    # Shared utilities
│   ├── ml_api_client.py      # Client for ML API
│   ├── pdf_generator.py      # PDF generation utilities
│   └── stripe_payment.py     # Stripe payment integration
├── docker-compose.yaml       # Container orchestration
├── Dockerfile                # Docker image definition
├── requirements.txt          # Python dependencies
└── manage.py                 # Django management script
```

## Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.10 or higher (for local development)
- PostgreSQL (for local development without Docker)

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/insuriq.git
   cd insuriq
   ```

2. Create an `.env` file with the following variables:
   ```
   DEBUG=True
   SECRET_KEY=your_secret_key
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=db
   DB_PORT=5432
   STRIPE_PUBLIC_KEY=your_stripe_public_key
   STRIPE_SECRET_KEY=your_stripe_secret_key
   STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
   ```

3. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

4. Create a superuser:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

5. Access the application at [http://localhost:8000](http://localhost:8000)

### Local Development

1. Clone the repository and create a virtual environment:
   ```bash
   git clone https://github.com/yourusername/insuriq.git
   cd insuriq
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables (similar to the `.env` file above)

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

6. Start the Django development server:
   ```bash
   python manage.py runserver
   ```

7. In a separate terminal, start the FastAPI service:
   ```bash
   cd FastAPI
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

## Usage

### User Roles

InsurIQ supports four different user roles:

1. **Regular User**: Can make predictions, view their history, and provide feedback
2. **AI Engineer**: Can manage ML models, review predictions, and monitor model performance
3. **Finance Team**: Can manage invoices, payments, and billing
4. **Administrator**: Has full access to all features and user management

### Making Predictions

1. Log in with your credentials
2. Navigate to the Predictions page
3. Fill in the required information about the insurance claim
4. Submit the form to receive a settlement prediction
5. Optionally provide feedback on the prediction accuracy

### Managing Models (AI Engineers)

1. Log in with AI Engineer credentials
2. Navigate to the Model Management page
3. Upload new models (.pkl or .h5 files)
4. Set a model as active for use in predictions
5. Review model performance metrics

## API Documentation

The InsurIQ platform provides a comprehensive API for integration:

- **REST API**: Available at `/api/` endpoint
- **FastAPI Documentation**: Available at `/fastapi/` endpoint
- **API Authentication**: Uses JWT tokens for secure access

For detailed API documentation, visit the API documentation page after running the application.

## Testing

### Automated Tests

Run the test suite with:

```bash
python manage.py test
```

### Stripe Test Cards

For testing payment functionality, use the following test cards:

- **Visa (Success)**: 4242 4242 4242 4242
- **Visa (Decline)**: 4000 0000 0000 0002
- **Expiration Date**: Any future date
- **CVV**: Any 3 digits
- **ZIP**: Any 5 digits

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- UWE Bristol - Distributed and Enterprise Software Development Module
- Libraries and frameworks used in this project
- The open-source community for their invaluable resources

