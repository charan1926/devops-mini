pipeline {
  agent any
  environment {
    DOCKER_IMAGE  = "charan1926/devops-mini"
    K8S_NAMESPACE = "devops-mini"
    SHORT_SHA     = ""
    TAG           = ""
  }
  options { timestamps() }

  stages {
    stage('Checkout') {
  steps {
    // if you're using "Pipeline script from SCM", keep `checkout scm`.
    // if inline job, use the `git ...` line instead.
    checkout scm
    // git branch: 'main', url: 'https://github.com/charan1926/devops-mini.git'

    script {
      // robust: get short SHA directly into env.TAG
      env.TAG = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD').trim()
    }
    echo "Building ${env.DOCKER_IMAGE}:${env.TAG} for ns ${env.K8S_NAMESPACE}"
  }
}
    }

    stage('Sanity: kubectl on agent') {
      steps {
        sh 'kubectl version --client'
        sh 'kubectl get ns | head -5'
      }
    }

    stage('Build Image') {
      steps {
        sh 'docker build -t ${DOCKER_IMAGE}:${TAG} .'
      }
    }

    stage('Login & Push') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
          sh '''
            echo "$PASS" | docker login -u "$USER" --password-stdin
            docker push ${DOCKER_IMAGE}:${TAG}
          '''
        }
      }
    }

    stage('Render Manifests') {
      steps {
        sh 'sed "s|PLACEHOLDER_TAG|${TAG}|g" k8s/app-deploy.yaml > k8s/app-deploy.rendered.yaml'
      }
    }

    stage('Deploy to K8s') {
      steps {
        sh '''
          kubectl apply -f k8s/namespace.yaml
          kubectl apply -f k8s/redis.yaml -n ${K8S_NAMESPACE}
          kubectl apply -f k8s/app-deploy.rendered.yaml -n ${K8S_NAMESPACE}
          kubectl rollout status deploy/flask-app -n ${K8S_NAMESPACE} --timeout=120s
        '''
      }
    }

    stage('Smoke Test (in-cluster)') {
      steps {
        sh '''
          kubectl -n ${K8S_NAMESPACE} run curl --rm -it --image=curlimages/curl:8.7.1 --restart=Never -- \
            sh -lc 'for i in 1 2 3; do curl -s http://flask-svc:5000/ | grep -q \\"status\\":\\"ok\\" && echo ok || exit 1; sleep 2; done'
        '''
      }
    }
  }

  post {
    success {
      sh 'kubectl get pods,svc -n ${K8S_NAMESPACE}'
      echo "Deployed ${env.DOCKER_IMAGE}:${env.TAG} to ${env.K8S_NAMESPACE}"
    }
    failure {
      echo "Deployment failed. Try: kubectl rollout undo deploy/flask-app -n ${env.K8S_NAMESPACE}"
    }
  }
}

