# GreenValue AI

**GreenValue AI** is a comprehensive waste management and recycling platform designed to connect waste producers with recycling facilities, optimize logistics, and promote a circular economy. The platform provides tools for waste tracking, facility management, and data-driven insights to improve recycling efficiency.

## Features

### For Waste Producers
- **Waste Registration**: Easily register waste with detailed information including type, quantity, and photos.
- **Facility Search**: Find nearby recycling facilities based on waste type and location.
- **Logistics Management**: Schedule waste pickups and track transportation status.
- **Waste Tracking**: Monitor waste flow from generation to final disposal.
- **Reporting**: Generate reports on waste generation and recycling performance.

### For Recycling Facilities
- **Facility Management**: Manage facility details, certifications, and capacity.
- **Waste Reception**: Track incoming waste and manage acceptance processes.
- **Processing Management**: Monitor waste processing operations.
- **Inventory Management**: Track recycled materials and stock levels.
- **Compliance**: Maintain records for environmental compliance and certifications.

### Platform Features
- **User Management**: Role-based access control for different user types.
- **Notifications**: Real-time alerts for waste pickups, status updates, and facility activities.
- **Search & Filtering**: Advanced search capabilities for facilities and waste types.
- **Dashboard**: Visual overview of waste management operations and key metrics.
- **Data Analytics**: Insights into recycling efficiency and environmental impact.

## Tech Stack

### Frontend
- **Framework**: Angular 20
- **UI Components**: Angular Material
- **Mapping**: Leaflet with Angular Leaflet Directive
- **Charts**: ngx-charts
- **State Management**: RxJS
- **Build Tool**: Angular CLI

### Backend
- **Framework**: ASP.NET Core 8
- **Language**: C#
- **Database**: PostgreSQL
- **ORM**: Entity Framework Core
- **Authentication**: JWT Authentication
- **API**: RESTful API with Swagger/OpenAPI

### Infrastructure
- **Containerization**: Docker
- **Container Orchestration**: Docker Compose
- **Cloud Platform**: Azure (App Service, PostgreSQL, Blob Storage)
- **CI/CD**: GitHub Actions

## Getting Started

### Prerequisites
- [.NET 8 SDK](https://dotnet.microsoft.com/download)
- [Node.js](https://nodejs.org/)
- [Angular CLI](https://angular.io/cli)
- [Docker](https://www.docker.com/)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd GreenValue AI
   ```

2. **Backend Setup**
   ```bash
   cd GreenValue.Api
   dotnet restore
   dotnet ef database update
   ```

3. **Frontend Setup**
   ```bash
   cd ../GreenValue.Client
   npm install
   ```

4. **Run the Application**
   ```bash
   # Run backend
   cd ../GreenValue.Api
   dotnet run
   
   # Run frontend
   cd ../GreenValue.Client
   ng serve
   ```

## Project Structure

```
GreenValue AI/
├── GreenValue.Api/             # Backend API
│   ├── Controllers/            # API Controllers
│   ├── Models/                 # Data Models
│   ├── Services/               # Business Logic
│   ├── Data/                   # Database Context
│   └── ...
├── GreenValue.Client/          # Frontend Application
│   ├── src/                    # Source Code
│   │   ├── app/                # Angular Components
│   │   ├── assets/             # Static Assets
│   │   ├── environments/       # Environment Configurations
│   │   └── ...
│   └── ...
├── docker-compose.yml          # Docker Compose Configuration
├── Dockerfile                  # Dockerfiles for services
└── README.md                   # Project Documentation
```

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

## Contact

For questions or support, please contact:
- **Email**: [EMAIL_ADDRESS]
- **Website**: [https://greenvalue.ai](https://greenvalue.ai)

## Acknowledgments

- [Angular](https://angular.io/)
- [ASP.NET Core](https://dotnet.microsoft.com/)
- [Leaflet](https://leafletjs.com/)
- [Angular Material](https://material.angular.io/)
- [PostgreSQL](https://www.postgresql.org/)
- [Docker](https://www.docker.com/)

## Support

If you find this project useful, please consider giving it a star ⭐!

---

*Built with ❤️ for a sustainable future*