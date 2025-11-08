pipeline {
  agent any

  environment {
    DOCKER_IMAGE  = "charan1926/devops-mini"   // change if your Docker Hub repo differs
    K8S_NAMESPACE = "devops-mini"
    TAG           = ""                         // filled in Checkout stage
  }

  options { timestamps() }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
        script {
          // compute short SHA and store in env
          env.TAG = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD').trim()
          echo "Computed TAG = ${env.TAG}"
        }
      }
    }

    stage('Sanity: tools') {
      steps {
        sh 'docker --version'
        sh 'kubectl version --client'
      }
    }

    stage('Assert TAG') {
      steps {
        // hard stop if TAG is empty for any reason
        sh '''
          echo "TAG=${TAG}"
          if [ -z "${TAG}" ]; then
            echo "ERROR: TAG is empty. Fix Checkout stage."; exit 1;
          fi
        '''
      }
    }

    stage('Build Image') {
      steps {
        sh '''
          echo "Building ${DOCKER_IMAGE}:${TAG}"
          docker build -t ${DOCKER_IMAGE}:${TAG} .
        '''
      }
    }

    stage('Login & Push') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
          sh '''
            echo "$PASS" | docker login -u "$USER" --password-stdin
            docker push ${DOCKER_IMAGE}:${TAG}
          '''
        }
      }
    }

    stage('Render Manifests') {
      steps {
        sh '''
          sed "s|PLACEHOLDER_TAG|${TAG}|g" k8s/app-deploy.yaml > k8s/app-deploy.rendered.yaml
          echo "Rendered manifest uses image: ${DOCKER_IMAGE}:${TAG}"
        '''
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
