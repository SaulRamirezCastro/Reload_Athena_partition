terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region  = "us-east-1"
}

resource "aws_iam_role" "lambda_role_athena" {
  name               = "lambda_role_athena_partition"
  description = "Lambda role for athena reload partition, created by terraform"
  assume_role_policy = "${file("assume-role-policy.json")}"
}

resource "aws_iam_policy" "lambda_policy_athena" {
  name = "lambda_policy_athena_partition"
  path = "/"
  description = "Aws Lambda policy for managing aws lambda role, created by terraform"
  policy =  "${file("aws-iam-policy.json")}"
}

resource "aws_iam_role_policy_attachment" "attach_aim_polity_to_role" {
  role       = aws_iam_role.lambda_role_athena.name
  policy_arn = aws_iam_policy.lambda_policy_athena.arn

}

data "archive_file" "zip_python_code" {
  type        = "zip"
  source_dir = "${path.root}./src/"
  output_path = "${path.module}/src/lambda_athena.zip"
}

resource "aws_lambda_function" "lambda_reload_athena" {
  function_name = "lambda_reload_athena"
  role          = aws_iam_role.lambda_role_athena.arn
  filename = "${path.module}/src/lambda_athena.zip"
  handler = "lambda_function.lambda_handler"
  runtime = "python3.8"
  timeout = 300
  layers = ["arn:aws:lambda:us-east-1:553264372403:layer:layer:1"]
  depends_on = [aws_iam_role_policy_attachment.attach_aim_polity_to_role]
}
