# Main module for creating CloudWatch Log Metric Filters and Alarms for application errors
# This module creates CloudWatch Log Metric Filters and Alarms for low, medium, and high severity application errors.

locals {
  sanitized_low_severity_keywords = [for keyword in var.low_severity_error_keywords :
    replace(replace(replace(keyword, ":", "_"), "*", "_"), "$", "_")]

  sanitized_medium_severity_keywords = [for keyword in var.medium_severity_error_keywords :
    replace(replace(replace(keyword, ":", "_"), "*", "_"), "$", "_")]

  sanitized_high_severity_keywords = [for keyword in var.high_severity_error_keywords :
    replace(replace(replace(keyword, ":", "_"), "*", "_"), "$", "_")]

  # Standard log group name construction
  log_group_name = "/aws/containerinsights/${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}/application"

    # Tags
  standard_tags = {
    SupportGroup      = var.tag_support_group
    AppGroupEmail     = var.tag_app_group_email
    EnvironmentType   = var.tag_environment_type
    SolutionCentralID = var.tag_solution_central_id
  }
}

# CloudWatch Log Metric Filters for low severity errors
resource "aws_cloudwatch_log_metric_filter" "low_severity_application_error" {
  for_each       = toset(local.sanitized_low_severity_keywords) # Use sanitized keywords for resource names
  name           = "${each.key}-metric-filter" # Use sanitized keyword
  log_group_name = local.log_group_name
  # Use original keyword from var for the pattern
  pattern        = "{ ($.log_processed.level = \"WARN\" || $.log_processed.level = \"ERROR\") && (($.log_processed.message = \"*${element(var.low_severity_error_keywords, index(local.sanitized_low_severity_keywords, each.key))}*\") || ($.log_processed.errorMessage = \"*${element(var.low_severity_error_keywords, index(local.sanitized_low_severity_keywords, each.key))}*\")) }"

  metric_transformation {
    name      = "${each.key}_Count" # Use sanitized keyword
    namespace = var.namespace
    value     = "1"
  }
}

# CloudWatch Log Metric Filters for medium severity errors
resource "aws_cloudwatch_log_metric_filter" "medium_severity_application_error" {
  for_each       = toset(local.sanitized_medium_severity_keywords) # Use sanitized
  name           = "${each.key}-metric-filter" # Use sanitized
  log_group_name = local.log_group_name
  # Use original keyword from var for the pattern
  pattern        = "{ $.log_processed.level = \"ERROR\" && ($.log_processed.errorMessage = \"*${element(var.medium_severity_error_keywords, index(local.sanitized_medium_severity_keywords, each.key))}*\") }"

  metric_transformation {
    name      = "${each.key}_Count" # Use sanitized
    namespace = var.namespace
    value     = "1"
  }
}

# CloudWatch Log Metric Filters for high severity errors
resource "aws_cloudwatch_log_metric_filter" "high_severity_application_error" {
  for_each       = toset(local.sanitized_high_severity_keywords) # Use sanitized
  name           = "${each.key}-metric-filter" # Use sanitized
  log_group_name = local.log_group_name
  # Use original keyword from var for the pattern
  pattern        = "{ $.log_processed.level = \"ERROR\" && ($.log_processed.errorMessage = \"*${element(var.high_severity_error_keywords, index(local.sanitized_high_severity_keywords, each.key))}*\") }"

  metric_transformation {
    name      = "${each.key}_Count" # Use sanitized
    namespace = var.namespace
    value     = "1"
  }
}

# CloudWatch Alarms for low severity errors
resource "aws_cloudwatch_metric_alarm" "low_severity_application_error_alarms" {
  for_each            = toset(local.sanitized_low_severity_keywords) # Use sanitized
  alarm_name          = "${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-${each.key}" # Use sanitized
  # Use original keyword for description
  alarm_description   = "${element(var.low_severity_error_keywords, index(local.sanitized_low_severity_keywords, each.key))} error has occurred in the log events."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.evaluation_periods
  period              = var.period
  threshold           = var.threshold
  statistic           = "Sum"
  metric_name         = aws_cloudwatch_log_metric_filter.low_severity_application_error[each.key].metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.low_severity_application_error[each.key].metric_transformation[0].namespace
  alarm_actions       = [aws_lambda_function.payment_hub_observability_lambda.arn]
  ok_actions          = [aws_lambda_function.payment_hub_observability_lambda.arn]
  insufficient_data_actions = []

  tags = {
    callout         = var.callout
    severity        = "Low"
    type            = "Low severity Payment-Hub application error"
    incidentgroup   = var.tag_support_group
    SupportGroup    = var.tag_support_group
    AppGroupEmail   = var.tag_app_group_email
    EnvironmentType = var.env_code_lower == "p" ? "Production" : "Test"
    Name            = "${var.alarm_prefix}-${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-Low severity application error-test-module"
    LogGroupName    = local.log_group_name # Added
    ErrorKeyword    = element(var.low_severity_error_keywords, index(local.sanitized_low_severity_keywords, each.key)) # Added (original keyword)
    AlarmCategory   = "Application" # Added
  }
}

# CloudWatch Alarms for medium severity errors
resource "aws_cloudwatch_metric_alarm" "medium_severity_application_error_alarms" {
  for_each            = toset(local.sanitized_medium_severity_keywords) # Use sanitized
  alarm_name          = "${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-${each.key}" # Use sanitized
  # Use original keyword for description
  alarm_description   = "${element(var.medium_severity_error_keywords, index(local.sanitized_medium_severity_keywords, each.key))} error has occurred in the log events."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.evaluation_periods
  period              = var.period
  threshold           = var.threshold
  statistic           = "Sum"
  metric_name         = aws_cloudwatch_log_metric_filter.medium_severity_application_error[each.key].metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.medium_severity_application_error[each.key].metric_transformation[0].namespace
  alarm_actions       = [aws_lambda_function.payment_hub_observability_lambda.arn]
  ok_actions          = [aws_lambda_function.payment_hub_observability_lambda.arn]
  insufficient_data_actions = []

  tags = {
    callout         = var.callout
    severity        = "Medium"
    type            = "Medium severity Payment-Hub application error"
    incidentgroup   = var.tag_support_group
    SupportGroup    = var.tag_support_group
    AppGroupEmail   = var.tag_app_group_email
    EnvironmentType = var.env_code_lower == "p" ? "Production" : "Test"
    Name            = "${var.alarm_prefix}-${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-Medium severity application error"
    LogGroupName    = local.log_group_name # Added
    ErrorKeyword    = element(var.medium_severity_error_keywords, index(local.sanitized_medium_severity_keywords, each.key)) # Added (original keyword)
    AlarmCategory   = "Application" # Added
  }
}

# CloudWatch Alarms for high severity errors
resource "aws_cloudwatch_metric_alarm" "high_severity_application_error_alarms" {
  for_each            = toset(local.sanitized_high_severity_keywords) # Use sanitized
  alarm_name          = "${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-${each.key}" # Use sanitized
  # Use original keyword for description
  alarm_description   = "${element(var.high_severity_error_keywords, index(local.sanitized_high_severity_keywords, each.key))} error has occurred in the log events."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.evaluation_periods
  period              = var.period
  threshold           = var.threshold
  statistic           = "Sum"
  metric_name         = aws_cloudwatch_log_metric_filter.high_severity_application_error[each.key].metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.high_severity_application_error[each.key].metric_transformation[0].namespace
  alarm_actions       = [aws_lambda_function.payment_hub_observability_lambda.arn]
  ok_actions          = [aws_lambda_function.payment_hub_observability_lambda.arn]
  insufficient_data_actions = []

  tags = {
    callout         = var.callout
    severity        = "High"
    type            = "High severity Payment-Hub application error"
    incidentgroup   = var.tag_support_group
    SupportGroup    = var.tag_support_group
    AppGroupEmail   = var.tag_app_group_email
    EnvironmentType = var.env_code_lower == "p" ? "Production" : "Test"
    Name            = "${var.alarm_prefix}-${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-High severity application error"
    LogGroupName    = local.log_group_name # Added
    ErrorKeyword    = element(var.high_severity_error_keywords, index(local.sanitized_high_severity_keywords, each.key)) # Added (original keyword)
    AlarmCategory   = "Application" # Added
  }
}

# -------- Lambda ------------

# Archive the Lambda code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda_function_payload.zip"
}

# IAM Role for Lambda
resource "aws_iam_role" "payment_hub_observability_lambda_role" {
  name = "payment_hub_observability-${data.aws_region.current.name}"
  tags = merge(local.standard_tags, {
    "Name" = "payment_hub_observability"
  })

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "payment_hub_observability_lambda_policy" {
  name = "payment_hub_observability_lambda_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # KMS permissions
      {
        Effect = "Allow"
        Action = [
          "kms:GenerateDataKey",
          "kms:Decrypt",
        ]
        Resource = "*"
      },
      # CloudWatch Logs permissions
      {
        Effect = "Allow"
        Action = [
          "logs:FilterLogEvents",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      # CloudWatch permissions
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:ListTagsForResource",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:DescribeAlarmsForMetric",
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:PutMetricData",
          "cloudwatch:DescribeAlarmHistory",
          "cloudwatch:EnableAlarmActions",
          "cloudwatch:DisableAlarmActions"
        ]
        Resource = "*"
      },
      # SNS permissions
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "sns:ListTopics"
        ]
        Resource = "*"
      },
      # EC2 permissions
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      },
      # Resource Groups permissions
      {
        Effect = "Allow"
        Action = [
          "resource-groups:GetGroup",
          "resource-groups:GetTags"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "payment_hub_observability_lambda_policy_attachment" {
  name       = "payment_hub_observability_lambda_policy_attachment"
  roles      = [aws_iam_role.payment_hub_observability_lambda_role.name]
  policy_arn = aws_iam_policy.payment_hub_observability_lambda_policy.arn
}

resource "aws_iam_policy_attachment" "lambda_basic_execution_policy_attachment" {
  name       = "lambda-basic-execution-policy-attachment"
  roles      = [aws_iam_role.payment_hub_observability_lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "payment_hub_observability_lambda_log_group" {
  name              = "/aws/lambda/payment_hub_observability_lambda"
  retention_in_days = 7
  tags = merge(local.standard_tags, {
    "Name" = "payment_hub_observability_log_group"
  })
}

resource "aws_lambda_function" "payment_hub_observability_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "payment_hub_observability_lambda" # Consider making this dynamic e.g. using var.project_name
  role             = aws_iam_role.payment_hub_observability_lambda_role.arn
  handler          = "app-error.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  tags = merge(local.standard_tags, {
    "Name" = "payment_hub_observability_lambda"
  })
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  for_each = merge(
    aws_cloudwatch_metric_alarm.low_severity_application_error_alarms,
    aws_cloudwatch_metric_alarm.medium_severity_application_error_alarms,
    aws_cloudwatch_metric_alarm.high_severity_application_error_alarms
  )

  statement_id = "AllowExecutionFromCloudWatch-${substr(replace(each.key, "/[^a-zA-Z0-9_-]/", "_"), 0, 50)}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.payment_hub_observability_lambda.function_name
  principal     = "lambda.alarms.cloudwatch.amazonaws.com"
  source_account = data.aws_caller_identity.current.account_id
  source_arn    = each.value.arn
}
