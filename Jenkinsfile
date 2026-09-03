pipeline {
  environment {
    devRegistry = 'ghcr.io/datakaveri/tgdex-monorepo'
    registryUri = 'https://ghcr.io'
    registryCredential = 'datakaveri-ghcr'
    GIT_HASH = GIT_COMMIT.take(7)
  }
  agent { 
    node {
      label 'slave1' 
    }
  }
  stages {

    stage('Building images') {
      steps{
        script {
          echo 'Pulled - ' + env.GIT_BRANCH
          devImage = docker.build( devRegistry, "-f Dockerfile .")
        }
      }
    }

    stage('Detect config/migration change') {
      when {
        not { changeRequest() }
      }
      steps {
        script {
          def baseCommit = env.GIT_PREVIOUS_SUCCESSFUL_COMMIT
          if (!baseCommit) {
            baseCommit = sh(script: 'git rev-list --max-parents=0 HEAD | tail -1', returnStdout: true).trim()
          }

          def changedFiles = sh(
            script: "git diff --name-only ${baseCommit} HEAD",
            returnStdout: true
          ).trim().split('\n') as List

          env.CONFIG_CHANGED = changedFiles.contains('example-config/.community-server.env') ? 'true' : 'false'
          env.MIGRATION_CHANGED = changedFiles.any { it.startsWith('stack/postgres/init-scripts/') } ? 'true' : 'false'

          echo "Diffing against ${baseCommit} (last successful build's commit): config changed=${env.CONFIG_CHANGED}, migration changed=${env.MIGRATION_CHANGED}"
        }
      }
    }

    stage('Continuous Deployment') {
      when {
        allOf {
          anyOf {
            changeset "src/**"
            changeset "Dockerfile"
            changeset "pyproject.toml"
            changeset "example-config/.community-server.env"
            changeset "stack/postgres/init-scripts/**"
            triggeredBy cause: 'UserIdCause'
          }
          expression {
            return env.GIT_BRANCH == 'origin/dev';
          }
        }
      }
      stages {
        stage('Push Images') {
          steps {
            script {
              def tagSuffix = ''
              if (env.CONFIG_CHANGED == 'true') {
                tagSuffix += '-C'
              }
              if (env.MIGRATION_CHANGED == 'true') {
                tagSuffix += '-M'
              }
              env.IMAGE_TAG = "1.0.0-${env.GIT_HASH}${tagSuffix}"
              docker.withRegistry( registryUri, registryCredential ) {
                devImage.push(env.IMAGE_TAG)
              }
            }
          }
        }
        stage('EKS Helm deployment') {
          steps {
            script {
              sh "ssh ubuntu@dev-eks 'cd v2-deployments/iudx/iudx-installer/K8s-deployment/Charts/community-layer && helm upgrade community-server . -n community-server --atomic --timeout 5m --reuse-values --set image.tag=${env.IMAGE_TAG}'"
              sh 'sleep 15'
              sh '''#!/bin/bash 
              response_code=$(curl -s -o /dev/null -w \'%{http_code}\\n\' --connect-timeout 5 --retry 5 --retry-connrefused -XGET https://v2.dev.community-layer.iudx.io/docs)

              if [[ "$response_code" -ne "200" ]]
              then
                echo "Health check failed"
                exit 1
              else
                echo "Health check complete; Server is up."
                exit 0
              fi
              '''                
            }
          }
          post{
            failure{
              error "Failed to deploy image to EKS via Helm"
            }
          }
        }
      }
    }
  }
  post{
    failure{
      script{
        if (env.GIT_BRANCH == 'origin/dev')
        emailext recipientProviders: [buildUser(), developers()], to: '$COMMUNITY_LAYER_RECIPIENTS, $DEFAULT_RECIPIENTS', subject: '$PROJECT_NAME - Build # $BUILD_NUMBER - $BUILD_STATUS!', body: '''$PROJECT_NAME - Build # $BUILD_NUMBER - $BUILD_STATUS:
Check console output at $BUILD_URL to view the results.'''
      }
    }
  }
}
