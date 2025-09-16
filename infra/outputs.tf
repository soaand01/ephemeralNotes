output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "redis_host" {
  value = azurerm_redis_cache.redis.hostname
}

output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}
