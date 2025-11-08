pipeline {
  agent any
  options { timestamps(); skipDefaultCheckout(true) }

  environment {
    DOCKER_IMAGE  = 'charan1926/devops-mini'   // your Docker Hub repo
    K8S_NAMESPACE = 'devops-mini'              // target namespace
    TAG           = ''                         // set after checkout
  }

  stages {
    stage('Checkout') {
      steps {
        script {
          // checkout and use Jenkins-provided commit SHA (no git CLI dependency)
          def scmVars = checkout scm
          env.TAG = (scmVars?.GIT_COMMIT ?: env.GIT_COMMIT ?: '').take(7)
          if (!env.TAG?.trim()) { error 'TAG is empty after checkout. Fix SCM config.' }
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
          # Replace placeholders in your base manifest
          sed -e "s|PLACEHOLDER_IMAGE|${DOCKER_IMAGE}|g" \
              -e "s|PLACEHOLDER_TAG|${TAG}|g" \
              k8s/app-deploy.yaml > k8s/app-deploy.rendered.yaml
          echo "Rendered image -> ${DOCKER_IMAGE}:${TAG}"
          grep -E '^\\s*image:' k8s/app-deploy.rendered.yaml || true
        '''
      }
    }

    stage('Deploy to K8s') {
      steps {
        sh '''
          set -e
          # Ensure namespace exists and is usable
          kubectl apply -f k8s/namespace.yaml
          # best-effort wait (Established condition may not be set everywhere)
          for i in 1 2 3; do kubectl get ns ${K8S_NAMESPACE} && break || sleep 2; done

          kubectl apply -n ${K8S_NAMESPACE} -f k8s/redis.yaml
          kubectl apply -n ${K8S_NAMESPACE} -f k8s/app-deploy.rendered.yaml

          # adjust 'flask-app' if your Deployment metadata.name differs
          kubectl rollout status deploy/flask-app -n ${K8S_NAMESPACE} --timeout=180s
        '''
      }
    }

    stage('Smoke Test (in-cluster)') {
      steps {
        sh '''
          set -e
          # no -it; run a one-shot curl pod and clean it up
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
      echo "Deployment failed. If a new ReplicaSet was created, try: kubectl rollout undo deploy/flask-app -n ${env.K8S_NAMESPACE}"
    }
  }
}
