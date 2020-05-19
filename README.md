# sls-python-aws-template

A template repository for Serverless framework projects built with Python 3 and AWS.


## How To Use


### Use this template to create a new project

See [Creating a repository from a template](https://help.github.com/en/articles/creating-a-repository-from-a-template)
to get started with creating a new repository for your project.

After you have created your repository, you should complete the following steps:

1. Modify the `service.name` value defined in `serverless.core.yml`. 
    Note that you will probably want to keep the `${self:custom.prefix}` part for your own
    development purposes.
2. Review the boilerplate configuration in `serverless.core.yml` file 
    as well as the `sls_custom/stage_derived/` YAML files and tailor their contents according
    to the needs to your project. Be sure to remove anything that you do not need!
3. Review the default API Gateway Authorizer functionality. The example Authorizer
    that ships with these examples is configured to require a valid Thor-issued JWT in order
    to allow requests to any other endpoint in the service. You should update this if your
    project has different authorization and authentication requirements.
4. Remove the example `HttpGetGreeting` Lambda function definition from `serverless.core.yml` 
    as well as its associated handler code, located at `src.handlers.get_greeting__http`.
5. Review the CI/CD settings defined in `.circleci/config.yml` and modify according to the needs
    of your team and this project. Specifically, you should set the `mentions` parameter for the
    workflow's `slack/approval-notification` job to the Slack username(s) who should be notified
    when the pipeline is waiting for approval. Generally, this should be your team's product 
    manager.
6. If you are using a version of Python greater than `3.6`, you should modify the CircleCI
    workflow Docker images as well as the Lambda function runtimes accordingly.


### Run the service provided by this template as an interactive example

This template provides a fully-functioning, deployable Serverless service. If you want to
explore this example in a live environment, you may do so by either cloning this template
repository or by creating a new, unmodified repository based on this template.

**Important Notes:** 
- You should only deploy this project to the Sandbox AWS account. 
    You should make sure your local development environment is configured to use the 
    correct development role for that account. 
- Make sure to clean up when you are done!

1. Deploy the service to a new CloudFormation stack:
    ```shell
    npm run sls-deploy
    ```
    
    **Note:** Your stack, as well as most of the resources it contains, will be prefixed
    with your local machine's username (obtained as the output of the `id -un` command).
2. Navigate to the [CloudFormation web console](https://us-west-2.console.aws.amazon.com/cloudformation/home)
    in your browser (remember to first navigate to the correct AWS account!) and locate your
    newly-deployed stack. From here, you may explore the infrastructure that makes up your service.
3. If you want to make HTTP requests: 
    - You must have a JWT signed with the secret key value defined in SSM 
        for the Sandbox deployment environment. By default, your service expects an SSM parameter
        at `/thor/sandbox/secret_key` to provide this value (referenced by Lambda functions 
        using the `THOR_API_SECRET_KEY__SSM_KEY` environment variable).
        
        If you need to obtain a JWT without making a request to Thor, try this in your terminal:
        ```cli
        export THOR_SECRET_KEY=$(aws ssm get-parameter --name /thor/sandbox/secret_key --region us-west-2 --with-decryption | jq .Parameter.Value -r)
        export MY_JWT=$(pyjwt --key=$THOR_SECRET_KEY encode user_id=myuserid first_name=Alice last_name=McTesterson)
        ```
        
        Note that this command assumes the following:
        1. You have AWS CLI and `pyjwt` (bundled with this project) installed in your current shell
        2. Your shell has permissions to retrieve and decrypt the `/thor/sandbox/secret_key` 
            SSM parameter in the Sandbox AWS account
    
    - Note the `ServiceBaseUrl` output printed to your command line when you deployed your stack.
        This URL is used for all example endpoints in this service. This value may also be found
        in the Outputs section of your CloudFormation stack.
        
    - Once you have obtained or generated a valid JWT, you must provide it in an `Authorization`
        header in all requests to this service.
    
    - Refer to the following examples for making `curl` requests
        
        ```cli
        curl $SERVICE_BASE_URL/v1/greeting -H "Authorization: Bearer $MY_JWT"
        curl $SERVICE_BASE_URL/v1/greeting?person=Alice -H "Authorization: Bearer $MY_JWT"
        curl $SERVICE_BASE_URL/v1/greeting?person=1234 -H "Authorization: Bearer $MY_JWT"
        ```
        
        Note that the above commands assume that your terminal environment has `$MY_JWT`
        and `$SERVICE_BASE_URL` environment variables defined. Refer to the previous steps
        in this section for more information on setting these environment variables.
4. When you are finished, please destroy your stack by running the following command:

    ```cli
    npm run sls-remove
    ```


## Using CircleCI for CI/CD

This example provides a `.circleci/` directory with a configured deployment pipeline, which
is configured to build and deploy whenever the `master` branch is changed. The pipeline will
first deploy a new build to the Staging environment in AWS and then will wait for manual approval
before continuing. At this point, a Slack notification will be sent to the `#eng-notifications`
channel in order to notify someone (usually a product manager) that there are newly-staged changes
that require approval.

Once/if the changes are approved in CircleCI, the pipeline will deploy the new build to the 
Production environment.


### Pipeline Configuration

You must complete the following steps before using CircleCI with your project:

1. Modify the `slack/approval-notification` job in the workflow (defined in `.circleci/config.yml`)
    so that the appropriate Slack users are notified when the pipeline requires manual approval.
    Note that the value for the `mentions` parameter should be one or more comma-separated
    Slack usernames (no spaces and no `@` symbols).
2. Configure the `SLACK_WEBHOOK` environment variable in your project's settings,
    located at `https://circleci.com/gh/divvydose/<your-repo-name>/edit#env-vars`.


### Reasons for Failure

Although there can be many reasons why a deployment pipeline fails, some are more common than
others. The following is a non-exhaustive list of several scenarios in which the pipeline is meant
to fail:

- **Failing unit tests:** This is the primary reason for failure. Unit tests are executed
    when the workflow runs the `test` job, which executes prior to any deployment
    operations.
- **Unsafe Python dependencies:** The `safety_check` job uses Pipenv to check for known
    [security vulnerabilities](https://pipenv.readthedocs.io/en/latest/advanced/#detection-of-security-vulnerabilities)
    in required packages and will fail if a vulnerable package is detected. This job executes
    prior to any deployment operations.
- **Serverless Build Errors:** Artifacts are built during the `build_preprod` and `build_prod`
    jobs. If either of these steps fail, it generally indicates that Serverless failed to generate
    a CloudFormation stack template (which suggests a problem in `serverless.core.yml` or other
    files used by the Serverless framework to build the CloudFormation stack) or that there was an
    error encountered while building the Lambda Zip artifact from your source code and/or its
    dependencies.
- **Serverless Deployment Errors:** Serverless deploys your CloudFormation stack during the
    `deploy_preprod` and `deploy_prod` jobs. If either of these steps fail _before_ stack updates
    have begun, it usually indicates that the environment in which Serverless is being executed
    does not have sufficient privileges to initiate the deployment in the target AWS environment.
    Failures that occur during deployment suggest that there is a problem within CloudFormation
    (for example, an incorrectly-configured CloudFormation stack resource). When CloudFormation
    errors occur, the stack should roll back to its original state; you should view the even log
    in your CloudFormation stack for insight into the cause of the failure. 
