# Xcellar - Django REST Framework Backend

A scalable Django REST Framework backend for mobile applications with n8n workflow automation integration.

## Features

- **Django REST Framework** with JWT authentication
- **Multi-user type support**: Regular Users and Couriers
- **PostgreSQL** database
- **Redis** for caching and rate limiting
- **n8n integration** for workflow automation (self-hosted)
- **Docker** containerization
- **Rate limiting** on all endpoints
- **Scalable architecture** with separated apps
- **API versioning** ready
- **Interactive API Documentation** with Swagger UI

## Project Structure

```
xcellar/
├── apps/
│   ├── accounts/          # Authentication & user management
│   ├── users/             # Customer-specific features
│   ├── couriers/          # Courier-specific features
│   ├── automation/        # n8n integration
│   └── core/              # Core utilities
├── xcellar/               # Django project settings
│   └── settings/          # Split settings (base, dev, prod)
├── docker-compose.yml     # Multi-container setup
├── Dockerfile             # Django app container
└── requirements.txt        # Python dependencies
```

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Qubic-Group/Xcellar_RestAPI.git
   cd Xcellar
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Build and start containers**
   ```bash
   docker-compose up --build
   ```

4. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Create superuser** (optional)
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

## Services

- **Django API**: http://localhost:8000
- **n8n**: http://localhost:5678
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## API Documentation

The API is fully documented with interactive Swagger UI and ReDoc interfaces:

- **Swagger UI**: http://localhost:8000/api/docs/
  - Interactive API explorer
  - Test endpoints directly from the browser
  - JWT authentication support
  - Request/response examples

- **ReDoc**: http://localhost:8000/api/redoc/
  - Clean, readable API documentation
  - Better for reading and understanding

- **OpenAPI Schema**: http://localhost:8000/api/schema/
  - Downloadable OpenAPI 3.0 JSON schema
  - Can be imported into Postman, Insomnia, etc.

### Using the Interactive Documentation

1. Visit http://localhost:8000/api/docs/
2. Click "Authorize" button
3. Enter your JWT token (obtained from login endpoint)
4. Test any endpoint directly from the browser!

## API Endpoints

For full API documentation, visit http://localhost:8000/api/docs/

### Authentication
- `POST /api/v1/auth/register/user/` - Register regular customer
- `POST /api/v1/auth/register/courier/` - Register courier
- `POST /api/v1/auth/login/` - Login (returns JWT tokens)
- `POST /api/v1/auth/refresh/` - Refresh JWT token
- `GET /api/v1/auth/profile/` - Get current user profile

### Users
- `GET /api/v1/users/dashboard/` - User dashboard (requires USER role)

### Couriers
- `GET /api/v1/couriers/dashboard/` - Courier dashboard (requires COURIER role)

### Automation (n8n)
- `POST /api/v1/automation/webhook/` - Webhook endpoint for n8n
- `GET /api/v1/automation/workflows/` - Get workflow logs
- `GET /api/v1/automation/tasks/` - Get automation tasks

## User Types

### Regular User (USER)
- Regular customers who place orders
- Access to user-specific endpoints

### Courier (COURIER)
- Drivers who deliver orders
- Access to courier-specific endpoints
- Additional fields: license_number, vehicle_type, is_available

## n8n Integration

### Django → n8n (Triggering Workflows)

Use the `WorkflowTrigger` service to trigger n8n workflows:

```python
from apps.automation.services.workflow_trigger import WorkflowTrigger

trigger = WorkflowTrigger()

# Trigger workflow when order is created
trigger.on_order_created(order_data, workflow_id='your-workflow-id')

# Trigger workflow when courier is assigned
trigger.on_courier_assigned(order_data, courier_data, workflow_id='your-workflow-id')
```

### n8n → Django (Webhook Endpoints)

n8n can call Django APIs via webhook endpoint:
- URL: `POST http://web:8000/api/v1/automation/webhook/`
- Payload: `{"action": "your_action", "data": {...}}`

## Rate Limiting

Rate limiting is configured on all endpoints:
- Authentication endpoints: 5-10 requests per hour per IP
- API endpoints: 100 requests per hour per user
- Webhook endpoints: 100 requests per hour per IP

## Development

### Running locally (without Docker)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   export DB_HOST=localhost
   export DB_NAME=xcellar_db
   # ... etc
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Run server:
   ```bash
   python manage.py runserver
   ```

### Accessing n8n

1. Navigate to http://localhost:5678
2. Login with credentials:
   - Username: `admin`
   - Password: `admin123` (change in production!)

## Environment Variables

See `.env.example` for all available environment variables.

Key variables:
- `SECRET_KEY` - Django secret key
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database credentials
- `N8N_API_URL` - n8n API URL
- `N8N_WEBHOOK_SECRET` - Webhook secret for n8n
- `JWT_ACCESS_TOKEN_LIFETIME` - JWT access token lifetime (minutes)

## Production Deployment

1. Set `DEBUG=False` in production settings
2. Update `ALLOWED_HOSTS` in `.env`
3. Use strong `SECRET_KEY`
4. Configure proper database credentials
5. Set up SSL/TLS certificates
6. Update n8n credentials
7. Configure proper CORS origins

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

