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
}

# CloudWatch Log Metric Filters for low severity errors
resource "aws_cloudwatch_log_metric_filter" "low_severity_application_error" {
  for_each       = toset(local.sanitized_low_severity_keywords)
  name           = "${each.key}-metric-filter"
  log_group_name = local.log_group_name
  pattern        = "{ ($.log_processed.level = \"WARN\" || $.log_processed.level = \"ERROR\") && (($.log_processed.message = \"*${each.key}*\") || ($.log_processed.errorMessage = \"*${each.key}*\")) }"
  
  metric_transformation {
    name      = "${each.key}_Count"
    namespace = var.namespace
    value     = "1"
  }
}

# CloudWatch Log Metric Filters for medium severity errors
resource "aws_cloudwatch_log_metric_filter" "medium_severity_application_error" {
  for_each       = toset(local.sanitized_medium_severity_keywords)
  name           = "${each.key}-metric-filter"
  log_group_name = local.log_group_name
  pattern        = "{ $.log_processed.level = \"ERROR\" && ($.log_processed.errorMessage = \"*${each.key}*\") }"
  
  metric_transformation {
    name      = "${each.key}_Count"
    namespace = var.namespace
    value     = "1"
  }
}

# CloudWatch Log Metric Filters for high severity errors
resource "aws_cloudwatch_log_metric_filter" "high_severity_application_error" {
  for_each       = toset(local.sanitized_high_severity_keywords)
  name           = "${each.key}-metric-filter"
  log_group_name = local.log_group_name
  pattern        = "{ $.log_processed.level = \"ERROR\" && ($.log_processed.errorMessage = \"*${each.key}*\") }"
  
  metric_transformation {
    name      = "${each.key}_Count"
    namespace = var.namespace
    value     = "1"
  }
}

# CloudWatch Alarms for low severity errors
resource "aws_cloudwatch_metric_alarm" "low_severity_application_error_alarms" {
  for_each            = toset(local.sanitized_low_severity_keywords)
  alarm_name          = "${var.alarm_prefix}-Application-Error-${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-${each.key}-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.evaluation_periods
  period              = var.period
  threshold           = var.threshold
  statistic           = "Sum"
  alarm_description   = "${each.key} error has occurred in the log events."
  metric_name         = aws_cloudwatch_log_metric_filter.low_severity_application_error[each.key].metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.low_severity_application_error[each.key].metric_transformation[0].namespace
  alarm_actions       = data.aws_lambda_function.fis_monitoring.*.arn
  ok_actions          = data.aws_lambda_function.fis_monitoring.*.arn
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
  }
}

# CloudWatch Alarms for medium severity errors
resource "aws_cloudwatch_metric_alarm" "medium_severity_application_error_alarms" {
  for_each            = toset(local.sanitized_medium_severity_keywords)
  alarm_name          = "${var.alarm_prefix}-Application-Error-${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-${each.key}-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.evaluation_periods
  period              = var.period
  threshold           = var.threshold
  statistic           = "Sum"
  alarm_description   = "${each.key} error has occurred in the log events."
  metric_name         = aws_cloudwatch_log_metric_filter.medium_severity_application_error[each.key].metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.medium_severity_application_error[each.key].metric_transformation[0].namespace
  alarm_actions       = data.aws_lambda_function.fis_monitoring.*.arn
  ok_actions          = data.aws_lambda_function.fis_monitoring.*.arn
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
  }
}

# CloudWatch Alarms for high severity errors
resource "aws_cloudwatch_metric_alarm" "high_severity_application_error_alarms" {
  for_each            = toset(local.sanitized_high_severity_keywords)
  alarm_name          = "${var.alarm_prefix}-Application-Error-${var.cus_short_lower}-${var.app_short_lower}-${var.env_short_lower}-${each.key}-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.evaluation_periods
  period              = var.period
  threshold           = var.threshold
  statistic           = "Sum"
  alarm_description   = "${each.key} error has occurred in the log events."
  metric_name         = aws_cloudwatch_log_metric_filter.high_severity_application_error[each.key].metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.high_severity_application_error[each.key].metric_transformation[0].namespace
  alarm_actions       = data.aws_lambda_function.fis_monitoring.*.arn
  ok_actions          = data.aws_lambda_function.fis_monitoring.*.arn
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
  }
}
