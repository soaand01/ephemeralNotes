variable "env" {
  description = "Deployment environment short name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project" {
  description = "Project/application name used as prefix"
  type        = string
  default     = "ephemeralnotes"
}

variable "location" {
  type    = string
  default = "westeurope"
}

variable "naming_suffix" {
  description = "Optional suffix to append to resource names (keeps names unique)"
  type        = string
  default     = ""
}

variable "acr_sku" {
  type    = string
  default = "Standard"
}

variable "redis_sku" {
  type    = string
  default = "Basic"
}

variable "app_service_sku" {
  type    = string
  default = "B3"
}

variable "image_name" {
  type    = string
  default = "ephemeralnotes"
}

