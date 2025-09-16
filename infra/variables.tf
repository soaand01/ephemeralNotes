variable "location" {
  type    = string
  default = "westeurope"
}

variable "resource_group" {
  type    = string
  default = "ephemeralnotes-rg"
}

variable "acr_name" {
  type    = string
  default = "ephemeralnotesacr"
}

variable "webapp_name" {
  type    = string
  default = "ephemeralnotes-prod"
}

variable "redis_name" {
  type    = string
  default = "ephemeralnotes-redis"
}

variable "app_plan" {
  type    = string
  default = "ephemeralnotes-plan"
}

variable "image_name" {
  type    = string
  default = "ephemeralnotes"
}
