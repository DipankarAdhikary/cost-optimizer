import boto3
import os
import logging
import json
import re
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from statistics import mean

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
DRY_RUN = os.environ.get('DRY_RUN', 'true').lower() == 'true'
TARGET_REGIONS_STR = os.environ.get("TARGET_REGIONS", "us-east-1")
TARGET_REGIONS = [region.strip() for region in TARGET_REGIONS_STR.split(',') if region.strip()]
DEFAULT_REGION = os.environ.get('AWS_REGION', 'us-east-1')
EXCLUDE_TAG_KEY = os.environ.get('OPTIMIZATION_EXCLUDE_TAG_KEY', 'cost-optimizer-exclude')
EXCLUDE_TAG_VALUE = os.environ.get('OPTIMIZATION_EXCLUDE_TAG_VALUE', 'true')

# EC2 Config
ENABLE_EC2_TERMINATION = os.environ.get('ENABLE_EC2_TERMINATION', 'true').lower() == 'true'
EC2_STOPPED_DAYS_THRESHOLD = int(os.environ.get('EC2_STOPPED_DAYS_THRESHOLD', '7')) 
ENABLE_EC2_OPTIMIZATION_REPORTING = os.environ.get('ENABLE_EC2_OPTIMIZATION_REPORTING', 'true').lower() == 'true'
EC2_RIGHTSIZE_CHECK_DAYS = int(os.environ.get('EC2_RIGHTSIZE_CHECK_DAYS', '14'))

# EBS Config
ENABLE_EBS_GP2_TO_GP3_CONVERSION = os.environ.get('ENABLE_EBS_GP2_TO_GP3_CONVERSION', 'true').lower() == 'true'
ENABLE_EBS_GP2_TO_GP3_CONVERSION_FOR_ROOT = os.environ.get('ENABLE_EBS_GP2_TO_GP3_CONVERSION_FOR_ROOT', 'false').lower() == 'true'
ENABLE_EBS_AVAILABLE_VOLUME_DELETION = os.environ.get('ENABLE_EBS_AVAILABLE_VOLUME_DELETION', 'true').lower() == 'true'
ENABLE_EBS_SNAPSHOT_DELETION = os.environ.get('ENABLE_EBS_SNAPSHOT_DELETION', 'true').lower() == 'true'
EBS_SNAPSHOT_RETENTION_DAYS = int(os.environ.get('EBS_SNAPSHOT_RETENTION_DAYS', '30')) 
ENABLE_EBS_IDLE_VOLUME_REPORTING = os.environ.get('ENABLE_EBS_IDLE_VOLUME_REPORTING', 'true').lower() == 'true'
EBS_IDLE_TIME_THRESHOLD_PERCENT = int(os.environ.get('EBS_IDLE_TIME_THRESHOLD_PERCENT', '99'))
EBS_IDLE_CHECK_DAYS = int(os.environ.get('EBS_IDLE_CHECK_DAYS', '14')) 

# ELB Config
ENABLE_ELB_DELETION = os.environ.get('ENABLE_ELB_DELETION', 'true').lower() == 'true'
ELB_IDLE_DAYS_THRESHOLD = int(os.environ.get('ELB_IDLE_DAYS_THRESHOLD', '30')) 

# EIP Config
ENABLE_EIP_RELEASE = os.environ.get('ENABLE_EIP_RELEASE', 'true').lower() == 'true'
UNATTACHED_EIP_PRICE_HOURLY = 0.005

# CW Logs Config
ENABLE_CW_LOG_GROUP_RETENTION_MANAGEMENT = os.environ.get('ENABLE_CW_LOG_GROUP_RETENTION_MANAGEMENT', 'true').lower() == 'true'
CW_LOG_GROUP_RETENTION_PROD_UAT_DAYS = int(os.environ.get('CW_LOG_GROUP_RETENTION_PROD_UAT_DAYS', '90'))
CW_LOG_GROUP_RETENTION_DEV_DAYS = int(os.environ.get('CW_LOG_GROUP_RETENTION_DEV_DAYS', '7'))
CW_LOG_GROUP_RETENTION_DEFAULT_DAYS = int(os.environ.get('CW_LOG_GROUP_RETENTION_DEFAULT_DAYS', '30'))
ENVIRONMENT_TAG_KEY = os.environ.get('ENVIRONMENT_TAG_KEY', 'Environment')
ENV_VALUES_PROD = [v.strip().lower() for v in os.environ.get('ENVIRONMENT_VALUES_PROD', 'prod,production').split(',')]
ENV_VALUES_UAT = [v.strip().lower() for v in os.environ.get('ENVIRONMENT_VALUES_UAT', 'uat,staging,stage,test').split(',')]
ENV_VALUES_DEV = [v.strip().lower() for v in os.environ.get('ENVIRONMENT_VALUES_DEV', 'dev,development').split(',')]
CW_LOG_STORAGE_PRICE_GB_MONTH = 0.03

# CW Alarms Config
ENABLE_CW_INSUFFICIENT_DATA_ALARM_REPORTING = os.environ.get('ENABLE_CW_INSUFFICIENT_DATA_ALARM_REPORTING', 'true').lower() == 'true'
CW_ALARM_INSUFFICIENT_DATA_DAYS_THRESHOLD = int(os.environ.get('CW_ALARM_INSUFFICIENT_DATA_DAYS_THRESHOLD', '30')) 

# RDS Config
ENABLE_RDS_BACKUP_RETENTION_ADJUSTMENT = os.environ.get('ENABLE_RDS_BACKUP_RETENTION_ADJUSTMENT', 'true').lower() == 'true'
RDS_MAX_BACKUP_RETENTION_DAYS = int(os.environ.get('RDS_MAX_BACKUP_RETENTION_DAYS', '7'))
ENABLE_RDS_MANUAL_SNAPSHOT_DELETION = os.environ.get('ENABLE_RDS_MANUAL_SNAPSHOT_DELETION', 'true').lower() == 'true'
RDS_MANUAL_SNAPSHOT_RETENTION_DAYS = int(os.environ.get('RDS_MANUAL_SNAPSHOT_RETENTION_DAYS', '7')) 
ENABLE_RDS_LOW_CPU_REPORTING = os.environ.get('ENABLE_RDS_LOW_CPU_REPORTING', 'true').lower() == 'true'
RDS_LOW_CPU_THRESHOLD_PERCENT = int(os.environ.get('RDS_LOW_CPU_THRESHOLD_PERCENT', '10'))
RDS_RIGHTSIZE_CHECK_DAYS = int(os.environ.get('RDS_RIGHTSIZE_CHECK_DAYS', '14')) 
RDS_SNAPSHOT_PRICE_GB_MONTH = 0.05

# S3 Config
ENABLE_S3_OBJECT_DELETION = os.environ.get('ENABLE_S3_OBJECT_DELETION', 'false').lower() == 'true'
S3_CLEANUP_TAG_KEY = os.environ.get('S3_CLEANUP_TAG_KEY', 'cost-optimizer-cleanup-objects')
S3_CLEANUP_TAG_VALUE = os.environ.get('S3_CLEANUP_TAG_VALUE', 'true')
S3_OBJECT_AGE_DAYS_THRESHOLD = int(os.environ.get('S3_OBJECT_AGE_DAYS_THRESHOLD', '30')) 
S3_STANDARD_PRICE_GB_MONTH = 0.023

# Lambda Config
ENABLE_LAMBDA_IDLE_REPORTING = os.environ.get('ENABLE_LAMBDA_IDLE_REPORTING', 'true').lower() == 'true'
LAMBDA_IDLE_DAYS_THRESHOLD = int(os.environ.get('LAMBDA_IDLE_DAYS_THRESHOLD', '30')) # USE DAYS
LAMBDA_IDLE_INVOCATION_THRESHOLD = int(os.environ.get('LAMBDA_IDLE_INVOCATION_THRESHOLD', '5'))

# EKS Config
ENABLE_EKS_UNUSED_CLUSTER_REPORTING = os.environ.get('ENABLE_EKS_UNUSED_CLUSTER_REPORTING', 'true').lower() == 'true'
EKS_CONTROL_PLANE_PRICE_HOURLY = 0.10
EKS_EXTENDED_SUPPORT_PRICE_HOURLY = 0.50

# NAT Gateway Config
ENABLE_NAT_GATEWAY_IDLE_REPORTING = os.environ.get('ENABLE_NAT_GATEWAY_IDLE_REPORTING', 'true').lower() == 'true'
NAT_IDLE_CHECK_DAYS = int(os.environ.get('NAT_IDLE_CHECK_DAYS', '30')) # USE DAYS
NAT_BYTES_PROCESSED_THRESHOLD = int(os.environ.get('NAT_BYTES_PROCESSED_THRESHOLD', 1 * 1024**3))
NAT_GW_PRICE_HOURLY = 0.045

# Security Groups Config
ENABLE_UNUSED_SECURITY_GROUP_REPORTING = os.environ.get('ENABLE_UNUSED_SECURITY_GROUP_REPORTING', 'true').lower() == 'true'


# --- Helper Functions ---

def is_excluded(tags):
    if not tags: return False
    tag_list = tags
    if isinstance(tags, dict): tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
    if not isinstance(tag_list, list): logger.warning(f"Unexpected tag format: {type(tag_list)}."); return False
    for tag in tag_list:
        if isinstance(tag, dict) and tag.get('Key') == EXCLUDE_TAG_KEY and tag.get('Value') == EXCLUDE_TAG_VALUE: return True
    return False

def get_tag_value(tags, key):
    if not tags or not key: return None
    tag_list = tags
    if isinstance(tags, dict): tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
    if not isinstance(tag_list, list): logger.warning(f"Unexpected tag format: {type(tag_list)}."); return None
    for tag in tag_list:
       if isinstance(tag, dict) and tag.get('Key') == key: return tag.get('Value')
    return None

# --- Pricing Helper Functions ---

def get_ec2_instance_price(instance_type, region):
    
    pricing_client = boto3.client('pricing', region_name='us-east-1')
    region_mapping = { 'us-east-1': 'US East (N. Virginia)', 'eu-west-1': 'EU (Ireland)' }
    location = region_mapping.get(region, region)
    try:
        response = pricing_client.get_products( ServiceCode='AmazonEC2', Filters=[ {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type}, {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location}, {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'}, {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'}, {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'}, {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'} ], MaxResults=1 )
        price_list = response.get('PriceList', [])
        if price_list:
            price_item = json.loads(price_list[0]); terms = price_item.get('terms', {}).get('OnDemand', {})
            if terms: term_key = list(terms.keys())[0]; price_dimensions = terms[term_key].get('priceDimensions', {}); price_key = list(price_dimensions.keys())[0]; price_value = price_dimensions[price_key].get('pricePerUnit', {}).get('USD')
            if price_value: return float(price_value)
        logger.warning(f"Could not parse EC2 price for {instance_type} in {region}")
        return None
    except (ClientError, KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError) as e:
        logger.error(f"Error fetching/parsing EC2 pricing for {instance_type} in {region}: {e}")
        return None

def get_ebs_price(volume_type, region):
    
     pricing_client = boto3.client('pricing', region_name='us-east-1')
     region_mapping = { 'us-east-1': 'US East (N. Virginia)', 'eu-west-1': 'EU (Ireland)' }
     location = region_mapping.get(region, region)
     try:
         response = pricing_client.get_products( ServiceCode='AmazonEC2', Filters=[ {'Type': 'TERM_MATCH', 'Field': 'volumeApiName', 'Value': volume_type}, {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location} ], MaxResults=1 )
         price_list = response.get('PriceList', [])
         if price_list:
             price_item = json.loads(price_list[0]); terms = price_item.get('terms', {}).get('OnDemand', {})
             if terms: term_key = list(terms.keys())[0]; price_dimensions = terms[term_key].get('priceDimensions', {}); price_key = list(price_dimensions.keys())[0]; price_value = price_dimensions[price_key].get('pricePerUnit', {}).get('USD')
             if price_value: return float(price_value)
         logger.warning(f"Could not parse EBS price for {volume_type} in {region}")
         return None
     except (ClientError, KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError) as e:
         logger.error(f"Error fetching/parsing EBS pricing for {volume_type} in {region}: {e}")
         return None

def get_ebs_snapshot_price(region):
     # ... (implementation from previous full code) ...
     pricing_client = boto3.client('pricing', region_name='us-east-1')
     region_mapping = { 'us-east-1': 'US East (N. Virginia)', 'eu-west-1': 'EU (Ireland)' }
     location = region_mapping.get(region, region)
     region_prefix_map = { 'us-east-1': 'USE1', 'eu-west-1': 'EU' }
     usage_type_prefix = region_prefix_map.get(region, region.upper().replace('-', ''))
     usage_type = f"{usage_type_prefix}-SnapshotUsage"
     price_value = None
     try:
         response = pricing_client.get_products( ServiceCode='AmazonEC2', Filters=[ {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage Snapshot'}, {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location}, {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': usage_type} ], MaxResults=1 )
         price_list = response.get('PriceList', [])
         if price_list:
              price_item = json.loads(price_list[0]); terms = price_item.get('terms', {}).get('OnDemand', {})
              if terms: term_key = list(terms.keys())[0]; price_dimensions = terms[term_key].get('priceDimensions', {}); price_key = list(price_dimensions.keys())[0]; price_str = price_dimensions[price_key].get('pricePerUnit', {}).get('USD')
              if price_str: price_value = float(price_str)
         if price_value is None:
             logger.warning(f"Snapshot price not found with usage type {usage_type}, trying generic filter.")
             response = pricing_client.get_products( ServiceCode='AmazonEC2', Filters=[ {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage Snapshot'}, {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location} ], MaxResults=1 )
             price_list = response.get('PriceList', [])
             if price_list:
                  price_item = json.loads(price_list[0]); terms = price_item.get('terms', {}).get('OnDemand', {})
                  if terms: term_key = list(terms.keys())[0]; price_dimensions = terms[term_key].get('priceDimensions', {}); price_key = list(price_dimensions.keys())[0]; price_str = price_dimensions[price_key].get('pricePerUnit', {}).get('USD')
                  if price_str: price_value = float(price_str)
         if price_value is None: logger.warning(f"Could not parse EBS snapshot price for {region}")
         return price_value
     except (ClientError, KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError) as e:
         logger.error(f"Error fetching/parsing EBS snapshot pricing for {region}: {e}")
         return None

def get_elb_price(lb_type, region):
     # ... (implementation from previous full code) ...
     pricing_client = boto3.client('pricing', region_name='us-east-1')
     region_mapping = { 'us-east-1': 'US East (N. Virginia)', 'eu-west-1': 'EU (Ireland)' }
     location = region_mapping.get(region, region)
     product_family_map = { 'application': 'Load Balancer-Application', 'network': 'Load Balancer-Network', 'gateway': 'Load Balancer-Gateway' }
     product_family = product_family_map.get(lb_type)
     if not product_family: return None
     region_prefix_map = { 'us-east-1': 'USE1', 'eu-west-1': 'EU' }
     usage_type_prefix = region_prefix_map.get(region, region.upper().replace('-', ''))
     usage_type_attempts = [ f"{usage_type_prefix}-LoadBalancerUsage", "LoadBalancerUsage" ]
     price_value = None
     try:
         for usage_type in usage_type_attempts:
             response = pricing_client.get_products( ServiceCode='AWSELB', Filters=[ {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': product_family}, {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location}, {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': usage_type} ], MaxResults=1 )
             price_list = response.get('PriceList', [])
             if price_list:
                 price_item = json.loads(price_list[0]); terms = price_item.get('terms', {}).get('OnDemand', {})
                 if terms: term_key = list(terms.keys())[0]; price_dimensions = terms[term_key].get('priceDimensions', {}); price_key = list(price_dimensions.keys())[0]; price_str = price_dimensions[price_key].get('pricePerUnit', {}).get('USD')
                 if price_str: price_value = float(price_str); break
             if price_value is not None: break
         if price_value is None: logger.warning(f"Could not parse ELB price for {lb_type} in {region}")
         return price_value
     except (ClientError, KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError) as e:
         logger.error(f"Error fetching/parsing pricing for {lb_type} Load Balancer in {region}: {e}")
         return None

# --- Service Specific Optimization Functions ---

def optimize_ec2(ec2_client, cloudwatch_client, compute_optimizer_client, region, context=None): # Added context for potential account ID lookup
    """Optimize EC2: Terminate old stopped, report old gen & Compute Optimizer findings (Prioritizing Graviton savings)."""
    logger.info(f"--- Starting EC2 Optimization in {region} ---")
    now_utc = datetime.now(timezone.utc)
    results = {
        "savings": 0.0, # Combined savings (Term + CO Graviton Potential)
        "errors": [],
        "terminated_action": {"count": 0, "details": []},
        "older_gen_report": {"count": 0, "details": []},
        "compute_optimizer_report": {"count": 0, "details": []},
        "termination_savings": 0.0,
        "co_potential_savings": 0.0 # Will primarily reflect Graviton savings if found
        }
    instances_to_terminate_ids = []
    terminated_instance_ids = []
    co_potential_savings_accumulator = 0.0 # Accumulator for CO savings

    # --- Terminate Old Stopped Instances ---
    if ENABLE_EC2_TERMINATION:
        try:
            stopped_cutoff_time = now_utc - timedelta(days=EC2_STOPPED_DAYS_THRESHOLD)
            logger.info(f"[{region}] Checking instances stopped before {stopped_cutoff_time.isoformat()}...")
            paginator = ec2_client.get_paginator("describe_instances")
            instances_to_terminate_candidates = []
            # ... (instance identification logic remains the same) ...
            for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]):
                 for res in page["Reservations"]:
                     for inst in res["Instances"]:
                         if is_excluded(inst.get("Tags", [])): continue
                         stop_time = inst.get("UsageOperationUpdateTime"); # ... (rest of stop time logic) ...
                         if 'StateTransitionReason' in inst and 'User initiated' in inst['StateTransitionReason']:
                              try: reason_time_str = inst['StateTransitionReason'].split('(')[-1].split(' GMT)')[0]; stop_time = datetime.strptime(reason_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                              except (IndexError, ValueError): logger.debug(f"Could not parse StateTransitionReason time for {inst['InstanceId']}"); stop_time = inst.get("UsageOperationUpdateTime", inst["LaunchTime"])
                         elif stop_time is None: stop_time = inst["LaunchTime"]
                         if stop_time.tzinfo is None: stop_time = stop_time.replace(tzinfo=timezone.utc)
                         if stop_time < stopped_cutoff_time: instances_to_terminate_candidates.append({"id": inst["InstanceId"], "type": inst["InstanceType"], "stopped_time": stop_time })

            # Calculate termination savings
            for info in instances_to_terminate_candidates:
                 inst_id, inst_type, stop_time_dt = info['id'], info['type'], info['stopped_time']
                 price = get_ec2_instance_price(inst_type, region)
                 term_savings_instance = (price * 24 * 30.44) if price else 0.0
                 if term_savings_instance > 0:
                     results['termination_savings'] += term_savings_instance # Add to specific accumulator
                 detail = f"{inst_id} ({inst_type}) - Stopped ~{stop_time_dt.strftime('%Y-%m-%d')} - Est ${term_savings_instance:.2f}/mo"
                 results['terminated_action']['details'].append(detail)
                 instances_to_terminate_ids.append(inst_id)

            results['terminated_action']['count'] = len(instances_to_terminate_ids)
            # ... (termination execution logic remains the same) ...
            if instances_to_terminate_ids and not DRY_RUN:
                 try: logger.info(f"[{region}] Terminating {len(instances_to_terminate_ids)} instances..."); ec2_client.terminate_instances(InstanceIds=instances_to_terminate_ids); terminated_instance_ids.extend(instances_to_terminate_ids); logger.info(f"[{region}] Successfully initiated termination.")
                 except ClientError as e: logger.error(f"[{region}] Error terminating instances: {e}"); results['errors'].append(f"EC2 Term Err: {e}")
            elif instances_to_terminate_ids: logger.info(f"[DRY RUN] Would terminate {len(instances_to_terminate_ids)} instances.")

        except ClientError as e:
            logger.error(f"[{region}] Error describing stopped instances: {e}")
            results['errors'].append(f"EC2 Desc Stopped Err: {e}")

    # --- Optimization Reporting (Older Gen & Compute Optimizer) ---
    if ENABLE_EC2_OPTIMIZATION_REPORTING:
        try:
            paginator = ec2_client.get_paginator("describe_instances")
            target_ids_terminated = set(instances_to_terminate_ids)
            older_gen_types = ['t2','m1','m2','m3','m4','c1','c3','c4','r3','r4','i2','d2','g2','f1','x1','p2','h1']
            co_arns = []
            logger.info(f"[{region}] Checking running/stopped instances for optimization reports...")
            # ... (ARN collection logic remains the same) ...
            for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]):
                 for res in page["Reservations"]:
                     for inst in res["Instances"]:
                         inst_id = inst["InstanceId"]; inst_type = inst["InstanceType"]; tags = inst.get("Tags", [])
                         if inst_id in target_ids_terminated or is_excluded(tags): continue
                         if inst_type.split('.')[0] in older_gen_types: results['older_gen_report']['details'].append(f"{inst_id}({inst_type})")
                         instance_arn = inst.get('InstanceArn') # ... (rest of ARN construction logic) ...
                         if not instance_arn:
                              account_id = 'unknown-account'; # ... (get account_id from context) ...
                              if context and hasattr(context, 'invoked_function_arn'):
                                   try: account_id = context.invoked_function_arn.split(":")[4]
                                   except IndexError: pass
                              instance_arn = f"arn:aws:ec2:{region}:{account_id}:instance/{inst_id}"
                         co_arns.append(instance_arn)
            results['older_gen_report']['count'] = len(results['older_gen_report']['details'])

            # --- Get Compute Optimizer Recommendations (Manual Pagination) ---
            if co_arns:
                logger.info(f"[{region}] Getting Compute Optimizer recommendations for {len(co_arns)} instances...")
                try:
                    all_recommendations = []
                    # ... (Manual pagination logic using next_token remains the same) ...
                    next_token = None
                    for i in range(0, len(co_arns), 100):
                         batch_arns = co_arns[i:i + 100]; logger.debug(f"[{region}] Requesting CO recs for batch...")
                         while True:
                              request_args = {'instanceArns': batch_arns}; # ... (add next_token if present) ...
                              if next_token: request_args['nextToken'] = next_token
                              try: response = compute_optimizer_client.get_ec2_instance_recommendations(**request_args)
                              except ClientError as e: logger.error(f"[{region}] Error calling CO API: {e}"); results['errors'].append(f"CO API Batch Err: {e}"); break
                              all_recommendations.extend(response.get('instanceRecommendations', []))
                              # ... (Handle response errors) ...
                              if response.get('errors'):
                                   for error in response.get('errors', []): err_id=error.get('identifier','N/A'); err_msg=error.get('message','N/A'); logger.warning(f"[{region}] CO error for {err_id}: {err_msg}"); results['errors'].append(f"CO Rec Err ({err_id}): {err_msg}")
                              next_token = response.get('nextToken')
                              if not next_token: break
                         next_token = None # Reset for next batch

                    logger.info(f"[{region}] Received {len(all_recommendations)} total Compute Optimizer recommendations.")

                    # --- Process Recommendations ---
                    processed_co_ids = set()
                    for rec in all_recommendations:
                        inst_arn = rec.get('instanceArn')
                        if not inst_arn or inst_arn in processed_co_ids: continue
                        processed_co_ids.add(inst_arn)

                        finding = rec.get('finding')
                        inst_id = inst_arn.split('/')[-1]
                        curr_type = rec.get('currentInstanceType', '?')
                        opts = rec.get('recommendationOptions', [])

                        if finding in ['OVER_PROVISIONED', 'UNDER_PROVISIONED', 'OPTIMIZED', 'NOT_OPTIMIZED']:
                            reason_codes = rec.get('findingReasonCodes')
                            reason = reason_codes[0] if reason_codes else 'N/A'

                            # --- Find Graviton and Best Savings Option ---
                            best_overall_savings = 0.0 # Track max savings across all options
                            best_overall_type = "N/A"
                            graviton_savings = 0.0     # Track savings for the first Graviton option found
                            graviton_type = "N/A"
                            options_for_display = []   # Store first few types for context
                            found_graviton = False

                            if opts:
                                for idx, option in enumerate(opts):
                                    current_option_savings = 0.0
                                    current_option_type = option.get('instanceType', '?')
                                    savings_data = option.get('estimatedMonthlySavings', {})

                                    # --- Add Debug Logging ---
                                    logger.debug(f"CO Option for {inst_id}: Idx={idx}, Type={current_option_type}, SavingsData={savings_data}")
                                    # --- End Debug Logging ---

                                    # Parse savings safely
                                    if 'value' in savings_data: current_option_savings = savings_data.get('value', 0.0)
                                    elif 'Value' in savings_data: current_option_savings = savings_data.get('Value', 0.0)
                                    try: current_option_savings = float(current_option_savings)
                                    except (ValueError, TypeError): current_option_savings = 0.0
                                    logger.debug(f"CO Parsed Savings for {current_option_type}: {current_option_savings}") # Log parsed value

                                    # Track the overall best savings
                                    if current_option_savings > best_overall_savings:
                                        best_overall_savings = current_option_savings
                                        best_overall_type = current_option_type

                                    # Track the *first* Graviton option found (ends with 'g', 'gdn', 'gn')
                                    # Make check slightly more robust for different Graviton types
                                    is_graviton = any(current_option_type.endswith(suffix) for suffix in ['g', 'gn', 'gdn'])
                                    if is_graviton and not found_graviton:
                                        graviton_savings = current_option_savings
                                        graviton_type = current_option_type
                                        found_graviton = True
                                        logger.debug(f"Found first Graviton option for {inst_id}: Type={graviton_type}, Savings={graviton_savings}")

                                    # Collect first few types for display
                                    if idx < 3: options_for_display.append(current_option_type)

                            # --- Decide which savings to accumulate and report ---
                            savings_to_add = 0.0
                            primary_rec_type = "N/A"
                            primary_rec_savings = 0.0

                            # Prioritize positive Graviton savings if found
                            if found_graviton and graviton_savings > 0:
                                savings_to_add = graviton_savings
                                primary_rec_type = graviton_type
                                primary_rec_savings = graviton_savings
                                logger.info(f"Prioritizing Graviton savings (${savings_to_add:.2f}) for {inst_id}.")
                            # Otherwise, use the overall best savings if positive
                            elif best_overall_savings > 0:
                                savings_to_add = best_overall_savings
                                primary_rec_type = best_overall_type
                                primary_rec_savings = best_overall_savings
                                logger.info(f"Using best overall savings (${savings_to_add:.2f}) for {inst_id} (Graviton not found or had $0 savings).")
                            else:
                                # If no option yields positive savings, report N/A but still show CO found it
                                primary_rec_type = best_overall_type if best_overall_type != "N/A" else (graviton_type if graviton_type != "N/A" else options_for_display[0] if options_for_display else "N/A") # Show *some* recommended type
                                logger.info(f"No positive savings found for {inst_id}. Best overall type: {best_overall_type}, Graviton type: {graviton_type}")


                            # Add the chosen savings to the accumulator (only if OVER_PROVISIONED)
                            if finding == 'OVER_PROVISIONED' and savings_to_add > 0:
                                co_potential_savings_accumulator += savings_to_add
                            # --- End deciding savings ---

                            # --- Build Detail String ---
                            opts_display_str = ", ".join(options_for_display)
                            savings_display = f"(Save ~${primary_rec_savings:.2f}/mo)" if finding == 'OVER_PROVISIONED' and primary_rec_savings > 0 else ""

                            detail = (f"{inst_id}({curr_type}) - {finding}({reason}), "
                                      f"Rec: {primary_rec_type} {savings_display}, " # Show prioritized recommendation
                                      f"OtherRecs:[{opts_display_str}...]")
                            results['compute_optimizer_report']['details'].append(detail)
                            # --- End Build Detail String ---

                    results['compute_optimizer_report']['count'] = len(results['compute_optimizer_report']['details'])
                    results['co_potential_savings'] = co_potential_savings_accumulator # Store CO savings separately

                except ClientError as e:
                    logger.error(f"[{region}] General ClientError during Compute Optimizer processing: {e}")
                    results['errors'].append(f"CO General ClientErr: {e}")
                except Exception as e:
                    logger.error(f"[{region}] Unexpected error processing Compute Optimizer results: {e}", exc_info=True)
                    results['errors'].append(f"CO Proc Err: {e}")

        except ClientError as e:
            logger.error(f"[{region}] Error during EC2 optimization reporting phase: {e}")
            results['errors'].append(f"EC2 Opt Rept Err: {e}")
        except Exception as e:
             logger.error(f"[{region}] Unexpected error during EC2 optimization reporting: {e}", exc_info=True)
             results['errors'].append(f"EC2 Opt Rept Unexpected Err: {e}")

    # --- Combine Savings and Return ---
    total_ec2_savings = results['termination_savings'] + results['co_potential_savings']
    results['savings'] = total_ec2_savings # Update the main savings key as well

    logger.info(f"[{region}] EC2 Savings Breakdown: Terminations=${results['termination_savings']:.2f}, CO Potential=${results['co_potential_savings']:.2f}, Total=${total_ec2_savings:.2f}")
    logger.info(f"--- Finished EC2 Optimization in {region} ---")

    # Return the results dict and the COMBINED savings value
    return results, total_ec2_savings



def optimize_ebs(ec2_client, cloudwatch_client, region):
    """Optimize EBS: Delete available, convert gp2->gp3, report idle, delete old snapshots."""
    logger.info(f"--- Starting EBS Optimization in {region} ---")
    now_utc = datetime.now(timezone.utc)
    # Initialize structured results
    results = {
        "savings": 0.0,
        "errors": [],
        "deleted_vol_action": {"count": 0, "details": []},
        "converted_vol_action": {"count": 0, "details": []},
        "deleted_snap_action": {"count": 0, "details": []},
        "idle_vol_report": {"count": 0, "details": []} # For idle volume reporting
    }
    # Internal tracking for DRY_RUN vs actual actions
    vol_would_del_ids, vol_would_conv_ids, snap_would_del_ids = [], [], []
    vol_del_ids, vol_conv_ids, snap_del_ids = [], [], []

    # Get prices upfront
    gp2_p, gp3_p, snap_p = get_ebs_price('gp2', region), get_ebs_price('gp3', region), get_ebs_snapshot_price(region)

    # --- 1. Delete available volumes ---
    if ENABLE_EBS_AVAILABLE_VOLUME_DELETION:
        try:
            logger.info(f"[{region}] Checking for 'available' volumes...")
            paginator = ec2_client.get_paginator("describe_volumes"); avail_vols = []
            for page in paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}]):
                for vol in page['Volumes']:
                    if not is_excluded(vol.get("Tags", [])):
                        avail_vols.append({'id':vol['VolumeId'],'size':vol['Size'],'type':vol['VolumeType']})

            results['deleted_vol_action']['count'] = len(avail_vols) # Count potential deletes
            logger.info(f"[{region}] Found {len(avail_vols)} candidate available volumes.")
            for v in avail_vols:
                vp=get_ebs_price(v['type'], region); vs=(v['size']*vp) if vp is not None else 0.0
                if vs > 0: results['savings'] += vs # Add potential savings
                detail=f"{v['id']} ({v['type']}, {v['size']}GB) - Est Savings: ${vs:.2f}/mo"
                results['deleted_vol_action']['details'].append(detail); vol_would_del_ids.append(v['id'])

                # Corrected block for actual deletion
                if not DRY_RUN:
                    try:
                        logger.info(f"[{region}] Deleting available volume {v['id']}...")
                        ec2_client.delete_volume(VolumeId=v['id'])
                        vol_del_ids.append(v['id']) # Track successful deletion
                        logger.info(f"[{region}] Successfully deleted volume {v['id']}.")
                    except ClientError as e:
                        logger.error(f"[{region}] Error deleting volume {v['id']}: {e}")
                        results['errors'].append(f"VolDelErr({v['id']}):{e}")
                        results['savings']-=vs # Subtract savings on failure
        except ClientError as e: results['errors'].append(f"DescAvailVolErr:{e}")

    # --- 2. Convert GP2 to GP3 ---
    processed_for_conversion = set(vol_would_del_ids) # Check against potential deletes
    if ENABLE_EBS_GP2_TO_GP3_CONVERSION:
        try:
            logger.info(f"[{region}] Checking for gp2 volumes to convert...")
            paginator=ec2_client.get_paginator("describe_volumes"); vols_to_conv=[]
            for page in paginator.paginate(Filters=[{'Name':'volume-type','Values':['gp2']}]):
                for vol in page['Volumes']:
                    vol_id=vol['VolumeId']; tags=vol.get("Tags",[])
                    if vol_id in processed_for_conversion or is_excluded(tags): continue
                    is_root = any(a.get('Device') in ['/dev/sda1','/dev/xvda'] for a in vol.get('Attachments',[]))
                    if is_root and not ENABLE_EBS_GP2_TO_GP3_CONVERSION_FOR_ROOT: continue
                    vols_to_conv.append({'id':vol_id, 'size':vol['Size']})

            results['converted_vol_action']['count'] = len(vols_to_conv) # Count potential conversions
            logger.info(f"[{region}] Found {len(vols_to_conv)} candidate gp2 volumes.")
            if gp2_p is not None and gp3_p is not None and gp2_p > gp3_p:
                sav_gb=gp2_p - gp3_p
                logger.info(f"[{region}] Potential savings per GB for gp2->gp3: ${sav_gb:.4f}")
                for v in vols_to_conv:
                    vs=v['size']*sav_gb; results['savings']+=vs # Add potential savings
                    detail=f"{v['id']} ({v['size']}GB) - Est Savings: ${vs:.2f}/mo"
                    results['converted_vol_action']['details'].append(detail); vol_would_conv_ids.append(v['id'])

                    # Corrected block for actual modification
                    if not DRY_RUN:
                        try:
                            logger.info(f"[{region}] Converting gp2 volume {v['id']} to gp3...")
                            ec2_client.modify_volume(VolumeId=v['id'],VolumeType='gp3')
                            vol_conv_ids.append(v['id']) # Track successful action
                            logger.info(f"[{region}] Successfully initiated conversion for {v['id']}.")
                        except ClientError as e:
                            logger.error(f"[{region}] Error modifying volume {v['id']}: {e}")
                            results['errors'].append(f"VolModErr({v['id']}):{e}")
                            results['savings']-=vs # Subtract savings on failure
            else: logger.warning(f"[{region}] Cannot calculate gp2->gp3 savings (pricing missing or no benefit).")
        except ClientError as e: results['errors'].append(f"DescGp2VolErr:{e}")

    # --- 3. Report Idle Volumes ---
    processed_for_idle = processed_for_conversion.union(set(vol_would_conv_ids)) # Skip deleted or converted
    if ENABLE_EBS_IDLE_VOLUME_REPORTING:
         try:
            logger.info(f"[{region}] Checking for idle EBS volumes (IdleTime > {EBS_IDLE_TIME_THRESHOLD_PERCENT}% over {EBS_IDLE_CHECK_DAYS} days)...")
            
            check_start_time = now_utc - timedelta(days=EBS_IDLE_CHECK_DAYS) 
            # check_start_time = now_utc - timedelta(days=EBS_IDLE_CHECK_DAYS) # Days for production
            paginator = ec2_client.get_paginator("describe_volumes")
            page_iterator = paginator.paginate(Filters=[{"Name": "status", "Values": ["in-use"]}])
            idle_vols_found = []

            for page in page_iterator:
                 for volume in page['Volumes']:
                     vol_id = volume['VolumeId']; tags = volume.get("Tags", [])
                     if vol_id in processed_for_idle or is_excluded(tags): continue
                     try:
                         metrics = cloudwatch_client.get_metric_statistics( Namespace='AWS/EBS', MetricName='VolumeIdleTime', Dimensions=[{'Name':'VolumeId','Value':vol_id}], StartTime=check_start_time, EndTime=now_utc, Period=86400, Statistics=['Average'], Unit='Seconds' )
                         avgs = [dp['Average'] for dp in metrics['Datapoints']]
                         if avgs: p_idle=(mean(avgs)/86400)*100 if mean(avgs) is not None else 0
                         else: p_idle = -1 # Indicate no metrics found
                         if p_idle > EBS_IDLE_TIME_THRESHOLD_PERCENT: idle_vols_found.append(f"{vol_id} ({p_idle:.1f}% idle)")
                         elif p_idle < 0: logger.debug(f"No IdleTime metrics for {vol_id}")
                     except (ClientError,KeyError,ValueError,TypeError) as e: results['errors'].append(f"EBSIdleMetricErr({vol_id}):{e}")

            results['idle_vol_report']['count'] = len(idle_vols_found)
            results['idle_vol_report']['details'] = idle_vols_found
            if idle_vols_found: logger.info(f"[{region}] Found {len(idle_vols_found)} potentially idle volumes.")
            else: logger.info(f"[{region}] No potentially idle volumes found.")
         except ClientError as e: results['errors'].append(f"EBSDescInUseErr:{e}")

    # --- 4. Delete old snapshots ---
    if ENABLE_EBS_SNAPSHOT_DELETION:
        try:
            
            cutoff = now_utc - timedelta(days=EBS_SNAPSHOT_RETENTION_DAYS) 
            logger.info(f"[{region}] Checking snapshots older than {cutoff.isoformat()}...")
            paginator = ec2_client.get_paginator("describe_snapshots"); snaps_to_del=[]
            for page in paginator.paginate(OwnerIds=["self"]):
                for snap in page['Snapshots']:
                    desc = snap.get('Description','').lower()
                    if 'createimage' in desc or 'aws backup' in desc or 'dlm lifecycle' in desc: continue
                    snap_id = snap['SnapshotId']
                    if is_excluded(snap.get("Tags",[])): continue
                    if snap['StartTime'] < cutoff: snaps_to_del.append({'id':snap_id,'size':snap['VolumeSize'],'time':snap['StartTime']})

            results['deleted_snap_action']['count'] = len(snaps_to_del) # Count potential deletes
            logger.info(f"[{region}] Found {len(snaps_to_del)} candidate old snapshots.")
            if snap_p is not None:
                for s in snaps_to_del:
                    ss = s['size']*snap_p; results['savings']+=ss # Add potential savings
                    detail=f"{s['id']}(Sz:{s['size']}GB,Created:{s['time']:%Y-%m-%d})-Est ${ss:.2f}/mo"
                    results['deleted_snap_action']['details'].append(detail); snap_would_del_ids.append(s['id'])
                    if not DRY_RUN:
                        try:
                            logger.info(f"Deleting snap {s['id']}. Est ${ss:.2f}")
                            ec2_client.delete_snapshot(SnapshotId=s['id']); snap_del_ids.append(s['id']) # Track actual deletes
                        except ClientError as e:
                            results['errors'].append(f"SnapDelErr({s['id']}):{e}"); results['savings']-=ss # Subtract savings on failure
            else: logger.warning(f"[{region}] Cannot calculate snapshot savings (price unavailable).")
        except ClientError as e: results['errors'].append(f"DescSnapErr:{e}")

    logger.info(f"--- Finished EBS Optimization in {region} ---")

    # Finalize counts based on actual actions if not DRY_RUN
    if not DRY_RUN:
        results['deleted_vol_action']['count'] = len(vol_del_ids)
        results['converted_vol_action']['count'] = len(vol_conv_ids)
        results['deleted_snap_action']['count'] = len(snap_del_ids)
        # Idle report count remains based on identification

    return results, results['savings']

def optimize_load_balancers(elbv2_client, cloudwatch_client, region):
    logger.info(f"--- Starting Load Balancer Optimization in {region} ---")
    results = {"savings": 0.0, "errors": [], "deleted_action": {"count": 0, "details": []}}
    lbs_to_del_info = []; deleted_lb_names = [] # Internal tracking
    if not ENABLE_ELB_DELETION: return {"summary_lines":["ELB deletion disabled."]}, 0.0

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=ELB_IDLE_DAYS_THRESHOLD)
    logger.info(f"[{region}] Checking LBs idle since {cutoff.isoformat()}...")

    try:
        paginator = elbv2_client.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            for lb in page['LoadBalancers']:
                arn, name, type, state = lb['LoadBalancerArn'], lb['LoadBalancerName'], lb['Type'], lb.get('State',{}).get('Code')
                if state != 'active': continue
                try:
                    tags = elbv2_client.describe_tags(ResourceArns=[arn])['TagDescriptions'][0].get('Tags',[])
                    if is_excluded(tags) or type == 'gateway': continue # Skip Gateway LBs

                    metric = 'RequestCount' if type == 'application' else 'ActiveFlowCount'
                    ns = 'AWS/ApplicationELB' if type == 'application' else 'AWS/NetworkELB'

                    # --- START CHANGE ---
                    # Old complex logic:
                    # period = max(60, 3600 if (ELB_IDLE_DAYS_THRESHOLD*60)>=3600 else 300)

                    # New simpler and correct logic: Use a 1-day period for idle checks over multiple days
                    period = 86400 # Period in seconds (86400 seconds = 1 day)
                    # --- END CHANGE ---

                    # Ensure the requested time range isn't excessively long for the period
                    # Although with a 1-day period, 30 days is fine (30 data points << 1440)

                    metrics = cloudwatch_client.get_metric_statistics(
                        Namespace=ns,
                        MetricName=metric,
                        Dimensions=[{'Name':'LoadBalancer','Value':'/'.join(arn.split(':')[-1].split('/')[-3:])}],
                        StartTime=cutoff,
                        EndTime=now_utc,
                        Period=period, # Use the corrected period
                        Statistics=['Sum'],
                        Unit='Count'
                    )
                    count = sum(dp['Sum'] for dp in metrics['Datapoints'])

                    # Check Target Group Health (Existing logic seems okay)
                    tgs = elbv2_client.describe_target_groups(LoadBalancerArn=arn)['TargetGroups']
                    unhealthy = not tgs # No target groups means it's unused
                    if tgs: # Only check health if target groups exist
                        all_targets_unhealthy = True
                        for tg in tgs:
                            try:
                                health_desc = elbv2_client.describe_target_health(TargetGroupArn=tg['TargetGroupArn'])['TargetHealthDescriptions']
                                if not health_desc: # Empty target group is considered unhealthy for this purpose
                                     continue
                                # Check if *any* target in this TG is healthy/initializing/draining
                                if any(t['TargetHealth']['State'] in ['healthy', 'initial', 'draining'] for t in health_desc):
                                    all_targets_unhealthy = False
                                    break # Found a healthy target group, LB is not idle
                            except ClientError as health_err:
                                # Log error checking health but potentially proceed cautiously
                                logger.warning(f"[{region}] Error checking health for TG {tg['TargetGroupArn']} on LB {name}: {health_err}. Skipping health check for this TG.")
                                # Decide if you want to consider this TG unhealthy or skip the LB
                                # For safety, let's assume it might be healthy if we can't check
                                all_targets_unhealthy = False
                                break
                        unhealthy = all_targets_unhealthy

                    # Decision logic: Low request count AND unhealthy targets/no targets
                    if count < 1 and unhealthy:
                        logger.info(f"[{region}] Found idle {type} LB {name} (Requests/Flows: {count}, Unhealthy Targets/No Targets: {unhealthy}).")
                        price = get_elb_price(type, region); savings = (price*24*30.44) if price else 0.0
                        lbs_to_del_info.append({'Arn':arn,'Name':name,'Type':type, 'Savings': savings})
                        if savings > 0: results['savings'] += savings
                    else:
                         logger.debug(f"[{region}] LB {name} ({type}) not idle (Count: {count}, Unhealthy: {unhealthy}).")

                except ClientError as e:
                     # Specific check for the original error to make sure it's gone after the fix
                     if 'InvalidParameterCombination' in str(e) and 'datapoints' in str(e):
                         logger.error(f"[{region}] PERSISTENT DATAPOINT ERROR for LB {name}. Check Period/TimeRange calculation. Error: {e}")
                     else:
                         logger.error(f"[{region}] Error processing LB {name}: {e}")
                     results['errors'].append(f"LB Proc Err ({name}):{e}")
                except Exception as e:
                    logger.error(f"[{region}] Unexpected error processing LB {name}: {e}", exc_info=True)
                    results['errors'].append(f"LB Unexp Err ({name}):{e}")

    except ClientError as e:
        logger.error(f"[{region}] Error describing load balancers: {e}")
        results['errors'].append(f"Desc LBs Err:{e}")

    # (Rest of the deletion logic remains the same)
    results['deleted_action']['count'] = len(lbs_to_del_info)
    if lbs_to_del_info:
        logger.info(f"[{region}] Processing {len(lbs_to_del_info)} LBs for deletion.")
        for lb in lbs_to_del_info:
            arn, name, type, sv = lb['Arn'], lb['Name'], lb['Type'], lb['Savings']
            detail = f"{name} ({type}) - Est Savings: ${sv:.2f}/mo"
            results['deleted_action']['details'].append(detail)
            if not DRY_RUN:
                try:
                    logger.info(f"Deleting {type} LB {name}.")
                    elbv2_client.delete_load_balancer(LoadBalancerArn=arn)
                    deleted_lb_names.append(name)
                except ClientError as e:
                    logger.error(f"[{region}] Error deleting LB {name}: {e}")
                    results['errors'].append(f"LB Del Err ({name}):{e}")
                    results['savings'] -= sv # Rollback savings if deletion fails
        # Update count for non-dry run summary
        if not DRY_RUN: results['deleted_action']['count'] = len(deleted_lb_names)

    logger.info(f"--- Finished Load Balancer Optimization in {region} ---")
    return results, results['savings']

def optimize_elastic_ips(ec2_client, region):
    logger.info(f"--- Starting Elastic IP Optimization in {region} ---")
    results = {"savings": 0.0, "errors": [], "released_action": {"count": 0, "details": []}, "skipped": []}
    if not ENABLE_EIP_RELEASE: return {"summary_lines":["EIP release disabled."]}, 0.0

    to_release_ids = []; released_ids = []
    monthly_cost = UNATTACHED_EIP_PRICE_HOURLY * 24 * 30.44

    try:
        for addr in ec2_client.describe_addresses().get("Addresses",[]):
            alloc_id, ip, tags = addr.get("AllocationId"), addr.get("PublicIp"), addr.get("Tags",[])
            if "AssociationId" in addr: continue
            if is_excluded(tags): results['skipped'].append(ip); continue
            logger.info(f"[{region}] Found unattached EIP: {ip} ({alloc_id}).")
            to_release_ids.append(alloc_id); results['savings'] += monthly_cost
            results['released_action']['details'].append(f"{ip} ({alloc_id}) - Est Savings: ${monthly_cost:.2f}/mo")

        results['released_action']['count'] = len(to_release_ids)
        if to_release_ids and not DRY_RUN:
            logger.info(f"[{region}] Processing {len(to_release_ids)} EIPs.")
            for alloc_id in to_release_ids:
                try: logger.info(f"Releasing EIP {alloc_id}."); ec2_client.release_address(AllocationId=alloc_id); released_ids.append(alloc_id)
                except ClientError as e: results['errors'].append(f"EIP Rel Err ({alloc_id}):{e}"); results['savings'] -= monthly_cost
            results['released_action']['count'] = len(released_ids) # Update count based on actual success
        elif not to_release_ids: logger.info(f"[{region}] No unattached EIPs found.")
    except ClientError as e: results['errors'].append(f"DescAddr Err:{e}")

    logger.info(f"--- Finished Elastic IP Optimization in {region} ---")
    return results, results['savings']


def optimize_cloudwatch_logs(logs_client, region):
    """Set retention periods for CloudWatch Log Groups, reporting $0 savings."""
    logger.info(f"--- Starting CloudWatch Log Group Optimization in {region} ---")
    # Initialize structured results
    results = {
        "savings": 0.0, # Explicitly $0 for CW Logs
        "errors": [],
        "modified_action": {"count": 0, "details": []}, # Details of groups modified
        "skipped": [] # List of skipped group names
    }
    if not ENABLE_CW_LOG_GROUP_RETENTION_MANAGEMENT:
        logger.info(f"[{region}] CW Log Group retention management disabled.")
        # Add a line to results summary if needed
        results['summary_lines'] = ["CW Log Group retention disabled."]
        return results, 0.0

    # Internal tracking
    log_groups_would_modify_names = []
    log_groups_modified_count = 0

    try:
        paginator = logs_client.get_paginator('describe_log_groups')
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for log_group in page.get('logGroups', []):
                lg_name = log_group['logGroupName']
                current_retention = log_group.get('retentionInDays')
                tags = {} # Initialize empty

                # Fetch tags safely
                try:
                    tags_response = logs_client.list_tags_log_group(logGroupName=lg_name)
                    tags = tags_response.get('tags', {}) # Returns dict
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        logger.warning(f"[{region}] LG {lg_name} not found listing tags. Skipping.")
                        continue # Skip this log group
                    else:
                        logger.warning(f"[{region}] Could not list tags for LG {lg_name}: {e}. Proceeding without tag checks.")
                        results['errors'].append(f"TagListErr({lg_name}):{e}")
                        # Continue processing without tags

                # Check Exclusion Tag
                if is_excluded(tags): # is_excluded handles dict or list
                    logger.info(f"[{region}] Skipping excluded Log Group {lg_name}")
                    results['skipped'].append(lg_name)
                    continue

                # Determine target retention
                env_tag_value = tags.get(ENVIRONMENT_TAG_KEY, '').lower()
                target_retention = CW_LOG_GROUP_RETENTION_DEFAULT_DAYS
                if env_tag_value in ENV_VALUES_PROD or env_tag_value in ENV_VALUES_UAT:
                    target_retention = CW_LOG_GROUP_RETENTION_PROD_UAT_DAYS
                elif env_tag_value in ENV_VALUES_DEV:
                    target_retention = CW_LOG_GROUP_RETENTION_DEV_DAYS

                # Apply retention if needed
                needs_update = False
                original_retention_str = "'Never expire'" if current_retention is None else f"{current_retention} days"
                if current_retention is None or current_retention > target_retention:
                    needs_update = True
                    # Log intention regardless of DRY_RUN
                    logger.info(f"[{region}] LG {lg_name} retention {original_retention_str} needs update to {target_retention} days.")

                if needs_update:
                    detail = f"{lg_name}: {original_retention_str} -> {target_retention} days"
                    results['modified_action']['details'].append(detail)
                    log_groups_would_modify_names.append(lg_name) # Track potential action

                    if not DRY_RUN:
                        try:
                            logger.info(f"[{region}] Setting retention for Log Group {lg_name} to {target_retention} days.")
                            logs_client.put_retention_policy(
                                logGroupName=lg_name,
                                retentionInDays=target_retention
                            )
                            log_groups_modified_count += 1 # Track successful action
                            logger.info(f"[{region}] Successfully set retention for Log Group {lg_name}.")
                        except ClientError as e:
                            logger.error(f"[{region}] Error setting retention for Log Group {lg_name}: {e}")
                            results['errors'].append(f"SetRetErr({lg_name}):{e}")

        # Finalize counts based on DRY_RUN status
        results['modified_action']['count'] = len(log_groups_would_modify_names) if DRY_RUN else log_groups_modified_count

        if results['modified_action']['count'] > 0:
            action = "Would modify" if DRY_RUN else "Modified"
            logger.info(f"[{region}] {action} retention policy for {results['modified_action']['count']} Log Group(s).")
        else:
            logger.info(f"[{region}] No Log Groups required retention policy updates based on criteria.")

    except ClientError as e:
        logger.error(f"[{region}] Error describing CloudWatch Log Groups: {e}")
        results['errors'].append(f"DescLGErr: {e}")

    logger.info(f"--- Finished CloudWatch Log Group Optimization in {region} ---")

    # Build summary lines for return (optional, as handler uses dict now)
    summary_lines = []
    count = results['modified_action']['count']
    if count > 0: summary_lines.append(f"{'Would modify' if DRY_RUN else 'Modified'} retention for {count} LG(s).")
    else: summary_lines.append("No LGs needed retention updates.")
    if results['skipped']: summary_lines.append(f"Skipped {len(results['skipped'])} excluded LG(s).")
    if results['errors']: summary_lines.append(f"Errors: {len(results['errors'])}")
    summary_lines.append("$0.00 USD/month estimated savings by CW Logs")
    results['summary_lines'] = summary_lines # Store summary for potential direct use

    return results, 0.0 # Always return $0 savings


def report_cloudwatch_alarms(cloudwatch_client, region):
    """Report on CloudWatch alarms potentially suitable for removal."""
    logger.info(f"--- Starting CloudWatch Alarm Reporting in {region} ---")
    # Initialize structured results
    results = {
        "errors": [],
        "insufficient_data_report": {"count": 0, "details": []}, # List alarms found
        "skipped": [] # List of skipped alarm names (optional)
    }
    if not ENABLE_CW_INSUFFICIENT_DATA_ALARM_REPORTING:
        logger.info(f"[{region}] CW Alarm reporting disabled.")
        results["summary_lines"] = ["CW Alarm reporting disabled."] # Add summary if needed
        return results # No savings

    now_utc = datetime.now(timezone.utc)
    
    cutoff = now_utc - timedelta(days=CW_ALARM_INSUFFICIENT_DATA_DAYS_THRESHOLD) 
    # cutoff = now_utc - timedelta(days=CW_ALARM_INSUFFICIENT_DATA_DAYS_THRESHOLD) # Days for production
    logger.info(f"[{region}] Checking alarms in INSUFFICIENT_DATA since {cutoff.isoformat()}...")

    alarms_to_report_details = [] # Use temporary list for details

    try:
        paginator = cloudwatch_client.get_paginator('describe_alarms')
        for page in paginator.paginate():
            # Combine Metric and Composite alarms if needed
            for alarm in page.get('MetricAlarms', []) + page.get('CompositeAlarms', []):
                alarm_name = alarm['AlarmName']
                alarm_arn = alarm['AlarmArn']
                state_value = alarm.get('StateValue')
                state_updated_timestamp = alarm.get('StateUpdatedTimestamp')

                # Filter for relevant state and timestamp
                if state_value != 'INSUFFICIENT_DATA' or not state_updated_timestamp:
                    continue

                tags = [] # Initialize empty list for tags
                # --- CORRECTED BLOCK ---
                try:
                    tag_response = cloudwatch_client.list_tags_for_resource(ResourceARN=alarm_arn)
                    tags = tag_response.get('Tags', []) # Assign tags if successful
                except ClientError as e:
                    # Log warning but continue without tags for exclusion check
                    logger.warning(f"[{region}] Could not list tags for alarm {alarm_name}: {e}.")
                    results['errors'].append(f"Alarm Tag Err ({alarm_name}): {e}") # Log error in results
                    pass # Proceed without tags
                # --- END CORRECTED BLOCK ---

                if is_excluded(tags):
                    logger.info(f"[{region}] Skipping excluded Alarm {alarm_name}")
                    results['skipped'].append(alarm_name) # Add to skipped list
                    continue

                # Check timestamp against cutoff
                if state_updated_timestamp < cutoff:
                    detail = f"{alarm_name} (since {state_updated_timestamp:%Y-%m-%d %H:%M})"
                    logger.info(f"[{region}] Found alarm meeting criteria: {detail}")
                    alarms_to_report_details.append(detail)

        # Finalize results dictionary
        results['insufficient_data_report']['count'] = len(alarms_to_report_details)
        results['insufficient_data_report']['details'] = alarms_to_report_details

        # Log summary warning if any found
        if results['insufficient_data_report']['count'] > 0:
            logger.warning(f"[{region}] {results['insufficient_data_report']['count']} Alarms in INSUFFICIENT_DATA > {CW_ALARM_INSUFFICIENT_DATA_DAYS_THRESHOLD} days found:")
            for detail in alarms_to_report_details[:5]: logger.warning(f"  - {detail}") # Log first few
            if len(alarms_to_report_details) > 5: logger.warning("  - ...")
            logger.warning(f"[{region}] Review removal from IaC source recommended.")
        else:
            logger.info(f"[{region}] No long-standing INSUFFICIENT_DATA alarms found.")

    except ClientError as e:
        logger.error(f"[{region}] Error describing CloudWatch Alarms: {e}")
        results['errors'].append(f"DescAlarmsErr:{e}")

    logger.info(f"--- Finished CloudWatch Alarm Reporting in {region} ---")

    # Build optional summary lines
    summary_lines = []
    count = results['insufficient_data_report']['count']
    if count > 0: summary_lines.append(f"Found {count} long-standing INSUFFICIENT_DATA alarm(s).")
    else: summary_lines.append("No long-standing INSUFFICIENT_DATA alarms.")
    if results['skipped']: summary_lines.append(f"Skipped {len(results['skipped'])} excluded alarm(s).")
    if results['errors']: summary_lines.append(f"Errors: {len(results['errors'])}")
    results['summary_lines'] = summary_lines # Store for potential direct use

    return results # Return structured results (no savings)

# --- RDS ---

def optimize_rds(rds_client, cloudwatch_client, region):
    """Optimize RDS: retention, snapshots, report low CPU."""
    logger.info(f"--- Starting RDS Optimization in {region} ---")
    now_utc = datetime.now(timezone.utc)
    # Initialize structured results
    results = {
        "savings": 0.0,
        "errors": [],
        "modified_inst_ret_action": {"count": 0, "details": []},
        "modified_clus_ret_action": {"count": 0, "details": []},
        "deleted_inst_snap_action": {"count": 0, "details": []},
        "deleted_clus_snap_action": {"count": 0, "details": []},
        "low_cpu_report": {"count": 0, "details": []}
    }
    # Internal tracking
    processed_clusters = set()
    clus_would_mod, inst_would_mod = set(), []
    snap_would_del, clus_snap_would_del = [], []
    snap_del, clus_snap_del = [], []
    inst_mod_cnt, clus_mod_cnt = 0, 0

    # --- 1. Adjust Retention & Report Low CPU ---
    if ENABLE_RDS_BACKUP_RETENTION_ADJUSTMENT or ENABLE_RDS_LOW_CPU_REPORTING:
        logger.info(f"[{region}] Checking RDS instances/clusters...")
        try:
            paginator = rds_client.get_paginator('describe_db_instances')
            
            check_start_time = now_utc - timedelta(days=RDS_RIGHTSIZE_CHECK_DAYS) 
            # check_start_time = now_utc - timedelta(days=RDS_RIGHTSIZE_CHECK_DAYS) # Days for production

            for page in paginator.paginate():
                for inst in page.get('DBInstances', []):
                    inst_id, inst_arn, clus_id = inst['DBInstanceIdentifier'], inst['DBInstanceArn'], inst.get('DBClusterIdentifier')

                    # Get instance tags (used for exclusion checks below)
                    tags = []
                    try:
                        tags = rds_client.list_tags_for_resource(ResourceName=inst_arn).get('TagList', [])
                    except ClientError as e:
                        logger.warning(f"[{region}] Could not get tags for instance {inst_id}: {e}. Proceeding without tag check for instance itself.")

                    if is_excluded(tags):
                        logger.info(f"[{region}] Skipping excluded instance {inst_id} based on its own tags.")
                        continue

                    # -- Cluster Processing --
                    if clus_id:
                        if clus_id in processed_clusters: continue
                        processed_clusters.add(clus_id)
                        try:
                            clus = rds_client.describe_db_clusters(DBClusterIdentifier=clus_id)['DBClusters'][0]
                            clus_tags = [] # Initialize cluster tags
                            try: # Get cluster tags separately
                                clus_tags = rds_client.list_tags_for_resource(ResourceName=clus['DBClusterArn']).get('TagList', [])
                            except ClientError as e:
                                logger.warning(f"[{region}] Could not get tags for cluster {clus_id}: {e}.")

                            if is_excluded(clus_tags): # Check cluster tags for exclusion
                                logger.info(f"[{region}] Skipping excluded cluster {clus_id} based on its tags.")
                                continue

                            # Retention Check
                            if ENABLE_RDS_BACKUP_RETENTION_ADJUSTMENT:
                                cur_ret = clus['BackupRetentionPeriod']
                                if cur_ret > RDS_MAX_BACKUP_RETENTION_DAYS:
                                    detail = f"Cluster {clus_id}: {cur_ret}d -> {RDS_MAX_BACKUP_RETENTION_DAYS}d"
                                    results['modified_clus_ret_action']['details'].append(detail)
                                    clus_would_mod.add(clus_id) # Track potential action
                                    if not DRY_RUN:
                                        try:
                                            logger.info(f"[{region}] Modifying cluster {clus_id} retention...")
                                            rds_client.modify_db_cluster(DBClusterIdentifier=clus_id, BackupRetentionPeriod=RDS_MAX_BACKUP_RETENTION_DAYS)
                                            clus_mod_cnt += 1 # Track actual action
                                        except ClientError as e:
                                            results['errors'].append(f"ClusModErr({clus_id}):{e}")
                        except (ClientError, IndexError) as e:
                            results['errors'].append(f"ClusFetchErr({clus_id}):{e}")

                    # -- Standalone Instance Processing --
                    else:
                        # Retention Check
                        ret = inst.get('BackupRetentionPeriod')
                        if ENABLE_RDS_BACKUP_RETENTION_ADJUSTMENT and ret is not None and ret > RDS_MAX_BACKUP_RETENTION_DAYS:
                            # Exclusion already checked using instance tags
                            detail = f"Instance {inst_id}: {ret}d -> {RDS_MAX_BACKUP_RETENTION_DAYS}d"
                            results['modified_inst_ret_action']['details'].append(detail)
                            inst_would_mod.append(inst_id) # Track potential action
                            if not DRY_RUN:
                                try:
                                    logger.info(f"[{region}] Modifying instance {inst_id} retention...")
                                    rds_client.modify_db_instance(DBInstanceIdentifier=inst_id, BackupRetentionPeriod=RDS_MAX_BACKUP_RETENTION_DAYS, ApplyImmediately=False)
                                    inst_mod_cnt += 1 # Track actual action
                                except ClientError as e:
                                    results['errors'].append(f"InstModErr({inst_id}):{e}")

                        # Low CPU Check
                        if ENABLE_RDS_LOW_CPU_REPORTING and inst.get('DBInstanceStatus') == 'available':
                            # Exclusion already checked using instance tags
                            try:
                                metrics = cloudwatch_client.get_metric_statistics(Namespace='AWS/RDS', MetricName='CPUUtilization', Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': inst_id}], StartTime=check_start_time, EndTime=now_utc, Period=86400, Statistics=['Average'], Unit='Percent')
                                avgs = [dp['Average'] for dp in metrics['Datapoints']]; avg_cpu = -1
                                if avgs: avg_cpu = mean(avgs)
                                if avg_cpu >= 0 and avg_cpu < RDS_LOW_CPU_THRESHOLD_PERCENT:
                                    results['low_cpu_report']['details'].append(f"{inst_id}({avg_cpu:.1f}% avg CPU)")
                            except (ClientError, KeyError, ValueError, TypeError) as e:
                                results['errors'].append(f"RDS CPU Err({inst_id}):{e}")
        except ClientError as e:
            results['errors'].append(f"DescInstErr:{e}")

    # --- 2 & 3. Snapshot Deletion ---
    if ENABLE_RDS_MANUAL_SNAPSHOT_DELETION:
        
        cutoff = now_utc - timedelta(days=RDS_MANUAL_SNAPSHOT_RETENTION_DAYS) 

        try: # Instance Snaps
            logger.info(f"[{region}] Checking inst snaps older than {cutoff.isoformat()}...")
            paginator = rds_client.get_paginator('describe_db_snapshots')
            snaps_to_proc = []
            for page in paginator.paginate(SnapshotType='manual', IncludeShared=False):
                for snap in page.get('DBSnapshots', []):
                    sid, arn, stime = snap['DBSnapshotIdentifier'], snap['DBSnapshotArn'], snap.get('SnapshotCreateTime')
                    tags = []
                    try: # Corrected Tag Block
                        tags = rds_client.list_tags_for_resource(ResourceName=arn).get('TagList', [])
                    except ClientError as e:
                        logger.warning(f"[{region}] Could not get tags for inst snap {sid}: {e}.")
                    # End Corrected Tag Block
                    if is_excluded(tags): continue
                    if snap.get('Status') == 'available' and stime and stime < cutoff:
                        snaps_to_proc.append({'id': sid, 'size': snap.get('AllocatedStorage', 0), 'time': stime})

            results['deleted_inst_snap_action']['count'] = len(snaps_to_proc) # Set potential count
            for s in snaps_to_proc:
                sv = s['size'] * RDS_SNAPSHOT_PRICE_GB_MONTH
                results['savings'] += sv # Add potential savings
                detail = f"{s['id']}(Sz:{s['size']}GB,Crtd:{s['time']:%Y-%m-%d})-Est ${sv:.2f}/mo"
                results['deleted_inst_snap_action']['details'].append(detail)
                snap_would_del.append(s['id']) # Track potential action

                # Corrected Deletion Block
                if not DRY_RUN:
                    try:
                        logger.info(f"[{region}] Deleting RDS instance snapshot {s['id']}...")
                        rds_client.delete_db_snapshot(DBSnapshotIdentifier=s['id'])
                        snap_del.append(s['id']) # Track actual deletion
                        logger.info(f"[{region}] Successfully deleted instance snapshot {s['id']}.")
                    except ClientError as e:
                        logger.error(f"[{region}] Error deleting instance snapshot {s['id']}: {e}")
                        results['errors'].append(f"ISnapDelErr({s['id']}):{e}")
                        results['savings'] -= sv # Subtract savings on failure
        except ClientError as e:
            results['errors'].append(f"DescISnapErr:{e}")

        try: # Cluster Snaps
            logger.info(f"[{region}] Checking clus snaps older than {cutoff.isoformat()}...")
            paginator = rds_client.get_paginator('describe_db_cluster_snapshots')
            snaps_to_proc = []
            for page in paginator.paginate(SnapshotType='manual', IncludeShared=False):
                 for snap in page.get('DBClusterSnapshots', []):
                    sid, arn, stime = snap['DBClusterSnapshotIdentifier'], snap['DBClusterSnapshotArn'], snap.get('SnapshotCreateTime')
                    tags = []
                    try: # Corrected Tag Block
                        tags = rds_client.list_tags_for_resource(ResourceName=arn).get('TagList', [])
                    except ClientError as e:
                        logger.warning(f"[{region}] Could not get tags for cluster snap {sid}: {e}.")
                    # End Corrected Tag Block
                    if is_excluded(tags): continue
                    if snap.get('Status') == 'available' and stime and stime < cutoff:
                        sz = snap.get('AllocatedStorage', 0)
                        sz = sz if isinstance(sz, (int, float)) else 0
                        snaps_to_proc.append({'id': sid, 'size': sz, 'time': stime})

            results['deleted_clus_snap_action']['count'] = len(snaps_to_proc) # Set potential count
            for s in snaps_to_proc:
                sv = s['size'] * RDS_SNAPSHOT_PRICE_GB_MONTH
                results['savings'] += sv # Add potential savings
                detail = f"{s['id']}(Sz:{s['size']}GB,Crtd:{s['time']:%Y-%m-%d})-Est ${sv:.2f}/mo"
                results['deleted_clus_snap_action']['details'].append(detail)
                clus_snap_would_del.append(s['id']) # Track potential action

                # Corrected Deletion Block
                if not DRY_RUN:
                    try:
                        logger.info(f"[{region}] Deleting RDS cluster snapshot {s['id']}...")
                        rds_client.delete_db_cluster_snapshot(DBClusterSnapshotIdentifier=s['id'])
                        clus_snap_del.append(s['id']) # Track actual deletion
                        logger.info(f"[{region}] Successfully deleted cluster snapshot {s['id']}.")
                    except ClientError as e:
                        logger.error(f"[{region}] Error deleting cluster snapshot {s['id']}: {e}")
                        results['errors'].append(f"CSnapDelErr({s['id']}):{e}")
                        results['savings'] -= sv # Subtract savings on failure
        except ClientError as e:
            results['errors'].append(f"DescCSnapErr:{e}")

    # Finalize counts based on DRY_RUN status
    if DRY_RUN:
         results['modified_inst_ret_action']['count'] = len(inst_would_mod)
         results['modified_clus_ret_action']['count'] = len(clus_would_mod)
         # Snapshot counts already set based on identified snaps
    else:
         results['modified_inst_ret_action']['count'] = inst_mod_cnt
         results['modified_clus_ret_action']['count'] = clus_mod_cnt
         results['deleted_inst_snap_action']['count'] = len(snap_del)
         results['deleted_clus_snap_action']['count'] = len(clus_snap_del)
    results['low_cpu_report']['count'] = len(results['low_cpu_report']['details'])

    logger.info(f"--- Finished RDS Optimization in {region} ---")
    return results, results['savings']


def optimize_s3(s3_client, region):
    logger.info(f"--- Starting S3 Optimization in {region} ---")
    results = {
        "savings": 0.0,
        "errors": [],
        "processed_buckets": 0,
        "deleted_action": {"count": 0, "details": []}
    }
    if not ENABLE_S3_OBJECT_DELETION:
        results['summary_lines'] = ["S3 object deletion disabled."]
        return results, 0.0

    now_utc = datetime.now(timezone.utc)
    
    cutoff = now_utc - timedelta(days=S3_OBJECT_AGE_DAYS_THRESHOLD) 
    logger.info(f"[{region}] Checking objects older than {cutoff.isoformat()} in region {region} buckets...")

    total_bytes_identified_for_deletion = 0 # Aggregate size across all buckets
    obj_ident_count = 0 # Total objects identified (DRY RUN or actual)
    obj_del_actual_count = 0 # Total objects actually deleted (non-DRY RUN)
    processed_bucket_count = 0 # Count buckets actually processed in the region

    try:
        for bucket in s3_client.list_buckets().get('Buckets', []):
            bname = bucket['Name']
            try:
                # Ensure bucket is in the target region before processing
                loc_response = s3_client.get_bucket_location(Bucket=bname)
                # Note: Buckets in us-east-1 return None or no LocationConstraint.
                bucket_region = loc_response.get('LocationConstraint') or 'us-east-1'

                if bucket_region != region:
                    # logger.debug(f"[{region}] Skipping bucket {bname} (in region {bucket_region}).")
                    continue # Skip buckets not in the current processing region

                logger.info(f"[{region}] Processing bucket {bname} (Region: {bucket_region})...")
                processed_bucket_count += 1 # Increment count for buckets in this region

                # Check versioning (skip if enabled)
                vers = s3_client.get_bucket_versioning(Bucket=bname).get('Status')
                if vers == 'Enabled':
                    logger.warning(f"[{region}] Skipping versioned bucket {bname}.")
                    continue

                # Check bucket tags for exclusion
                try:
                     tags_resp = s3_client.get_bucket_tagging(Bucket=bname)
                     tags = tags_resp.get('TagSet', [])
                     if is_excluded(tags):
                          logger.info(f"[{region}] Skipping excluded bucket {bname} based on tags.")
                          continue
                except ClientError as e:
                     if e.response['Error']['Code'] == 'NoSuchTagSet':
                          pass # No tags is fine, not excluded
                     else:
                          logger.warning(f"[{region}] Could not get tags for bucket {bname}: {e}. Proceeding without tag check.")
                          results['errors'].append(f"S3TagErr({bname}):{e}")


                paginator = s3_client.get_paginator('list_objects_v2')
                batch_to_delete = []
                batch_bytes_current = 0
                bucket_objects_deleted_count = 0 # Track deletes per bucket for logging/details if needed

                for page in paginator.paginate(Bucket=bname):
                    for obj in page.get('Contents', []):
                        # Check object age and skip "folders"
                        if obj['LastModified'] < cutoff and not (obj['Key'].endswith('/') and obj.get('Size', 0) == 0):
                            # Check object tags for exclusion (more granular, if needed)
                            # try:
                            #     obj_tags_resp = s3_client.get_object_tagging(Bucket=bname, Key=obj['Key'])
                            #     obj_tags = obj_tags_resp.get('TagSet', [])
                            #     if is_excluded(obj_tags):
                            #         logger.debug(f"[{region}] Skipping excluded object {bname}/{obj['Key']} based on tags.")
                            #         continue
                            # except ClientError as e:
                            #      if e.response['Error']['Code'] == 'NoSuchTagSet': pass # No tags is fine
                            #      else: logger.warning(f"Tag check failed for {bname}/{obj['Key']}: {e}")


                            batch_to_delete.append({'Key': obj['Key']})
                            current_obj_size = obj.get('Size', 0)
                            batch_bytes_current += current_obj_size
                            obj_ident_count += 1 # Increment identified count regardless of dry run

                            if len(batch_to_delete) >= 1000:
                                # Add bytes to regional total *before* attempting delete
                                total_bytes_identified_for_deletion += batch_bytes_current

                                if DRY_RUN:
                                    logger.info(f"[DRY RUN] Would delete {len(batch_to_delete)} objects (approx {batch_bytes_current/(1024**2):.2f} MB) from {bname}.")
                                else:
                                    try:
                                        logger.info(f"[{region}] Deleting {len(batch_to_delete)} objects batch (approx {batch_bytes_current/(1024**2):.2f} MB) from {bname}...")
                                        s3_client.delete_objects(Bucket=bname, Delete={'Objects': batch_to_delete, 'Quiet': True})
                                        obj_del_actual_count += len(batch_to_delete) # Increment actual count on success
                                        bucket_objects_deleted_count += len(batch_to_delete)
                                    except ClientError as e:
                                        logger.error(f"[{region}] Error deleting batch from {bname}: {e}")
                                        results['errors'].append(f"S3BatchDelErr({bname}):{e}")
                                        # Do NOT subtract savings here - calculate only once at the end
                                # Reset batch
                                batch_to_delete, batch_bytes_current = [], 0

                # Process the final batch (if any objects were found)
                if batch_to_delete:
                    total_bytes_identified_for_deletion += batch_bytes_current
                    if DRY_RUN:
                        logger.info(f"[DRY RUN] Would delete {len(batch_to_delete)} final objects (approx {batch_bytes_current/(1024**2):.2f} MB) from {bname}.")
                    else:
                        try:
                            logger.info(f"[{region}] Deleting {len(batch_to_delete)} final objects batch (approx {batch_bytes_current/(1024**2):.2f} MB) from {bname}...")
                            s3_client.delete_objects(Bucket=bname, Delete={'Objects': batch_to_delete, 'Quiet': True})
                            obj_del_actual_count += len(batch_to_delete)
                            bucket_objects_deleted_count += len(batch_to_delete)
                        except ClientError as e:
                            logger.error(f"[{region}] Error deleting final batch from {bname}: {e}")
                            results['errors'].append(f"S3FinalDelErr({bname}):{e}")
                            # Do NOT subtract savings here

            except ClientError as e:
                # Handle errors like AccessDenied, NoSuchBucket, potentially skip bucket
                if e.response['Error']['Code'] in ['AccessDenied', 'NoSuchBucket']:
                     logger.warning(f"[{region}] Skipping bucket {bname} due to error: {e}")
                elif e.response['Error']['Code'] == 'NoSuchTagSet' and 'get_bucket_tagging' in str(e):
                     pass # Ignore error getting tags if none exist
                else:
                     logger.error(f"[{region}] Error processing bucket {bname}: {e}")
                     results['errors'].append(f"S3 Proc/List Err ({bname}): {e}")
                continue # Skip to the next bucket on error

        # --- SINGLE REGIONAL SAVINGS CALCULATION ---
        total_gb_deleted = total_bytes_identified_for_deletion / (1024**3)
        results['savings'] = total_gb_deleted * S3_STANDARD_PRICE_GB_MONTH

        # Log the final calculation details
        logger.info(f"[{region}] S3 Summary: Identified {obj_ident_count} objects totaling {total_gb_deleted:.4f} GB for potential deletion.")
        logger.info(f"[{region}] S3 Calculated Savings: ${results['savings']:.4f}/month") # Log with more precision

        results['processed_buckets'] = processed_bucket_count
        final_report_count = obj_ident_count if DRY_RUN else obj_del_actual_count
        results["deleted_action"]["count"] = final_report_count

        # Update details for the report (still summarized)
        if final_report_count > 0:
            action_str = "Identified" if DRY_RUN else "Deleted"
            results["deleted_action"]["details"] = [f"{action_str} {final_report_count} object(s) totaling {total_gb_deleted:.2f} GB across {processed_bucket_count} bucket(s)"]
        else:
             results["deleted_action"]["details"] = [f"No objects {('identified' if DRY_RUN else 'deleted')} across {processed_bucket_count} bucket(s)."]


    except ClientError as e:
        logger.error(f"[{region}] Error listing S3 buckets: {e}")
        results['errors'].append(f"S3 ListBuckets Err:{e}")

    logger.info(f"--- Finished S3 Optimization in {region} ---")
    # Return the calculated results and the single, aggregated savings value
    return results, results['savings']

# --- optimize_lambda_functions ---
def optimize_lambda_functions(lambda_client, cloudwatch_client, region):
    logger.info(f"--- Starting Lambda Idle Reporting in {region} ---")
    results = {"errors": [], "idle_report": {"count": 0, "details": []}, "skipped": []}
    if not ENABLE_LAMBDA_IDLE_REPORTING:
        results["summary_lines"] = ["Lambda reporting disabled."]
        return results, 0.0

    now_utc = datetime.now(timezone.utc)
    idle_start_time = now_utc - timedelta(days=LAMBDA_IDLE_DAYS_THRESHOLD) # USE DAYS
    logger.info(f"[{region}] Checking Lambdas idle since {idle_start_time.isoformat()}...")
    idle_funcs_details = []

    try:
        paginator = lambda_client.get_paginator('list_functions')
        for page in paginator.paginate():
            for func in page.get('Functions', []):
                fname, arn, mod_str = func['FunctionName'], func['FunctionArn'], func['LastModified']
                mod_dt = datetime.strptime(mod_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                if mod_dt > idle_start_time: continue # Skip recent

                tags = {}
                # --- CORRECTED TAG BLOCK ---
                try: tags = lambda_client.list_tags(Resource=arn).get('Tags',{})
                except ClientError as e: logger.warning(f"[{region}] Could not get tags for Lambda {fname}: {e}.")
                # --- END CORRECTED BLOCK ---

                if is_excluded(tags): results['skipped'].append(fname); continue

                try:
                    period = max(60, int(timedelta(days=LAMBDA_IDLE_DAYS_THRESHOLD).total_seconds())); period=min(period, 86400*30)
                    metrics = cloudwatch_client.get_metric_statistics( Namespace='AWS/Lambda', MetricName='Invocations', Dimensions=[{'Name':'FunctionName','Value':fname}], StartTime=idle_start_time, EndTime=now_utc, Period=period, Statistics=['Sum'], Unit='Count' )
                    invocations = sum(dp['Sum'] for dp in metrics['Datapoints'])
                    if invocations <= LAMBDA_IDLE_INVOCATION_THRESHOLD: idle_funcs_details.append(f"{fname} ({invocations} invocations)")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidParameterValue' and mod_dt < idle_start_time: idle_funcs_details.append(f"{fname} (No invocations found)")
                    else: results['errors'].append(f"Lambda CW Err ({fname}): {e}")
                except Exception as e: results['errors'].append(f"Lambda Proc Err ({fname}): {e}")

        results['idle_report']['count'] = len(idle_funcs_details)
        results['idle_report']['details'] = idle_funcs_details
        if results['idle_report']['count'] > 0: logger.info(f"Found {results['idle_report']['count']} idle Lambdas.")

    except ClientError as e: results['errors'].append(f"List Functions Err: {e}")
    logger.info(f"--- Finished Lambda Idle Reporting in {region} ---")
    return results, 0.0

try:
    EKS_EXTENDED_SUPPORT_PRICE_HOURLY = float(os.environ.get('EKS_EXTENDED_SUPPORT_PRICE_HOURLY', '0.50'))
    logger.info(f"Using EKS Extended Support hourly price: ${EKS_EXTENDED_SUPPORT_PRICE_HOURLY}")
except ValueError:
    logger.error("Invalid value for EKS_EXTENDED_SUPPORT_PRICE_HOURLY env var. Defaulting to 0.50.")
    EKS_EXTENDED_SUPPORT_PRICE_HOURLY = 0.50

try:
    # N=3, default to 3 if env var is missing/invalid
    EKS_STANDARD_SUPPORT_VERSION_COUNT = int(os.environ.get('EKS_STANDARD_SUPPORT_VERSION_COUNT', '3'))
    logger.info(f"Assuming {EKS_STANDARD_SUPPORT_VERSION_COUNT} EKS versions are in standard support.")
except ValueError:
    logger.error("Invalid value for EKS_STANDARD_SUPPORT_VERSION_COUNT env var. Defaulting to 3.")
    EKS_STANDARD_SUPPORT_VERSION_COUNT = 3

# --- Helper Function for Dynamic Version Discovery ---
def get_dynamic_eks_standard_versions(eks_client, count=3):
    """
    Dynamically determines the set of standard supported EKS versions
    by finding the latest version mentioned in addon compatibilities.
    Returns a set of 'major.minor' version strings or None if lookup fails.
    """
    supported_versions_set = set()
    all_k8s_versions_found = set()
    try:
        logger.info("Attempting to dynamically determine latest EKS K8s version via describe_addon_versions...")
        paginator = eks_client.get_paginator('describe_addon_versions')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            addons = page.get('addons', [])
            for addon in addons:
                addon_versions = addon.get('addonVersions', [])
                for addon_version_info in addon_versions:
                    compatibilities = addon_version_info.get('compatibilities', [])
                    for comp in compatibilities:
                        cluster_version = comp.get('clusterVersion')
                        if cluster_version:
                            # Extract major.minor using regex for safety
                            match = re.match(r"(\d+\.\d+)", cluster_version)
                            if match:
                                all_k8s_versions_found.add(match.group(1))

        if not all_k8s_versions_found:
            logger.error("Could not find any K8s versions from describe_addon_versions response.")
            return None  # Indicate failure

        # Sort versions using tuple comparison
        sorted_versions = sorted(
            all_k8s_versions_found,
            key=lambda v: tuple(map(int, v.split("."))),
            reverse=True
        )
        logger.info(f"Sorted Kubernetes versions: {sorted_versions}")

        # Generate the list of N supported versions (latest, latest-1, ..., latest-N+1)
        return set(sorted_versions[:count])

    except ClientError as e:
        logger.error(f"Error fetching addon versions: {e}")
        return None
    
# --- Main Optimization Function For EKS ---
def optimize_eks_clusters(eks_client, region):
    """Reports on potentially unused EKS clusters and clusters incurring Extended Support costs."""
    logger.info(f"--- Starting EKS Cluster Optimization in {region} ---")
    results = {
        "savings": 0.0, # Will hold combined savings
        "errors": [],
        "unused_report": {"count": 0, "details": []},
        "extended_support_report": {"count": 0, "details": []}
    }
    # Separate accumulators for clarity
    unused_cluster_savings_accumulator = 0.0
    extended_support_savings_accumulator = 0.0

    # Calculate potential monthly costs
    eks_monthly_unused_cost = EKS_CONTROL_PLANE_PRICE_HOURLY * 24 * 30.44
    eks_monthly_extended_cost = EKS_EXTENDED_SUPPORT_PRICE_HOURLY * 24 * 30.44

    unused_clusters_details = []
    extended_support_details = []

    # --- Dynamically determine standard support versions ---
    standard_support_versions = get_dynamic_eks_standard_versions(eks_client, EKS_STANDARD_SUPPORT_VERSION_COUNT)
    if standard_support_versions is None:
        results['errors'].append("Failed to dynamically determine EKS standard support versions. Extended support check skipped.")
        # Optionally, decide whether to proceed with only the unused check or stop EKS checks
        logger.warning("Skipping EKS extended support checks due to failure in dynamic version lookup.")
        # We can still proceed with the unused check

    # --- Process Clusters ---
    try:
        paginator = eks_client.get_paginator('list_clusters')
        for page in paginator.paginate():
            for name in page.get('clusters', []):
                try:
                    # Describe the cluster
                    cluster_response = eks_client.describe_cluster(name=name)
                    cluster_data = cluster_response.get('cluster', {})
                    if not cluster_data:
                        logger.warning(f"[{region}] Could not retrieve cluster data for {name}. Skipping.")
                        continue

                    status = cluster_data.get('status')
                    tags = cluster_data.get('tags', {}) # Tags are directly on the cluster object
                    cluster_version_full = cluster_data.get('version', 'Unknown')

                    # --- Check 1: Potentially Unused Cluster ---
                    # Only check active clusters that are not excluded
                    if status == 'ACTIVE' and not is_excluded(tags):
                         try:
                              nodegroups = eks_client.list_nodegroups(clusterName=name).get('nodegroups')
                              fargate = eks_client.list_fargate_profiles(clusterName=name).get('fargateProfileNames')
                              if not nodegroups and not fargate:
                                   detail = f"{name} (Est Control Plane Cost: ${eks_monthly_unused_cost:.2f}/mo savings)"
                                   unused_clusters_details.append(detail)
                                   unused_cluster_savings_accumulator += eks_monthly_unused_cost
                                   logger.info(f"[{region}] Found potentially unused EKS cluster: {name}")
                         except ClientError as check_err:
                              logger.warning(f"[{region}] Error checking nodegroups/fargate for {name}: {check_err}")
                              results['errors'].append(f"EKS Node Check Err ({name}): {check_err}")

                    # --- Check 2: Extended Support Status (if versions determined) ---
                    if standard_support_versions is not None: # Only run if dynamic lookup succeeded
                        # Extract major.minor version
                        major_minor_version = "Unknown"
                        match = re.match(r"(\d+\.\d+)", cluster_version_full)
                        if match:
                            major_minor_version = match.group(1)

                        # Check active clusters outside standard support that are not excluded
                        if status == 'ACTIVE' \
                           and major_minor_version != "Unknown" \
                           and major_minor_version not in standard_support_versions \
                           and not is_excluded(tags):

                            detail = f"{name} (Version: {cluster_version_full}) - Est Extended Support Cost: ${eks_monthly_extended_cost:.2f}/mo"
                            extended_support_details.append(detail)
                            extended_support_savings_accumulator += eks_monthly_extended_cost
                            logger.warning(f"[{region}] Found EKS cluster potentially on Extended Support: {name} (Version: {cluster_version_full}) - Check against {standard_support_versions}")


                except ClientError as e:
                    if e.response.get('Error', {}).get('Code') == 'ResourceNotFoundException':
                         logger.warning(f"[{region}] Cluster {name} not found during describe (possibly deleted). Skipping.")
                    else:
                         logger.error(f"[{region}] Error describing EKS cluster {name}: {e}")
                         results['errors'].append(f"EKS Describe Err ({name}): {e}")
                except Exception as e:
                    logger.error(f"[{region}] Unexpected error processing EKS cluster {name}: {e}", exc_info=True)
                    results['errors'].append(f"EKS Proc Err ({name}): {e}")

        # Populate results dictionary
        results['unused_report']['count'] = len(unused_clusters_details)
        results['unused_report']['details'] = unused_clusters_details
        results['extended_support_report']['count'] = len(extended_support_details)
        results['extended_support_report']['details'] = extended_support_details

        # Calculate total savings for EKS
        total_eks_savings = unused_cluster_savings_accumulator + extended_support_savings_accumulator
        results['savings'] = total_eks_savings

        logger.info(f"[{region}] EKS Savings Breakdown: Unused Potential=${unused_cluster_savings_accumulator:.2f}, Extended Support=${extended_support_savings_accumulator:.2f}, Total=${total_eks_savings:.2f}")

    except ClientError as e:
        logger.error(f"[{region}] Error listing EKS clusters: {e}")
        results['errors'].append(f"List EKS Err: {e}")

    logger.info(f"--- Finished EKS Cluster Optimization in {region} ---")
    return results, results['savings'] # Return dict and COMBINED savings

# --- optimize_nat_gateways  ---
def optimize_nat_gateways(ec2_client, cloudwatch_client, region):
    logger.info(f"--- Starting NAT Gateway Idle Reporting in {region} ---")
    results = { "savings": 0.0, "errors": [], "idle_report": {"count": 0, "details": []}, "skipped": [] }
    if not ENABLE_NAT_GATEWAY_IDLE_REPORTING:
        results["summary_lines"] = ["NAT GW reporting disabled."]
        return results, 0.0

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=NAT_IDLE_CHECK_DAYS) # USE DAYS
    logger.info(f"[{region}] Checking NAT GWs idle since {cutoff.isoformat()}...")
    nat_monthly_cost = NAT_GW_PRICE_HOURLY * 24 * 30.44
    idle_nat_details = []

    try:
        paginator = ec2_client.get_paginator('describe_nat_gateways')
        for page in paginator.paginate(Filter=[{'Name':'state','Values':['available']}]):
            for nat in page.get('NatGateways', []):
                nat_id, tags = nat['NatGatewayId'], nat.get('Tags', [])
                if is_excluded(tags): results['skipped'].append(nat_id); continue
                try:
                    metrics = cloudwatch_client.get_metric_statistics( Namespace='AWS/NATGateway', MetricName='BytesProcessed', Dimensions=[{'Name':'NatGatewayId','Value':nat_id}], StartTime=cutoff, EndTime=now_utc, Period=86400*NAT_IDLE_CHECK_DAYS, Statistics=['Sum'], Unit='Bytes' )
                    total_bytes = sum(dp['Sum'] for dp in metrics['Datapoints'])
                    if total_bytes < NAT_BYTES_PROCESSED_THRESHOLD:
                        gb_proc = total_bytes / (1024**3)
                        detail = f"{nat_id} ({gb_proc:.2f} GB processed) - Est ${nat_monthly_cost:.2f}/mo savings"
                        idle_nat_details.append(detail)
                        results['savings'] += nat_monthly_cost
                except ClientError as e: results['errors'].append(f"NAT Metric Err ({nat_id}): {e}")
                except Exception as e: results['errors'].append(f"NAT Proc Err ({nat_id}): {e}")

        results['idle_report']['count'] = len(idle_nat_details)
        results['idle_report']['details'] = idle_nat_details
        if results['idle_report']['count'] > 0: logger.info(f"Found {results['idle_report']['count']} potentially idle NAT GWs.")

    except ClientError as e: results['errors'].append(f"Desc NAT GW Err: {e}")
    logger.info(f"--- Finished NAT Gateway Idle Reporting in {region} ---")
    return results, results['savings']

# --- optimize_security_groups ---
def optimize_security_groups(ec2_client, region):
    logger.info(f"--- Starting Unused Security Group Reporting in {region} ---")
    results = { "errors": [], "unused_report": {"count": 0, "details": []}, "skipped": [] }
    if not ENABLE_UNUSED_SECURITY_GROUP_REPORTING:
        results["summary_lines"] = ["Unused SG reporting disabled."]
        return results, 0.0

    try:
        all_sgs={}; used_sgs=set(); unused_details = []
        paginator_sg = ec2_client.get_paginator('describe_security_groups')
        for page in paginator_sg.paginate():
            for sg in page.get('SecurityGroups', []):
                if sg.get('GroupName') != 'default': all_sgs[sg['GroupId']] = {'Name': sg['GroupName'], 'Tags': sg.get('Tags', [])}

        logger.info(f"[{region}] Found {len(all_sgs)} non-default SGs. Checking ENIs...")
        try:
            paginator_eni = ec2_client.get_paginator('describe_network_interfaces')
            for page in paginator_eni.paginate():
                for eni in page.get('NetworkInterfaces', []):
                    for group in eni.get('Groups', []): used_sgs.add(group['GroupId'])
        except ClientError as e: results['errors'].append(f"SG Check ENI Err: {e}")

        # Basic check: SG exists but wasn't found on any ENI
        for sg_id, sg_info in all_sgs.items():
            if sg_id not in used_sgs:
                 if not is_excluded(sg_info['Tags']):
                      unused_details.append(f"{sg_id}({sg_info['Name']})")
                 else:
                      results['skipped'].append(sg_id) # Track skipped

        results['unused_report']['count'] = len(unused_details)
        results['unused_report']['details'] = unused_details
        if results['unused_report']['count'] > 0: logger.info(f"Found {results['unused_report']['count']} potentially unused SGs.")

    except ClientError as e: results['errors'].append(f"Desc SG Err: {e}")
    except Exception as e: results['errors'].append(f"SG Assoc Check Err: {e}")
    logger.info(f"--- Finished Unused Security Group Reporting in {region} ---")
    return results, 0.0 # No savings


# --- Main Handler ---
def lambda_handler(event, context):
    """Main Lambda execution entry point."""
    # Initialize savings totals dictionary
    savings_totals = {
        "EC2": 0.0, "EBS": 0.0, "ELB": 0.0, "EIP": 0.0, "NAT Gateway": 0.0,
        "Security Group": 0.0, "CloudWatch Logs": 0.0, "CloudWatch Alarms": 0.0,
        "RDS": 0.0, "S3": 0.0, "Lambda": 0.0, "EKS": 0.0
    }
    all_regional_results = {} # Store structured results per region/service
    all_regional_errors = {} # Store errors per region

    # --- Get Environment Variables ---
    report_bucket_name = os.environ.get("REPORT_BUCKET_NAME")
    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
    # Use a local variable for DRY_RUN for clarity within the handler scope
    dry_run_env = os.environ.get('DRY_RUN', 'true').lower() == 'true'
    target_regions_str = os.environ.get("TARGET_REGIONS", os.environ.get('AWS_REGION', 'us-east-1')) # Default to current region if not set
    target_regions = [region.strip() for region in target_regions_str.split(',') if region.strip()]
    # Note: S3 client region doesn't matter for list_buckets, but needed for location check
    # Other clients should be instantiated per-region in the loop


    if not report_bucket_name or not sns_topic_arn:
        error_message = f"Missing required ENV VAR(s): {'REPORT_BUCKET_NAME ' if not report_bucket_name else ''}{'SNS_TOPIC_ARN' if not sns_topic_arn else ''}".strip()
        logger.error(error_message)
        return {"statusCode": 500, "body": json.dumps({"error": error_message})}

    logger.info("--- Starting Cloud Infra Cost Optimizer ---")
    start_time = datetime.now(timezone.utc)
    logger.info(f"Timestamp: {start_time.isoformat()}")
    if dry_run_env:
        logger.warning("DRY RUN mode enabled.")
    else:
        logger.warning("DRY RUN mode disabled. CHANGES WILL BE APPLIED.")

    regions_to_process = target_regions
    logger.info(f"Target regions: {regions_to_process}")

    # --- Loop through Regions ---
    for region in regions_to_process:
        logger.info(f"--- Processing Region: {region} ---")
        region_start_time = datetime.now(timezone.utc)
        region_results_dict = {}
        region_errors = []
        try:
            # Create boto3 clients for the current region
            session = boto3.Session(region_name=region)
            # Create an S3 client - it's region-agnostic for list_buckets but good practice
            # Need a separate client for upload potentially in Lambda's region later
            s3_client_regional = session.client("s3")
            clients = {
                "ec2": session.client("ec2"),
                "elbv2": session.client("elbv2"),
                "cloudwatch": session.client("cloudwatch"),
                "logs": session.client("logs"),
                "rds": session.client("rds"),
                "s3": s3_client_regional, # Pass regional client
                "lambda": session.client("lambda"),
                "eks": session.client("eks"),
                "compute-optimizer": session.client("compute-optimizer"),
                # Add other clients as needed
            }

            # Map service names to their optimization functions and arguments
            service_processing_map = {
                "EC2": (optimize_ec2, [clients["ec2"], clients["cloudwatch"], clients["compute-optimizer"], region, context]), # Pass context to EC2
                "EBS": (optimize_ebs, [clients["ec2"], clients["cloudwatch"], region]),
                "ELB": (optimize_load_balancers, [clients["elbv2"], clients["cloudwatch"], region]),
                "EIP": (optimize_elastic_ips, [clients["ec2"], region]),
                "CloudWatch Logs": (optimize_cloudwatch_logs, [clients["logs"], region]),
                "CloudWatch Alarms": (report_cloudwatch_alarms, [clients["cloudwatch"], region]),
                "RDS": (optimize_rds, [clients["rds"], clients["cloudwatch"], region]),
                "S3": (optimize_s3, [clients["s3"], region]), # Pass regional client
                "Lambda": (optimize_lambda_functions, [clients["lambda"], clients["cloudwatch"], region]),
                "EKS": (optimize_eks_clusters, [clients["eks"], region]),
                "NAT Gateway": (optimize_nat_gateways, [clients["ec2"], clients["cloudwatch"], region]),
                "Security Group": (optimize_security_groups, [clients["ec2"], region]),
            }

            # Process each service
            for service_name, (func, args) in service_processing_map.items():
                srv_start = datetime.now(timezone.utc)
                logger.info(f"[{region}] Running {service_name} checks...")
                try:
                    # Call the optimization function
                    result = func(*args) # Unpack arguments

                    # Process the result (expecting dict or tuple(dict, float))
                    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], dict) and isinstance(result[1], (float, int)):
                        result_dict, savings = result
                    elif isinstance(result, dict):
                        result_dict = result
                        savings = result.get("savings", 0.0) # Get savings from dict if available, else 0
                    else:
                        logger.error(f"[{region}] Invalid return type from {func.__name__}. Expected dict or (dict, float). Got: {type(result)}")
                        result_dict = {"errors": [f"Invalid return type from function: {type(result)}."]}
                        savings = 0.0

                    # Ensure savings is non-negative before adding
                    current_service_savings = max(0.0, float(savings))
                    savings_totals[service_name] += current_service_savings
                    region_results_dict[service_name] = result_dict

                    # Collect errors
                    if result_dict.get("errors"):
                        region_errors.extend([f"{service_name}:{e}" for e in result_dict["errors"]])

                except Exception as e:
                    logger.error(f"[{region}] UNHANDLED Error in {service_name}: {e}", exc_info=True)
                    # Store error information for the report
                    region_results_dict[service_name] = {"errors": [f"Unhandled Exception: {e}"]}
                    region_errors.append(f"{service_name}:Unhandled:{e}")
                logger.info(f"[{region}] Finished {service_name}. Duration: {datetime.now(timezone.utc) - srv_start}")

            # Store results for the region
            all_regional_results[region] = region_results_dict

        except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
            error_msg = f"AWS Client/Credential error processing region {region}: {e}"
            logger.error(f"!!! {error_msg}", exc_info=True)
            all_regional_results[region] = {"Error": error_msg}
            region_errors.append(f"Client/Cred Error: {e}")
        except Exception as e:
            error_msg = f"Unexpected error processing region {region} setup: {e}"
            logger.error(f"!!! {error_msg}", exc_info=True)
            all_regional_results[region] = {"Error": error_msg}
            region_errors.append(f"Setup Error: {e}")

        # Store regional errors if any occurred
        if region_errors:
            all_regional_errors[region] = region_errors

        logger.info(f"--- Finished processing region {region}. Duration: {datetime.now(timezone.utc) - region_start_time} ---")

    # --- Aggregated Metrics & Report Data ---
    total_regions_processed = len(regions_to_process)
    total_errors_count = sum(len(v) for v in all_regional_errors.values())
    total_savings = sum(savings_totals.values()) # Sums the final values for each service

    # Prepare data for the chart
    chart_labels = ["EC2", "EBS", "ELB", "EIP", "NAT GW", "SG", "CW Logs", "RDS", "S3", "Lambda", "EKS"] # Define labels for chart
    # Map labels to keys in savings_totals, handle potential name differences
    chart_label_to_key = {
        "EC2": "EC2", "EBS": "EBS", "ELB": "ELB", "EIP": "EIP",
        "NAT GW": "NAT Gateway", "SG": "Security Group", "CW Logs": "CloudWatch Logs",
        "RDS": "RDS", "S3": "S3", "Lambda": "Lambda", "EKS": "EKS"
    }
    chart_values = [savings_totals.get(chart_label_to_key.get(label, label), 0.0) for label in chart_labels]
    savings_data_for_js = {"labels": chart_labels, "values": chart_values}
    savings_json_str = json.dumps(savings_data_for_js)

    # --- Build HTML Report ---
    html_lines = [
        "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>",
        "<title>Cloud Infra Cost Optimizer Report</title>",
        "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>",
        # Basic Styling
        "<style>",
        "body{font-family: system-ui, sans-serif; margin: 20px; line-height: 1.5; background-color: #f8f9fa; color: #212529;}",
        "h1, h2, h3, h4 {color: #007bff; margin-top: 1.5em; margin-bottom: 0.5em;}",
        "h1 {text-align: center; border-bottom: 2px solid #dee2e6; padding-bottom: 10px;}",
        ".meta-info {text-align: center; margin-bottom: 2em; color: #6c757d;}",
        ".region-summary {background-color: #fff; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}",
        ".region-summary h3 {color: #17a2b8; margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 5px;}",
        ".service-details {margin-left: 1em; border-left: 3px solid #eee; padding-left: 1em; margin-bottom: 1em;}",
        ".service-details h4 {color: #6c757d; margin-top: 1em; font-size: 1.1em; margin-bottom: 0.3em;}",
        ".service-savings {font-weight: bold; color: #28a745; margin-bottom: 0.5em;}", # Style for service savings
        ".summary-section {margin-top: 30px; padding: 20px; background-color: #fff; border: 1px solid #dee2e6; border-radius: 5px;}",
        "pre {background-color: #e9ecef; padding: 5px 8px; border: 1px solid #ced4da; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; font-size: 0.9em; margin-top: 5px; margin-bottom: 5px;}",
        "strong {color: #495057;}",
        "ul {list-style: none; margin-left: 0; padding-left: 5px;} li {margin-bottom: 3px;}",
        ".notes {font-size: 0.9em; color: #6c757d; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px;}",
        ".chart-container {max-width: 800px; margin: 20px auto; height: 450px;}",
        "</style>",
        "</head><body>",
        "<h1>Cloud Infra Cost Optimizer Report</h1>",
        f"<div class='meta-info'><strong>Execution Time:</strong> {start_time.isoformat()}<br/><strong>DRY RUN Mode:</strong> {dry_run_env}</div>",
        "<h2>Regional Details</h2>"
    ]

    if all_regional_results:
        # Helper function to format details lists safely
        def format_details_list_html(data_dict, key, title, limit=10):
            items = data_dict.get(key, {}).get('details', [])
            count = data_dict.get(key, {}).get('count', 0) # Default count to 0
            if count == 0 and items: count = len(items)
            elif count > 0 and not items: count = 0
            lines = []
            if data_dict.get(key) is not None:
                if count > 0:
                    lines.append(f"<p><strong>{title}:</strong> {count} item(s)</p><ul>")
                    for detail in items[:limit]:
                        safe_detail = str(detail).replace('&', '&').replace('<', '<').replace('>', '>')
                        lines.append(f"<li><pre>{safe_detail}</pre></li>")
                    if len(items) > limit: lines.append("<li>...</li>")
                    lines.append("</ul>")
                else:
                    lines.append(f"<p><strong>{title}:</strong> None found/identified.</p>")
            return lines

        # Iterate through regions and services to build the report body
        for region, region_data in all_regional_results.items():
            html_lines.append(f"<div class='region-summary'><h3>Region: {region}</h3>")
            if "Error" in region_data:
                html_lines.append(f"<pre style='color: red;'><strong>Error:</strong> {region_data['Error']}</pre>")
            else:
                # Defined order for services in the report
                service_order = ["EC2", "EBS", "ELB", "EIP", "NAT Gateway", "Security Group", "CloudWatch Logs", "CloudWatch Alarms", "RDS", "S3", "Lambda", "EKS"]

                for service in service_order:
                    if service in region_data:
                        service_result = region_data[service]
                        html_lines.append(f"<div class='service-details'><h4>{service}</h4>")

                        # --- Display Savings Info ---
                        service_savings = savings_totals.get(service, 0.0) # Use aggregated total for consistency

                        # Special handling for EC2 to show breakdown
                        if service == "EC2":
                            term_sav = service_result.get('termination_savings', 0.0)
                            co_sav = service_result.get('co_potential_savings', 0.0)
                            html_lines.append(f"<p style='margin-bottom: 0.2em;'><strong>Savings from Terminations:</strong> ${term_sav:.2f}/mo</p>")
                            html_lines.append(f"<p style='margin-bottom: 0.2em;'><strong>Potential Savings (Recommendations):</strong> ${co_sav:.2f}/mo</p>")
                            html_lines.append(f"<p class='service-savings'>Total Estimated EC2 Savings: ${service_savings:.2f}/mo</p>") # Shows combined
                        # Special handling for EKS to show breakdown
                        elif service == "EKS":
                             unused_sav = service_result.get('unused_report', {}).get('savings', 0.0) # Get from results if stored, else calc approx
                             ext_sav = service_result.get('extended_support_report', {}).get('savings', 0.0) # Get from results if stored
                             # Recalculate approx if needed (better to store in results dict if possible)
                             if unused_sav == 0.0 and service_result.get('unused_report', {}).get('count', 0) > 0:
                                 unused_sav = service_result['unused_report']['count'] * EKS_CONTROL_PLANE_PRICE_HOURLY * 24 * 30.44
                             if ext_sav == 0.0 and service_result.get('extended_support_report', {}).get('count', 0) > 0:
                                 ext_sav = service_result['extended_support_report']['count'] * EKS_EXTENDED_SUPPORT_PRICE_HOURLY * 24 * 30.44

                             html_lines.append(f"<p style='margin-bottom: 0.2em;'><strong>Potential Savings (Unused):</strong> ${unused_sav:.2f}/mo</p>")
                             html_lines.append(f"<p style='margin-bottom: 0.2em;'><strong>Potential Savings (Extended Support):</strong> ${ext_sav:.2f}/mo</p>")
                             html_lines.append(f"<p class='service-savings'>Total Estimated EKS Savings: ${service_savings:.2f}/mo</p>") # Shows combined
                        else:
                            # Default display for other services
                            html_lines.append(f"<p class='service-savings'>Estimated Savings: ${service_savings:.2f}/mo</p>")
                        # --- End Display Savings Info ---


                        # --- Display Details ---
                        if service == "EC2":
                            action = "Would Terminate" if dry_run_env else "Terminated"
                            html_lines.extend(format_details_list_html(service_result, 'terminated_action', action))
                            html_lines.extend(format_details_list_html(service_result, 'older_gen_report', "Older Generation Report"))
                            html_lines.extend(format_details_list_html(service_result, 'compute_optimizer_report', "Compute Optimizer Report"))
                        elif service == "EBS":
                            action_del = "Would Delete" if dry_run_env else "Deleted"; action_conv = "Would Convert" if dry_run_env else "Converted"
                            html_lines.extend(format_details_list_html(service_result, 'deleted_vol_action', f"{action_del} Available Volumes"))
                            html_lines.extend(format_details_list_html(service_result, 'converted_vol_action', f"{action_conv} Volumes (gp2->gp3)"))
                            html_lines.extend(format_details_list_html(service_result, 'deleted_snap_action', f"{action_del} Old Snapshots"))
                            html_lines.extend(format_details_list_html(service_result, 'idle_vol_report', "Potentially Idle Volumes Report"))
                        elif service == "RDS":
                            action_mod = "Would Modify" if dry_run_env else "Modified"; action_del = "Would Delete" if dry_run_env else "Deleted"
                            html_lines.extend(format_details_list_html(service_result, 'modified_inst_ret_action', f"{action_mod} Instance Retention"))
                            html_lines.extend(format_details_list_html(service_result, 'modified_clus_ret_action', f"{action_mod} Cluster Retention"))
                            html_lines.extend(format_details_list_html(service_result, 'deleted_inst_snap_action', f"{action_del} Instance Snapshots"))
                            html_lines.extend(format_details_list_html(service_result, 'deleted_clus_snap_action', f"{action_del} Cluster Snapshots"))
                            html_lines.extend(format_details_list_html(service_result, 'low_cpu_report', "Low CPU Instances Report"))
                        elif service == "ELB": html_lines.extend(format_details_list_html(service_result, 'deleted_action', "Would Delete Idle LBs" if dry_run_env else "Deleted Idle LBs"))
                        elif service == "EIP": html_lines.extend(format_details_list_html(service_result, 'released_action', "Would Release Unattached EIPs" if dry_run_env else "Released Unattached EIPs"))
                        elif service == "NAT Gateway": html_lines.extend(format_details_list_html(service_result, 'idle_report', "Potentially Idle NAT Gateways Report"))
                        elif service == "Security Group": html_lines.extend(format_details_list_html(service_result, 'unused_report', "Potentially Unused Security Groups Report"))
                        elif service == "CloudWatch Logs": html_lines.extend(format_details_list_html(service_result, 'modified_action', "Log Groups Retention Update"))
                        elif service == "CloudWatch Alarms": html_lines.extend(format_details_list_html(service_result, 'insufficient_data_report', "Long Insufficient Data Alarms Report"))
                        elif service == "S3": action = "Objects Identified" if dry_run_env else "Objects Deleted"; html_lines.extend(format_details_list_html(service_result, 'deleted_action', action))
                        elif service == "Lambda": html_lines.extend(format_details_list_html(service_result, 'idle_report', "Potentially Idle Functions Report"))
                        elif service == "EKS":
                            html_lines.extend(format_details_list_html(service_result, 'extended_support_report', "Clusters on Extended Support (Upgrade Required)"))
                            html_lines.extend(format_details_list_html(service_result, 'unused_report', "Potentially Unused Clusters Report"))
                        # --- End Display Details ---

                        # Display errors for the service
                        if service_result.get("errors"):
                            html_lines.append("<p style='color:orange;'><strong>Service Errors:</strong></p><ul>")
                            for err in service_result["errors"][:5]: # Limit displayed errors
                                safe_err = str(err).replace('&', '&').replace('<', '<').replace('>', '>')
                                html_lines.append(f"<li><pre>{safe_err}</pre></li>")
                            if len(service_result["errors"]) > 5:
                                html_lines.append("<li>... (more errors in logs)</li>")
                            html_lines.append("</ul>")
                        html_lines.append("</div>") # End Service Details
            html_lines.append("</div>") # End Region Summary
    else:
        html_lines.append("<p>No regions processed or no results available.</p>")

    # --- Overall Summary and Chart Section ---
    html_lines.extend([
        "<div class='summary-section'><h2>Overall Summary</h2>",
        f"<p><strong>Total Regions Processed:</strong> {total_regions_processed}</p>",
        f"<p><strong>Total Errors Encountered:</strong> {total_errors_count}</p>"
    ])
    if total_errors_count > 0:
        html_lines.append("<p><strong>Errors Summary (by region):</strong></p><ul>")
        for r, e in all_regional_errors.items():
            html_lines.append(f"<li>{r}: {len(e)} error(s)</li>")
        html_lines.append("</ul>")
    html_lines.extend([
        "<h2>Savings Breakdown</h2>",
        "<div class='chart-container'><canvas id='savingsBarChart'></canvas></div>",
        f"<p style='text-align: center; font-size: 1.2em;'><strong>Total Estimated Savings: ${total_savings:.2f}</strong></p>",
        "</div>"
    ])

    # --- Notes Section ---
    html_lines.append("<div class='notes'>")
    if dry_run_env: html_lines.append("<p>Note: Savings are estimated based on DRY RUN mode.</p>")
    def check_svc_processed(svc): return any(svc in r and isinstance(r.get(svc), dict) and "Error" not in r for r in all_regional_results.values() if isinstance(r, dict))
    if check_svc_processed("CloudWatch Logs"): html_lines.append("<p>Note: CW Logs savings reported as $0.00; actual savings vary.</p>")
    if check_svc_processed("Lambda"): html_lines.append("<p>Note: Lambda reports potentially idle functions ($0.00 savings reported).</p>")
    # Updated EKS Note
    if check_svc_processed("EKS"): html_lines.append("<p>Note: EKS savings include estimates for control plane cost of potentially unused clusters and Extended Support charges. Manual verification and cluster upgrades are required.</p>")
    if check_svc_processed("NAT Gateway"): html_lines.append("<p>Note: NAT GW savings estimate for hourly cost of potentially idle gateways. Verify connectivity needs manually.</p>")
    if check_svc_processed("Security Group"): html_lines.append("<p>Note: Unused SG check is basic; requires manual verification before deletion.</p>")
    if check_svc_processed("EC2"): html_lines.append("<p>Note: EC2 savings include direct terminations and potential savings from Compute Optimizer recommendations requiring manual action.</p>")
    if check_svc_processed("EBS"): html_lines.append("<p>Note: EBS includes idle volume reporting. Manual verification needed.</p>")
    if check_svc_processed("RDS"): html_lines.append("<p>Note: RDS includes low CPU reporting. Consider downsizing after analysis.</p>")
    html_lines.append("</div>")

    # --- Embedded JavaScript for Chart ---
    html_lines.append("<script>")
    html_lines.append(f"const savingsData = {savings_json_str};")
    html_lines.append("const ctxBar = document.getElementById('savingsBarChart').getContext('2d');")
    html_lines.append("new Chart(ctxBar, { type: 'bar', data: {")
    html_lines.append("  labels: savingsData.labels, datasets: [{")
    html_lines.append("    label: 'Estimated Monthly Savings ($)', data: savingsData.values,")
    html_lines.append("    backgroundColor: ['#D9534F', '#5BC0DE', '#F0AD4E', '#5CB85C', '#FFB04E', '#7E827A', '#6E54D9', '#0275D8', '#F7AC49', '#FF9900', '#232F3E', '#8C8C8C'],")
    html_lines.append("    borderColor: '#fff', borderWidth: 1")
    html_lines.append("}]}, options: { indexAxis: 'y', scales: { x: { beginAtZero: true, title: { display: true, text: 'USD ($) per Month' } } }, responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, title: { display: true, text: 'Estimated Savings Breakdown by Service', font: { size: 16 } } } } });")
    html_lines.append("</script>")
    html_lines.append("</body></html>")
    html_content = "\n".join(html_lines)

    # --- Finalize and Upload Report ---
    report_url = f"s3://{report_bucket_name}/ERROR_UPLOADING_REPORT.html" # Default URL
    try:
        # Use default session for upload client (usually same region as Lambda)
        s3_client_upload = boto3.client("s3")
        report_time_str = start_time.strftime('%Y-%m-%dT%H-%M-%SZ')
        report_key_prefix = os.environ.get('REPORT_KEY_PREFIX', 'cost-optimizer-reports/')
        if report_key_prefix and not report_key_prefix.endswith('/'): report_key_prefix += '/'
        report_key = f"{report_key_prefix}{report_time_str}-report.html"
        report_url = upload_report_to_s3(s3_client_upload, report_bucket_name, report_key, html_content)
    except Exception as e:
        logger.error(f"Failed to upload report to S3: {e}", exc_info=True)

    # --- Send SNS Notification ---
    try:
        # Use default session for SNS client
        sns_client = boto3.client("sns")
        action_desc = 'DRY RUN' if dry_run_env else 'ACTION TAKEN'
        sns_subject = f"Cost Optimizer Report ({action_desc}) - ${total_savings:.2f} Savings Est"
        sns_message = ( f"Optimizer execution completed.\n\nMode: {action_desc}\nTime: {start_time.isoformat()}\n"
                        f"Total Savings Est: ${total_savings:.2f}\nRegions: {total_regions_processed}, Errors: {total_errors_count}\n\n"
                        f"Report URL: {report_url}" )
        send_sns_notification(sns_client, sns_topic_arn, sns_subject, sns_message)
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {e}", exc_info=True)

    end_time = datetime.now(timezone.utc)
    logger.info(f"--- Cloud Infra Cost Optimizer execution finished. Total Duration: {end_time - start_time} ---")

    # Return summary information
    return { "statusCode": 200, "body": json.dumps({ "message": f"Run complete. Report URL: {report_url}", "totalSavings": total_savings, "dryRun": dry_run_env, "errors": total_errors_count, "regionsProcessed": total_regions_processed }) }

# --- Placeholder Helper Functions (Define these properly in your code) ---
def upload_report_to_s3(s3_client, bucket_name, report_key, report_content):
    """Uploads the report to S3 (HTML) and generates a pre-signed URL."""
    try:
        report_bytes = report_content.encode('utf-8')
        s3_client.put_object( Bucket=bucket_name, Key=report_key, Body=report_bytes, ContentType="text/html; charset=utf-8" )
        logger.info(f"Report uploaded to S3: s3://{bucket_name}/{report_key}")
        try:
             presigned_url = s3_client.generate_presigned_url( 'get_object', Params={'Bucket': bucket_name, 'Key': report_key}, ExpiresIn=604800 ) # 7 days
             logger.debug(f"Generated pre-signed URL (valid 7 days)")
             return presigned_url
        except ClientError as e:
             logger.error(f"Could not generate pre-signed URL: {e}. Returning S3 URI.")
             return f"s3://{bucket_name}/{report_key}"
    except ClientError as e: logger.error(f"Error uploading report to S3: {e}"); return f"s3://{bucket_name}/{report_key}"
    except Exception as e: logger.error(f"Unexpected error during S3 report upload: {e}", exc_info=True); raise

def send_sns_notification(sns_client, topic_arn, subject, message):
    """Sends a notification to the specified SNS topic."""
    try:
        if len(message.encode('utf-8')) > 256 * 1024: logger.warning("SNS message potentially exceeds 256KB limit, truncating."); message = message[:30000] + "\n... (message truncated)"
        response = sns_client.publish(TopicArn=topic_arn, Subject=subject, Message=message)
        logger.info(f"Notification sent to SNS {topic_arn}. Msg ID: {response.get('MessageId')}")
    except ClientError as e: logger.error(f"Error sending SNS notification: {e}")
    except Exception as e: logger.error(f"Unexpected error sending SNS: {e}", exc_info=True)
