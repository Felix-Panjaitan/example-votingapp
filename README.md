# Voting App

A simple distributed application that allows users to vote between two options and view real-time results.

## Project Overview

This application consists of:
- A Python web app for voting
- A Redis cache to collect votes
- A .NET worker to process votes
- A PostgreSQL database for storage
- A Node.js results app to display voting results
- Monitoring with Prometheus and Grafana

## Setup Instructions

### Local Development with Docker

1. Clone this repository
2. Run the application:
```
docker compose up
```
3. Access the applications:
   - Voting interface: http://localhost:4000
   - Results dashboard: http://localhost:4001
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (username: admin, password: admin)

### Azure Deployment

1. Ensure you have the Azure CLI and Terraform installed
2. Initialize Terraform:
```
terraform init
```
3. Deploy the infrastructure:
```
terraform apply
```
4. Connect to the AKS cluster:
```
az aks get-credentials --resource-group voting-app-resources --name voting-app-aks
```
5. Deploy the application to AKS:
```
kubectl create -f k8s-specifications/
```

## Design Decisions

- **Microservices Architecture**: Each component runs in its own container for better scalability and maintainability
- **Redis for Vote Collection**: Provides fast in-memory storage for incoming votes
- **PostgreSQL for Persistent Storage**: Reliable database for storing the final voting data
- **Basic Monitoring Setup**: Prometheus and Grafana for tracking system performance
- **Cost-Efficient Azure Resources**: B-series VMs and Basic tiers to minimize cloud expenses
- **Simple User Interface**: Clean design focused on the voting experience

## Potential Improvements

- Add authentication for users
- Implement CI/CD pipeline for automated deployments
- Enhance the monitoring with custom dashboards and alerts
- Add more voting options beyond the binary choice
- Implement scaling policies for handling traffic spikes
- Create a backup and disaster recovery strategy
- Add application security scanning

## License

Apache License 2.0
