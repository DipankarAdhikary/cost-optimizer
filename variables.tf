variable "schedule_expression" {
  description = "Cron expression for how often the Lambda should run (e.g., 'cron(0 12 ? * SUN *)' for noon UTC every Sunday)."
  type        = string
  default     = "cron(0 12 ? * SUN *)" # Default: Weekly Sunday Noon UTC
}

variable "lambda_timeout" {
  description = "Timeout for the Lambda function in seconds."
  type        = number
  default     = 900 # 15 minutes
}

variable "lambda_memory_size" {
  description = "Memory allocation for the Lambda function in MB."
  type        = number
  default     = 256
}

variable "log_retention_in_days" {
  description = "Retention period for the Lambda function's CloudWatch Log Group."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags to apply to the created resources (Lambda, IAM role, etc.)."
  type        = map(string)
  default     = {}
}

variable "dry_run" {
  description = "If true, Lambda reports actions without performing them. HIGHLY RECOMMENDED to start with true."
  type        = bool
  default     = true
}

variable "target_regions" {
  description = "List of AWS regions to scan. If empty, uses the Lambda's default region."
  type        = list(string)
  default     = ["us-east-1", "eu-west-1"] # Example: ["us-east-1", "eu-west-1"]
}

variable "project_name" {
  description = "Name of the project for resource naming."
  type        = string
  default     = "cloud-infra-cost-optimizer"
}

variable "report_bucket_name" {
  description = "Name of the S3 bucket for storing reports."
  type        = string
  default     = "cloud-infra-cost-optimizer-reports"
  # Note: The bucket name must be globally unique across all AWS accounts and regions.
}

variable "sns_topic_name" {
  description = "Name of the SNS topic for notifications."
  type        = string
  default     = "cloud-infra-cost-optimizer-notifications"
}

# --- Service Specific Flags & Settings ---

variable "enable_ec2_termination" {
  description = "Enable termination of old stopped EC2 instances."
  type        = bool
  default     = true
}

variable "ec2_stopped_days_threshold" {
  description = "Terminate EC2 instances stopped for more than this number of days."
  type        = number
  default     = 7
}

variable "enable_ec2_instance_type_optimization_reporting" {
  description = "Enable reporting of non-optimal instance types using older generation checks and Compute Optimizer (if available)." # Updated description
  type        = bool
  default     = true
}

variable "enable_ebs_gp2_to_gp3_conversion" {
  description = "Enable automatic conversion of GP2 volumes to GP3. WARNING: May require instance stop/start for root volumes."
  type        = bool
  default     = true
}

variable "enable_ebs_gp2_to_gp3_conversion_for_root" {
  description = "Enable conversion of GP2 root volumes to GP3. WARNING: May require instance stop/start."
  type        = bool
  default     = false
}

variable "enable_ebs_available_volume_deletion" {
  description = "Enable deletion of 'available' (unattached) EBS volumes."
  type        = bool
  default     = true
}

variable "ebs_snapshot_retention_days" {
  description = "Delete EBS snapshots older than this number of days."
  type        = number
  default     = 30
}

variable "enable_ebs_snapshot_deletion" {
  description = "Enable deletion of old EBS snapshots."
  type        = bool
  default     = true
}

variable "enable_elb_deletion" {
  description = "Enable deletion of idle Load Balancers (ALB/NLB)." 
  type        = bool
  default     = true
}

variable "elb_idle_days_threshold" {
  description = "Delete Load Balancers with negligible activity for this many days."
  type        = number
  default     = 30
}

variable "enable_eip_release" {
  description = "Enable release of unattached Elastic IPs."
  type        = bool
  default     = true
}

variable "enable_cw_log_group_retention_management" {
  description = "Enable setting retention periods on CloudWatch Log Groups."
  type        = bool
  default     = true
}

variable "cw_log_group_retention_prod_uat_days" {
  description = "Retention period (days) for Prod/UAT environment log groups."
  type        = number
  default     = 90
}

variable "cw_log_group_retention_dev_days" {
  description = "Retention period (days) for Dev environment log groups."
  type        = number
  default     = 7
}

variable "cw_log_group_retention_default_days" {
  description = "Default retention if environment cannot be determined or if it's not Prod/UAT/Dev."
  type        = number
  default     = 90
}

variable "environment_tag_key" {
  description = "The tag key used to identify the environment (e.g., 'Environment', 'env'). Used for CW Log retention."
  type        = string
  default     = "Environment"
}

variable "environment_values_prod" {
  description = "List of tag values identifying Production environments."
  type        = list(string)
  default     = ["prod", "production"]
}

variable "environment_values_uat" {
  description = "List of tag values identifying UAT environments."
  type        = list(string)
  default     = ["uat", "staging","test"]
}

variable "environment_values_dev" {
  description = "List of tag values identifying Development environments."
  type        = list(string)
  default     = ["dev", "development"]
}

variable "enable_cw_insufficient_data_alarm_reporting" {
  description = "Enable reporting of CloudWatch Alarms in INSUFFICIENT_DATA state for a long time. Does NOT delete them."
  type        = bool
  default     = true
}

variable "cw_alarm_insufficient_data_days_threshold" {
  description = "Report alarms in INSUFFICIENT_DATA state for longer than this many days."
  type        = number
  default     = 30
}


variable "enable_rds_backup_retention_adjustment" {
  description = "Enable adjusting RDS automated backup retention period."
  type        = bool
  default     = true
}

variable "rds_max_backup_retention_days" {
  description = "Maximum automated backup retention period (days) for RDS instances/clusters." 
  type        = number
  default     = 7
}

variable "enable_rds_manual_snapshot_deletion" {
  description = "Enable deletion of old MANUAL RDS snapshots."
  type        = bool
  default     = true
}

variable "rds_manual_snapshot_retention_days" {
  description = "Delete MANUAL RDS snapshots older than this number of days."
  type        = number
  default     = 7
}

variable "enable_s3_object_deletion" {
  description = "Enable deletion of old objects in S3 buckets tagged for cleanup. HIGHLY DANGEROUS. Use with extreme caution and specific tags."
  type        = bool
  default     = false
}

variable "s3_cleanup_tag_key" {
  description = "Tag key to identify S3 buckets where old object deletion should occur."
  type        = string
  default     = "cost-optimizer-cleanup-objects"
}

variable "s3_cleanup_tag_value" {
  description = "Tag value required on the bucket (matching s3_cleanup_tag_key) to enable object deletion."
  type        = string
  default     = "true"
}

variable "s3_object_age_days_threshold" {
  description = "Delete objects in tagged S3 buckets older than this many days based on LastModified date."
  type        = number
  default     = 30
}

variable "optimization_exclude_tag_key" {
  description = "Tag key used to explicitly exclude resources from optimization actions."
  type        = string
  default     = "cost-optimizer-exclude"
}

variable "optimization_exclude_tag_value" {
  description = "Tag value (matching optimization_exclude_tag_key) to exclude a resource."
  type        = string
  default     = "true"
}

variable "sns_subscription_email" {
  description = "Email address to subscribe to the SNS topic for receiving notifications."
  type        = string
  default     = "" # Optional: Leave empty if no subscription is required
}

variable "ec2_rightsize_check_days" {
  description = "Number of days of CloudWatch metrics / Compute Optimizer lookback period to analyze for EC2 rightsizing checks."
  type        = number
  default     = 14
}

# EBS Idle Volume Reporting
variable "enable_ebs_idle_volume_reporting" {
  description = "Enable reporting of potentially idle EBS volumes (based on high VolumeIdleTime)."
  type        = bool
  default     = true
}

variable "ebs_idle_time_threshold_percent" {
  description = "Report EBS volumes with average VolumeIdleTime percentage above this threshold."
  type        = number
  default     = 99 # High percentage indicates very little activity
}

variable "ebs_idle_check_days" {
  description = "Number of days of CloudWatch metrics to analyze for EBS idle checks."
  type        = number
  default     = 14
}

# RDS Rightsizing Reporting
variable "enable_rds_low_cpu_reporting" {
  description = "Enable reporting of RDS instances with sustained low CPU utilization."
  type        = bool
  default     = true
}

variable "rds_low_cpu_threshold_percent" {
  description = "Report RDS instances with average CPU below this percentage over the check period."
  type        = number
  default     = 10
}

variable "rds_rightsize_check_days" {
  description = "Number of days of CloudWatch metrics to analyze for RDS rightsizing checks."
  type        = number
  default     = 14
}

# NAT Gateway Reporting
variable "enable_nat_gateway_idle_reporting" {
  description = "Enable reporting of potentially idle NAT Gateways based on low processed bytes."
  type        = bool
  default     = true
}

variable "nat_idle_check_days" {
  description = "Number of days of CloudWatch metrics to analyze for NAT Gateway idle checks."
  type        = number
  default     = 30
}

variable "nat_bytes_processed_threshold" {
  description = "Report NAT Gateways processing fewer bytes than this threshold over the check period."
  type        = number
  default     = 1073741824 # Default: 1 GB (1 * 1024^3)
}

# Security Group Reporting
variable "enable_unused_security_group_reporting" {
  description = "Enable reporting of potentially unused Security Groups (basic check, requires verification)."
  type        = bool
  default     = true
}

# Lambda Idle Reporting
variable "enable_lambda_idle_reporting" {
  description = "Enable reporting of potentially idle Lambda functions."
  type        = bool
  default     = true
}

variable "lambda_idle_days_threshold" {
  description = "Number of days to check for Lambda invocations."
  type        = number
  default     = 30
}

variable "lambda_idle_invocation_threshold" {
  description = "Report Lambdas with fewer than this many invocations over the threshold period."
  type        = number
  default     = 5
}

# EKS Unused Reporting
variable "enable_eks_unused_cluster_reporting" {
  description = "Enable reporting of potentially unused EKS clusters (basic check)."
  type        = bool
  default     = true
}

variable "enable_ec2_low_cpu_reporting" {
  description = "Enable reporting of EC2 instances with sustained low CPU utilization."
  type        = bool
  default     = true # Or false if you prefer it off by default
}

variable "ec2_low_cpu_threshold_percent" {
  description = "Report EC2 instances with average CPU below this percentage over the check period."
  type        = number
  default     = 10
}