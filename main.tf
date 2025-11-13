terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = "your-subscription-id"
}

# Resource Group
resource "azurerm_resource_group" "voting_app" {
  name     = "voting-app-resources"
  location = "East Asia"
  tags = {
    environment = "dev"
  }
}

# Virtual Network
resource "azurerm_virtual_network" "voting_app" {
  name                = "voting-app-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.voting_app.location
  resource_group_name = azurerm_resource_group.voting_app.name
}

# Subnets
resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.voting_app.name
  virtual_network_name = azurerm_virtual_network.voting_app.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "db" {
  name                 = "db-subnet"
  resource_group_name  = azurerm_resource_group.voting_app.name
  virtual_network_name = azurerm_virtual_network.voting_app.name
  address_prefixes     = ["10.0.2.0/24"]
  service_endpoints    = ["Microsoft.Sql"]
}

# Azure Container Registry - Using Basic tier
resource "azurerm_container_registry" "acr" {
  name                = "votingappacr"
  resource_group_name = azurerm_resource_group.voting_app.name
  location            = azurerm_resource_group.voting_app.location
  sku                 = "Basic"  # Changed from Standard to Basic
  admin_enabled       = true
}

# AKS Cluster - Reduced to 1 node with smaller instance size
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "voting-app-aks"
  location            = azurerm_resource_group.voting_app.location
  resource_group_name = azurerm_resource_group.voting_app.name
  dns_prefix          = "voting-app-k8s"
  kubernetes_version  = "1.26.0"

  default_node_pool {
    name           = "default"
    node_count     = 1           # Reduced from 2 to 1
    vm_size        = "Standard_B2s"  # Changed from D2_v2 to B2s (burstable, cheaper)
    vnet_subnet_id = azurerm_subnet.aks.id
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "kubenet"  # Changed from azure to kubenet (simpler)
    network_policy = null       # Removed Calico
  }

  tags = {
    environment = "dev"
  }
}

# Role Assignment for AKS to pull from ACR
resource "azurerm_role_assignment" "aks_to_acr" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

# PostgreSQL Server - Using Basic tier
resource "azurerm_postgresql_server" "db" {
  name                = "voting-app-postgres"
  location            = azurerm_resource_group.voting_app.location
  resource_group_name = azurerm_resource_group.voting_app.name

  sku_name = "B_Gen5_1"  # Changed from GP_Gen5_2 to B_Gen5_1 (Basic, single core)

  storage_mb                   = 5120
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  auto_grow_enabled            = true

  administrator_login          = "postgres"
  administrator_login_password = "Password1234!"
  version                      = "11"
  ssl_enforcement_enabled      = true
}

# PostgreSQL Database
resource "azurerm_postgresql_database" "db" {
  name                = "voting"
  resource_group_name = azurerm_resource_group.voting_app.name
  server_name         = azurerm_postgresql_server.db.name
  charset             = "UTF8"
  collation           = "English_United States.1252"
  
}

# PostgreSQL Virtual Network Rule
resource "azurerm_postgresql_virtual_network_rule" "db_vnet_rule" {
  name                = "postgresql-vnet-rule"
  resource_group_name = azurerm_resource_group.voting_app.name
  server_name         = azurerm_postgresql_server.db.name
  subnet_id           = azurerm_subnet.db.id
}

# Azure Redis Cache - Using Basic tier
resource "azurerm_redis_cache" "redis" {
  name                = "voting-app-redis"
  location            = azurerm_resource_group.voting_app.location
  resource_group_name = azurerm_resource_group.voting_app.name
  capacity            = 0        # Smallest size (0.5GB)
  family              = "C"
  sku_name            = "Basic"  # Changed from Standard to Basic
  non_ssl_port_enabled = true
  minimum_tls_version = "1.2"

  redis_configuration {
  }
}

# Output the AKS cluster name and Redis connection string
output "kubernetes_cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "aks_credentials_command" {
  value = "az aks get-credentials --resource-group ${azurerm_resource_group.voting_app.name} --name ${azurerm_kubernetes_cluster.aks.name}"
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "postgres_fqdn" {
  value = azurerm_postgresql_server.db.fqdn
}

output "redis_hostname" {
  value = azurerm_redis_cache.redis.hostname
}