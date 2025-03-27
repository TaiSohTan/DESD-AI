# MLAAS - Machine Learning as a Service Platform

## Overview

MLAAS is a comprehensive platform that provides insurance settlement predictions through machine learning. Built with a modern microservices architecture, the application combines the power of Django for the web application and FastAPI for the machine learning service.

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

## Technology Stack

- **Backend**: Django, FastAPI
- **Frontend**: Bootstrap, HTML/CSS, JavaScript
- **Database**: PostgreSQL
- **Authentication**: JWT (JSON Web Tokens)
- **Containerization**: Docker, Docker Compose
- **ML Framework**: Scikit-learn, XGBoost, Tensorflow, Keras
- **Payment Processing**: Stripe API

## Getting Started

.env
docker-compose.yaml
Dockerfile
entrypoint.sh
insurance_claim_data.csv
manage.py
README.md
requirements.txt
wait-for
.vscode/
    settings.json
api/
    __init__.py
    admin.py
    apps.py
    middleware.py
    models.py
    permissions.py
    serializers.py
    tests.py
    urls.py
    views.py
    viewsets.py
    migrations/
    static/
        templates/
desd/
    __init__.py
    asgi.py
    settings.py
    urls.py
    wsgi.py
FastAPI/
    appendix.txt
    auth.py
    Dockerfile
    gbr_fs.pkl
    gbr.pkl
    main.py
utils/
    ...

- Django Application: Located in the root and desd directories.
- FastAPI ML Service: Located in the FastAPI directory.
- Shared Resources: The .env and docker-compose.yaml files configure the entire project.

## Test Cards for the Stripe Payment (Dont use real cards)
Visa Credit : 4242 4242 4242 Exp : Future Data CVV2: Any 3 Digit No. 
Source Stripe API Documentation

