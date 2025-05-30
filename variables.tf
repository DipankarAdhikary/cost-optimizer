variable "low_severity_error_keywords" {
  description = "List of low severity error keywords to monitor"
  type        = list(string)
  default     = [
    "Communication Failure", "NullPointerException", "FormatFactory writeObject failed",
    "Application encountered error", "Request failed: UnknownHostException", "cannot be cast to class",
    "Algorithm negotiation fail", "ActiveMQConnectionTimedOutException", "Mandate not found", "ReadTimeOut",
    "Incoming Communications failed", "Failed to load payment file", "FormatFactory: 1 errors",
    "Could not find nor determine order type", "incoming routing is missing", "Database upgrade failed:",
    "objects present in a non-final state", "objects present in pending/partial approved",
    "FailureException: javax.persistence.PersistenceException", "LockAcquisitionException", "RollbackException",
    "UnmarshalException: Problem finding error class", "EJB Invocation failed on component CRUDSessionBean",
    "Not in GZIP format", "EmptyStackException: Empty stack", "org.bouncycastle.openpgp.PGPException","updated by another user","create netty connection"
  ]
}

variable "medium_severity_error_keywords" {
  description = "List of medium severity error keywords to monitor"
  type        = list(string)
  default     = [
    "Deadlock", "OutOfMemoryError", "SocketTimeout", "TransactionTimeout", "java.net.SocketException", 
    "GenericJDBCException", "OptimisticLockException", "java.net.ConnectException", 
    "com.microsoft.sqlserver.jdbc.SQLServerException:"
  ]
}

variable "high_severity_error_keywords" {
  description = "List of high severity error keywords to monitor"
  type        = list(string)
  default     = [
    "SAML response is not signed", "TwoPhaseOutcome.HEURISTIC_HAZARD", 
    "java.sql.SQLException: pingDatabase failed status=-1"
  ]
}

variable "namespace" {
  description = "The CloudWatch namespace for metrics"
  type        = string
  default     = "Payment-Hub_Application_Error_Monitoring"
}

variable "cus_short_lower" {
  description = "Customer short code in lowercase"
  type        = string
}

variable "app_short_lower" {
  description = "Application short code in lowercase"
  type        = string
}

variable "env_short_lower" {
  description = "Environment short code in lowercase"
  type        = string
}

variable "env_code_lower" {
  description = "Environment code (p for production, etc.)"
  type        = string
  default     = ""
}

variable "alarm_prefix" {
  description = "Prefix for alarm names"
  type        = string
  default     = "FIS-Monitoring"
}

variable "period" {
  description = "The period in seconds over which the metrics are evaluated"
  type        = number
  default     = 60
}

variable "callout" {
  type        = string
  default     = "N"
  description = "If specified and set to Y, xMatters will initiate a callout to the appropriate team after the incident is created."
}

variable "tag_support_group" {
  description = "The name of the group responsible for the deployed asset."
  default     = "Corporate Liquidity - Platform - Payment Hub Standard Edition Technical Support"
}

variable "tag_app_group_email" {
  description = "The email address for the operations team responsible for the deployed asset."
  default     = "cm.cl.platform.paymenthubtechnicalsupport@fisglobal.com"
}

variable "tag_solution_central_id" {
  description = "The Asset ID related to the entry in Solution Central for the product to be deployed on the given asset."
  type        = string
  default     = "12215"
}

variable "tag_environment_type" {
  description = "The tier of environment for the application -- this is separate from the service level defined at the subscription level."
  default     = "Production"
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

variable "enable_fis_monitoring" {
  type        = bool
  default     = true
  description = "Whether or not to enable FIS monitoring.  Default is to disable it."
}

variable "evaluation_periods" {
  description = "Number of periods to evaluate for the alarm"
  type        = number
  default     = 1
}

variable "threshold" {
  description = "Threshold for triggering alarms"
  type        = number
  default     = 1
}

