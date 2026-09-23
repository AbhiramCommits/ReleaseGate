output "ecr_backend_repository_url" {
  description = "Backend ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  description = "Frontend ECR repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "alb_dns_name" {
  description = "ALB DNS name (set this as the DEPLOY_HEALTH_URL repo variable)"
  value       = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.app.name
}

output "github_deploy_role_arn" {
  description = "OIDC deploy role ARN (set this as the AWS_DEPLOY_ROLE_ARN repo variable)"
  value       = aws_iam_role.github_deploy.arn
}

output "task_definition_json" {
  description = "Rendered ECS task definition (save to infra/ecs-task-definition.json for the deploy workflow)"
  value = jsonencode({
    family                  = aws_ecs_task_definition.app.family
    networkMode             = aws_ecs_task_definition.app.network_mode
    requiresCompatibilities = aws_ecs_task_definition.app.requires_compatibilities
    cpu                     = aws_ecs_task_definition.app.cpu
    memory                  = aws_ecs_task_definition.app.memory
    executionRoleArn        = aws_ecs_task_definition.app.execution_role_arn
    taskRoleArn             = aws_ecs_task_definition.app.task_role_arn
    containerDefinitions    = jsondecode(aws_ecs_task_definition.app.container_definitions)
  })
}
