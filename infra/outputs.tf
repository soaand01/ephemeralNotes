output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "redis_host" {
  value = azurerm_redis_cache.redis.hostname
}

output "webapp_name" {
  value = azurerm_app_service.webapp.name
}
