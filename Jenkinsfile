pipeline {
  agent any

  environment {
    DOCKER_IMAGE  = "charan1926/devops-mini"   // change if your Docker Hub repo differs
    K8S_NAMESPACE = "devops-mini"
    TAG           = ""                         // computed at runtime
  }

  options { timestamps() }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.TAG = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD').trim()
        }
        echo "Building ${env.DOCKER_IMAGE}:${env.TAG} for ns ${env.K8S_NAMESPACE}"
      }
    }

    stage('Sanity: tools') {
      steps {
        sh 'docker --version'
        sh 'kubectl version --client'
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

    stage('Deploy + Smoke Test (with kubeconfig cred)') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig-devops-mini', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            export KUBECONFIG="${KUBECONFIG_FILE}"
            kubectl apply -f k8s/namespace.yaml
            kubectl apply -f k8s/redis.yaml -n ${K8S_NAMESPACE}
            sed "s|PLACEHOLDER_TAG|${TAG}|g" k8s/app-deploy.yaml > k8s/app-deploy.rendered.yaml
            kubectl apply -f k8s/app-deploy.rendered.yaml -n ${K8S_NAMESPACE}
            kubectl rollout status deploy/flask-app -n ${K8S_NAMESPACE} --timeout=120s

            # in-cluster curl smoke test
            kubectl -n ${K8S_NAMESPACE} run curl --rm -it --image=curlimages/curl:8.7.1 --restart=Never -- \
              sh -lc 'for i in 1 2 3; do curl -s http://flask-svc:5000/ | grep -q \\"status\\":\\"ok\\" && echo ok || exit 1; sleep 2; done'
          '''
        }
      }
    }
  }

  post {
    success {
      withCredentials([file(credentialsId: 'kubeconfig-devops-mini', variable: 'KUBECONFIG_FILE')]) {
        sh '''
          export KUBECONFIG="${KUBECONFIG_FILE}"
          kubectl get pods,svc -n ${K8S_NAMESPACE}
        '''
      }
      echo "Deployed ${env.DOCKER_IMAGE}:${env.TAG} to ${env.K8S_NAMESPACE}"
    }
    failure {
      echo "Deployment failed. Try: kubectl rollout undo deploy/flask-app -n ${env.K8S_NAMESPACE}"
    }
  }
}
