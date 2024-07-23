# Reload hive partition in Aws Athena
Class to reload Aws Athena partition using lambda 

### Project structure 
```txt
├── LICENSE
├── README.md
├── deploy
│        ├── assume-role-policy.json
│        ├── aws-iam-policy.json
│        └── main.tf
│
│       
└── src
    ├── config.yml
    ├── lambda_function.py
    └── reload_athena.py


```


### TO DO:
- [ ] Add Terraform to deploy the project.
