# --- Networking: small self-contained VPC (works in any account, no NAT costs) ---

resource "aws_vpc" "this" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.name}-vpc" }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = { Name = "${var.name}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.20.1.0/24"
  map_public_ip_on_launch = true

  tags = { Name = "${var.name}-public" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = { Name = "${var.name}-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Always-current Windows Server 2022 AMI, resolved via AWS's public SSM parameter
data "aws_ssm_parameter" "windows_ami" {
  name = "/aws/service/ami-windows-latest/Windows_Server-2022-English-Full-Base"
}

# --- Key pair (used to decrypt the Windows Administrator password) ---

resource "tls_private_key" "this" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "this" {
  key_name   = "${var.name}-key"
  public_key = tls_private_key.this.public_key_openssh
}

resource "local_sensitive_file" "private_key" {
  content         = tls_private_key.this.private_key_pem
  filename        = "${path.module}/${var.name}-key.pem"
  file_permission = "0600"
}

# --- Security group: RDP + DCV, only from your IP ---

resource "aws_security_group" "this" {
  name        = "${var.name}-sg"
  description = "RDP and Amazon DCV access for ${var.name}"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "RDP"
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  ingress {
    description = "Amazon DCV web client"
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  ingress {
    description = "Amazon DCV QUIC transport"
    from_port   = 8443
    to_port     = 8443
    protocol    = "udp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    description = "All outbound (Windows updates, Tally, GST/PF/PT portals)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Instance role: SSM (browser fallback via Fleet Manager) + DCV license ---

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "instance" {
  name               = "${var.name}-instance-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Amazon DCV is free on EC2; the server verifies this by reading a license
# file from a regional AWS-owned S3 bucket.
resource "aws_iam_role_policy" "dcv_license" {
  name = "dcv-license"
  role = aws_iam_role.instance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "arn:aws:s3:::dcv-license.${var.region}/*"
    }]
  })
}

resource "aws_iam_instance_profile" "this" {
  name = "${var.name}-profile"
  role = aws_iam_role.instance.name
}

# --- The Windows workstation ---

resource "aws_instance" "this" {
  ami                         = nonsensitive(data.aws_ssm_parameter.windows_ami.value)
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.this.id]
  key_name                    = aws_key_pair.this.key_name
  iam_instance_profile        = aws_iam_instance_profile.this.name
  associate_public_ip_address = true
  disable_api_termination     = true
  user_data                   = file("${path.module}/userdata.ps1")

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    volume_size = var.volume_size_gb
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name   = var.name
    Backup = var.name
  }

  lifecycle {
    # A newer Windows AMI is published monthly and user_data edits also force
    # replacement — either would DESTROY the instance and its data. Never let
    # routine applies replace this machine; restore from a snapshot instead.
    ignore_changes = [ami, user_data]
  }
}
