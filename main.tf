terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}


# Archive the Lambda code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda_function_payload.zip"
}

# IAM Role for Lambda
resource "aws_iam_role" "optimizer_lambda_role" {
  name = "CostOptimizerLambdaRole-${data.aws_region.current.name}"
  tags = merge(local.standard_tags, {
    "Name" = "Cost-optimizer-iam-role"
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


# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "optimizer_lambda_log_group" {
  name              = "/aws/lambda/cost-optimizer-lambda"
  retention_in_days = var.log_retention_in_days
  tags = merge(local.standard_tags, {
    "Name" = "Cost-optimizer-log-group"
  })
}

resource "aws_lambda_function" "cost_optimizer_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "cost-optimizer-lambda" # Consider making this dynamic e.g. using var.project_name
  role             = aws_iam_role.optimizer_lambda_role.arn
  handler          = "optimizer_lambda.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  tags = merge(local.standard_tags, {
    "Name" = "Cost-optimizer-lambda"
  })

  # Pass configuration as environment variables
  environment {
    variables = {
      DRY_RUN                                     = var.dry_run
      TARGET_REGIONS                              = join(",", var.target_regions)
      REPORT_BUCKET_NAME                          = aws_s3_bucket.report_bucket.id
      REPORT_KEY_PREFIX                           = "cost-optimizer-reports/"
      SNS_TOPIC_ARN                               = aws_sns_topic.notifications.arn
      ENABLE_EC2_TERMINATION                      = var.enable_ec2_termination
      EC2_STOPPED_DAYS_THRESHOLD                  = var.ec2_stopped_days_threshold
      ENABLE_EC2_INSTANCE_TYPE_OPTIMIZATION_REPORTING = var.enable_ec2_instance_type_optimization_reporting
      ENABLE_EBS_GP2_TO_GP3_CONVERSION            = var.enable_ebs_gp2_to_gp3_conversion
      ENABLE_EBS_GP2_TO_GP3_CONVERSION_FOR_ROOT   = var.enable_ebs_gp2_to_gp3_conversion_for_root 
      ENABLE_EBS_AVAILABLE_VOLUME_DELETION        = var.enable_ebs_available_volume_deletion
      ENABLE_EBS_SNAPSHOT_DELETION                = var.enable_ebs_snapshot_deletion
      EBS_SNAPSHOT_RETENTION_DAYS                 = var.ebs_snapshot_retention_days
      ENABLE_ELB_DELETION                         = var.enable_elb_deletion
      ELB_IDLE_DAYS_THRESHOLD                     = var.elb_idle_days_threshold
      ENABLE_EIP_RELEASE                          = var.enable_eip_release
      ENABLE_CW_LOG_GROUP_RETENTION_MANAGEMENT    = var.enable_cw_log_group_retention_management
      CW_LOG_GROUP_RETENTION_PROD_UAT_DAYS        = var.cw_log_group_retention_prod_uat_days
      CW_LOG_GROUP_RETENTION_DEV_DAYS             = var.cw_log_group_retention_dev_days
      CW_LOG_GROUP_RETENTION_DEFAULT_DAYS         = var.cw_log_group_retention_default_days
      ENVIRONMENT_TAG_KEY                         = var.environment_tag_key
      ENVIRONMENT_VALUES_PROD                     = join(",", var.environment_values_prod)
      ENVIRONMENT_VALUES_UAT                      = join(",", var.environment_values_uat)
      ENVIRONMENT_VALUES_DEV                      = join(",", var.environment_values_dev)
      ENABLE_CW_INSUFFICIENT_DATA_ALARM_REPORTING = var.enable_cw_insufficient_data_alarm_reporting
      CW_ALARM_INSUFFICIENT_DATA_DAYS_THRESHOLD   = var.cw_alarm_insufficient_data_days_threshold
      ENABLE_RDS_BACKUP_RETENTION_ADJUSTMENT      = var.enable_rds_backup_retention_adjustment
      RDS_MAX_BACKUP_RETENTION_DAYS               = var.rds_max_backup_retention_days
      ENABLE_RDS_MANUAL_SNAPSHOT_DELETION         = var.enable_rds_manual_snapshot_deletion
      RDS_MANUAL_SNAPSHOT_RETENTION_DAYS          = var.rds_manual_snapshot_retention_days
      ENABLE_S3_OBJECT_DELETION                   = var.enable_s3_object_deletion
      S3_CLEANUP_TAG_KEY                          = var.s3_cleanup_tag_key
      S3_CLEANUP_TAG_VALUE                        = var.s3_cleanup_tag_value
      S3_OBJECT_AGE_DAYS_THRESHOLD                = var.s3_object_age_days_threshold
      OPTIMIZATION_EXCLUDE_TAG_KEY                = var.optimization_exclude_tag_key
      OPTIMIZATION_EXCLUDE_TAG_VALUE              = var.optimization_exclude_tag_value


      ENABLE_EC2_LOW_CPU_REPORTING                = var.enable_ec2_low_cpu_reporting
      EC2_LOW_CPU_THRESHOLD_PERCENT               = var.ec2_low_cpu_threshold_percent
      EC2_RIGHTSIZE_CHECK_DAYS                    = var.ec2_rightsize_check_days
      ENABLE_EBS_IDLE_VOLUME_REPORTING            = var.enable_ebs_idle_volume_reporting
      EBS_IDLE_TIME_THRESHOLD_PERCENT             = var.ebs_idle_time_threshold_percent
      EBS_IDLE_CHECK_DAYS                         = var.ebs_idle_check_days
      ENABLE_RDS_LOW_CPU_REPORTING                = var.enable_rds_low_cpu_reporting
      RDS_LOW_CPU_THRESHOLD_PERCENT               = var.rds_low_cpu_threshold_percent
      RDS_RIGHTSIZE_CHECK_DAYS                    = var.rds_rightsize_check_days
      ENABLE_NAT_GATEWAY_IDLE_REPORTING           = var.enable_nat_gateway_idle_reporting
      NAT_IDLE_CHECK_DAYS                         = var.nat_idle_check_days
      NAT_BYTES_PROCESSED_THRESHOLD               = var.nat_bytes_processed_threshold
      ENABLE_UNUSED_SECURITY_GROUP_REPORTING      = var.enable_unused_security_group_reporting
      ENABLE_LAMBDA_IDLE_REPORTING                = var.enable_lambda_idle_reporting
      LAMBDA_IDLE_DAYS_THRESHOLD                  = var.lambda_idle_days_threshold
      LAMBDA_IDLE_INVOCATION_THRESHOLD            = var.lambda_idle_invocation_threshold
      ENABLE_EKS_UNUSED_CLUSTER_REPORTING         = var.enable_eks_unused_cluster_reporting
      EKS_EXTENDED_SUPPORT_PRICE_HOURLY           = var.eks_extended_support_price_hourly
    }
  }

  # Ensure logs go to the dedicated group
  depends_on = [aws_cloudwatch_log_group.optimizer_lambda_log_group, aws_iam_role_policy.optimizer_lambda_policy, aws_iam_role.optimizer_lambda_role] # Explicit dependency on policy
}


resource "aws_cloudwatch_event_rule" "optimizer_schedule" {
  name                = "CostOptimizerSchedule"
  description         = "Triggers the Cost Optimizer Lambda function based on schedule"
  schedule_expression = var.schedule_expression
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "optimizer_lambda_target" {
  rule      = aws_cloudwatch_event_rule.optimizer_schedule.name
  target_id = "CostOptimizerLambdaTarget"
  arn       = aws_lambda_function.cost_optimizer_lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_optimizer_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.optimizer_schedule.arn
}

resource "aws_s3_bucket" "report_bucket" {
  bucket = var.report_bucket_name # Ensure this var defines a globally unique name
  tags = merge(local.standard_tags, {
    "Name"           = "cost-optimizer-s3-reporting-bucket",
    "Purpose"        = "Cost Optimization - Reporting",
    "ExpirationDate" = "Never",
    "SLA"            = "99.99",
    "NPI"            = "False"
  }) 
}

resource "aws_s3_bucket_public_access_block" "report_bucket" {
  bucket = aws_s3_bucket.report_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "report_bucket" {
  bucket = aws_s3_bucket.report_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "report_bucket" {
  bucket = aws_s3_bucket.report_bucket.id

  rule {
    id     = "expiration-policy"
    status = "Enabled"
    expiration {
      days = 90
    }
  }
}

# Create an SNS topic for notifications
resource "aws_sns_topic" "notifications" {
  name = var.sns_topic_name
  kms_master_key_id = "alias/aws/sns"
  tags = merge(local.standard_tags, {
    "Name" = "Cost-optimizer-sns-topic"
  })  
}

resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "email"
  endpoint  = var.sns_subscription_email
  count = var.sns_subscription_email != "" ? 1 : 0
}
