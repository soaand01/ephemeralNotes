terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features = {}
}

locals {
  prefix       = lower("${var.project}-${var.env}")
  suffix       = var.naming_suffix != "" ? "-${var.naming_suffix}" : ""
  resource_rg  = "rg-${local.prefix}-${local.suffix}"
  acr_name     = lower(replace("${var.project}${local.suffix}acr", "_", ""))
  redis_name   = lower("${local.prefix}-redis${local.suffix}")
  app_plan     = lower("${local.prefix}-plan${local.suffix}")
  webapp_name  = lower("${local.prefix}${local.suffix}")
}

resource "azurerm_resource_group" "rg" {
  name     = local.resource_rg
  location = var.location
}

resource "azurerm_container_registry" "acr" {
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = var.acr_sku
  admin_enabled       = false
}

resource "azurerm_redis_cache" "redis" {
  name                = local.redis_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = var.redis_sku
  capacity            = 0
  family              = "C"
  minimum_tls_version = "1.2"
}

resource "azurerm_app_service_plan" "plan" {
  name                = local.app_plan
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "Linux"
  reserved            = true

  sku {
    tier = "Standard"
    size = var.app_service_sku
  }
}

resource "azurerm_app_service" "webapp" {
  name                = local.webapp_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  app_service_plan_id = azurerm_app_service_plan.plan.id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    linux_fx_version = "DOCKER|${azurerm_container_registry.acr.login_server}/${var.image_name}:latest"
  }
}

# Assign AcrPull to the web app's principal id
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_app_service.webapp.identity[0].principal_id
}
