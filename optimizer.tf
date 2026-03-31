
module "cost_optimizer" {
  source = "./modules/cost-optimizer-module"
  dry_run = true
  lambda_timeout                 = var.lambda_timeout
  lambda_memory_size             = var.lambda_memory_size
  tags                           = var.tags
  report_bucket_name           = var.report_bucket_name
  sns_subscription_email       = var.sns_subscription_email
  enable_ec2_termination             = var.enable_ec2_termination
  enable_ebs_gp2_to_gp3_conversion_for_root          = true
  enable_ebs_available_volume_deletion         = true
  enable_ebs_snapshot_deletion       = true
  enable_elb_deletion                = true
  enable_eip_release                 = true
  enable_cw_log_group_retention_management = true
  enable_s3_object_deletion          = true
}

variable "aws_region" {
  description = "AWS region to deploy the optimizer"
  type        = string
  default     = "us-east-1"
}

variable "sns_subscription_email" {
  description = "Email address to subscribe to the SNS topic for receiving notifications."
  type        = string
  default     = "dipankar.adhikary@fisglobal.com" # Optional: Leave empty if no subscription is required
}

variable "report_bucket_name" {
  description = "Name of the S3 bucket to store reports"
  type        = string
  default     = "payment-hub-bucket-for-cost-optimizer-reports"
  
}

variable "optimizer_lambda_function_name" {
  description = "Name of the Cost Optimizer Lambda function"
  type        = string
  default     = "cloud-cost-optimizer"
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (e.g. rate or cron)"
  type        = string
  default     = "rate(7 days)"
}

variable "log_retention_in_days" {
  description = "How many days to retain CloudWatch Logs"
  type        = number
  default     = 30
}

variable "report_key_prefix" {
  description = "Prefix path inside S3 bucket to store reports"
  type        = string
  default     = "cost-optimizer-reports/"
}

variable "lambda_timeout" {
  description = "Timeout in seconds for the Lambda function"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Memory size for the Lambda function in MB"
  type        = number
  default     = 256
}

/*variable "tags" {
  description = "Tags to apply to all created resources"
  type        = map(string)
  default     = {}
}*/

variable "enable_ec2_termination" {
  description = "Enable termination of old stopped EC2 instances."
  type        = bool
  default     = true
}
