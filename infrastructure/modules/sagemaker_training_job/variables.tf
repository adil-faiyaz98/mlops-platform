# infrastructure/modules/sagemaker_training_job/variables.tf

variable "training_job_name" {
  type = string
  description = "The name of the SageMaker training job."
}

variable "training_image" {
  type = string
  description = "The Docker image to use for training."
}

variable "training_data_uri" {
  type = string
  description = "The S3 URI for the training data."
}

variable "validation_data_uri" {
  type = string
  description = "The S3 URI for the validation data."
}

variable "output_data_uri" {
  type = string
  description = "The S3 URI for the output data (model artifacts)."
}

variable "instance_count" {
  type = number
  description = "The number of instances to use for training."
}

variable "instance_type" {
  type = string
  description = "The type of instance to use for training."
}

variable "volume_size_in_gb" {
  type = number
  description = "The volume size in GB for the training instance."
}

variable "sagemaker_role_arn" {
  type = string
  description = "The ARN of the SageMaker role."
}

variable "max_runtime_in_seconds" {
  type = number
  description = "The maximum runtime in seconds for the training job."
}

variable "static_hyperparameters" {
  type = map(string)
  description = "Static hyperparameters to pass to the training script."
  default = {}
}