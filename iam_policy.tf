resource "aws_iam_role_policy" "optimizer_lambda_policy" {
  name = "CostOptimizerLambdaPolicy"
  role = aws_iam_role.optimizer_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        # Logging permissions 
        "Sid": "Logging",
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:*:*:*"
      },
      {
        # EC2 permissions 
        "Sid": "EC2ReadOptimize",
        "Effect": "Allow",
        "Action": [
          "ec2:DescribeInstances",
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots",
          "ec2:DescribeAddresses",
          "ec2:DescribeNetworkInterfaces", 
          "ec2:DescribeTags",
          "ec2:DescribeSecurityGroups",   
          "ec2:DescribeNatGateways",      
          # --- Actions (only performed if not DRY_RUN) ---
          #"ec2:TerminateInstances",
          #"ec2:DeleteVolume",
          #"ec2:ModifyVolume",
          #"ec2:DeleteSnapshot",
          #"ec2:ReleaseAddress"
        ],
        "Resource": "*"
      },
      {
        # ELB permissions 
        "Sid": "ELBOptimize",
        "Effect": "Allow",
        "Action": [
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTags",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeTargetHealth",
          # Action
          #"elasticloadbalancing:DeleteLoadBalancer"
        ],
        "Resource": "*"
      },
      {
        # CloudWatch permissions 
        "Sid": "CloudWatchRead",
        "Effect": "Allow",
        "Action": [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:DescribeAlarmHistory",
          "cloudwatch:ListTagsForResource"
        ],
        "Resource": "*"
      },
      {
        # CloudWatch Logs permissions 
        "Sid": "CloudWatchLogsOptimize",
        "Effect": "Allow",
        "Action": [
          "logs:DescribeLogGroups",
          "logs:ListTagsLogGroup",
          # Action
          #"logs:PutRetentionPolicy"
        ],
        "Resource": "*"
      },
      {
        # RDS permissions 
        "Sid": "RDSOptimize",
        "Effect": "Allow",
        "Action": [
          "rds:DescribeDBInstances",
          "rds:DescribeDBSnapshots",
          "rds:ListTagsForResource",
          "rds:DescribeDBClusters",
          "rds:DescribeDBClusterSnapshots",
          # Actions
          #"rds:ModifyDBInstance",
          #"rds:ModifyDBCluster",
          #"rds:DeleteDBSnapshot",
          #"rds:DeleteDBClusterSnapshot"
        ],
        "Resource": "*"
      },
      {
        "Sid": "KMSAccess",
        "Effect": "Allow",
        "Action": ["kms:Decrypt", "kms:DescribeKey"],
        "Resource": "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
      },
      {
        # S3 permissions 
        "Sid": "S3Optimize",
        "Effect": "Allow",
        "Action": [
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "s3:GetBucketTagging",
          "s3:GetBucketVersioning",
          "s3:ListBucket",
          "s3:GetObject",
          #"s3:DeleteObject",
          "s3:PutObject" 
        ],
        "Resource": [
          "arn:aws:s3:::*",
          "arn:aws:s3:::*/*"
        ]
      },
      {
        # SNS permissions 
        "Sid": "SNSPublish",
        "Effect": "Allow",
        "Action": [ "sns:Publish" ],
        "Resource": "*" 
      },
      {
        # Pricing API access (Existing)
        "Sid": "PricingAccess",
        "Effect": "Allow",
        "Action": [ "pricing:GetProducts" ],
        "Resource": "*"
      },
      {
        # Lambda/EKS Reporting permissions
        "Sid": "LambdaEKSReporting", 
        "Effect": "Allow",
        "Action": [
          "lambda:ListFunctions",
          "lambda:ListTags",
          "eks:ListClusters",
          "eks:DescribeCluster",
          "eks:DescribeAddonVersions",
          "eks:ListNodegroups",
          "eks:ListFargateProfiles",
          "eks:ListTagsForResource" 
        ],
        "Resource": "*"
      },
      {
        # Compute Optimizer permissions (Required for EC2 rightsizing)
        "Sid": "ComputeOptimizerRead",
        "Effect": "Allow",
        "Action": [
          "compute-optimizer:GetEC2InstanceRecommendations",
          "compute-optimizer:Get*Recommendations"
        ],
        "Resource": "*"
      }
    ]
  })
}
