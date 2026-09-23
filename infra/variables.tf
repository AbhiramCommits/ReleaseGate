variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used to prefix resources"
  type        = string
  default     = "releasegate"
}

variable "github_org" {
  description = "GitHub organization (or user) that owns the repository"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "ReleaseGate"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Postgres database name"
  type        = string
  default     = "releasegate"
}

variable "db_username" {
  description = "Postgres master username"
  type        = string
  default     = "releasegate"
}

variable "task_cpu" {
  description = "ECS task CPU units"
  type        = string
  default     = "512"
}

variable "task_memory" {
  description = "ECS task memory in MiB"
  type        = string
  default     = "1024"
}

variable "desired_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 2
}
