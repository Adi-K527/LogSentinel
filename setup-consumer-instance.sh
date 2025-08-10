EC2_USER="ec2-user"
EC2_HOST="13.217.103.34"
KEY_PATH="C:\Users\adika\Downloads\terraform-key.pem"

# Upload docker-compose.yaml to EC2 instance
scp -i "$KEY_PATH" consumer/docker-compose.yaml "$EC2_USER@$EC2_HOST:~/docker-compose.yaml"

ssh -i "$KEY_PATH" "$EC2_USER@$EC2_HOST" << EOF
    sudo yum update -y
    sudo yum install -y docker
    sudo amazon-linux-extras enable selinux-ng
    sudo yum clean metadata
    sudo yum install -y selinux-policy-targeted
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    sudo docker-compose -f ~/docker-compose.yaml up -d
EOF