{
  "ImageId": "@@AMI_ID@@",
  "InstanceType": "t3.micro",
  "IamInstanceProfile": { "Name": "ubuntu-order-worker-profile" },
  "SecurityGroupIds": ["@@WORKER_SG@@"],
  "MetadataOptions": { "HttpTokens": "required", "HttpEndpoint": "enabled" },
  "UserData": "@@USERDATA_B64@@",
  "TagSpecifications": [
    {
      "ResourceType": "instance",
      "Tags": [
        { "Key": "Name", "Value": "ubuntu-order-worker" },
        { "Key": "Project", "Value": "aws-decoupled-order-pipeline" }
      ]
    }
  ]
}
