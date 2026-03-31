output "lambda_function_arn" {
  description = "ARN of the created Cost Optimizer Lambda function."
  value       = aws_lambda_function.cost_optimizer_lambda.arn
}

output "lambda_iam_role_arn" {
  description = "ARN of the IAM role created for the Lambda function."
  value       = aws_iam_role.optimizer_lambda_role.arn
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule that triggers the Lambda."
  value       = aws_cloudwatch_event_rule.optimizer_schedule.arn
}

# Output the S3 bucket name and SNS topic ARN for external use
output "report_bucket_name" {
  value = aws_s3_bucket.report_bucket.bucket
}

output "sns_topic_arn" {
  value = aws_sns_topic.notifications.arn
}
