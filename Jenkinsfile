pipeline {
  agent any
  options { timestamps(); skipDefaultCheckout(true) }

  environment {
    DOCKER_IMAGE  = 'charan1926/devops-mini'
    K8S_NAMESPACE = 'devops-mini'
    TAG           = ''
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.TAG = (env.GIT_COMMIT ? env.GIT_COMMIT.take(7) : '').trim()
          if (!env.TAG) {
            env.TAG = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD').trim()
          }
          if (!env.TAG) { error 'TAG is empty after checkout. Check SCM config.' }
          echo "Computed tag: ${env.TAG}"
        }
        echo "Building ${env.DOCKER_IMAGE}:${env.TAG} for namespace ${env.K8S_NAMESPACE}"
      }
    }

    stage('Sanity: tools') {
      steps {
        sh '''
          set -e
          docker --version
          kubectl version --client
          kubectl config current-context || true
        '''
      }
    }

    stage('Assert TAG') {
      steps {
        sh '''
          set -e
          [ -n "${TAG}" ] || { echo "ERROR: TAG is empty"; exit 1; }
          echo "TAG=${TAG}"
        '''
      }
    }

    stage('Build Image') {
      steps {
        sh '''
          set -e
          echo "Building ${DOCKER_IMAGE}:${TAG}"
          docker build -t ${DOCKER_IMAGE}:${TAG} .
          # also tag latest for human-friendly pulls
          docker tag ${DOCKER_IMAGE}:${TAG} ${DOCKER_IMAGE}:latest
        '''
      }
    }

    stage('Login & Push') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
          sh '''
            set -e
            echo "$PASS" | docker login -u "$USER" --password-stdin
            docker push ${DOCKER_IMAGE}:${TAG}
            docker push ${DOCKER_IMAGE}:latest
          '''
        }
      }
    }

    stage('Render Manifests') {
      steps {
        sh '''
          set -e
          # ensure both repo and tag are what we just built
          sed -e "s|PLACEHOLDER_IMAGE|${DOCKER_IMAGE}|g" \
              -e "s|PLACEHOLDER_TAG|${TAG}|g" \
              k8s/app-deploy.yaml > k8s/app-deploy.rendered.yaml
          echo "Rendered image -> ${DOCKER_IMAGE}:${TAG}"
          grep -E 'image:' k8s/app-deploy.rendered.yaml || true
        '''
      }
    }

    stage('Deploy to K8s') {
      steps {
        sh '''
          set -e
          # create/ensure namespace first, then wait
          kubectl apply -f k8s/namespace.yaml
          kubectl wait --for=condition=Established --timeout=30s namespace/${K8S_NAMESPACE} || true
          kubectl get ns ${K8S_NAMESPACE}

          kubectl apply -n ${K8S_NAMESPACE} -f k8s/redis.yaml
          kubectl apply -n ${K8S_NAMESPACE} -f k8s/app-deploy.rendered.yaml

          # adjust name if your Deployment differs from 'flask-app'
          kubectl rollout status deploy/flask-app -n ${K8S_NAMESPACE} --timeout=180s
        '''
      }
    }

    stage('Smoke Test (in-cluster)') {
      steps {
        sh '''
          set -e
          # no -it in CI; run-and-clean one-shot pod
          kubectl -n ${K8S_NAMESPACE} run curl --image=curlimages/curl:8.7.1 --restart=Never \
            --command -- sh -lc 'for i in 1 2 3; do curl -s http://flask-svc:5000/ | grep -q \\"status\\":\\"ok\\" && exit 0; sleep 2; done; exit 1'
          kubectl -n ${K8S_NAMESPACE} delete pod curl --ignore-not-found
        '''
      }
    }
  }

  post {
    success {
      sh '''
        set -e
        kubectl get pods,svc -n ${K8S_NAMESPACE}
      '''
      echo "Deployed ${env.DOCKER_IMAGE}:${env.TAG} to ${env.K8S_NAMESPACE}"
    }
    failure {
      echo "Deployment failed. If rollout created a new replicaset, try: kubectl rollout undo deploy/flask-app -n ${env.K8S_NAMESPACE}"
    }
  }
}
