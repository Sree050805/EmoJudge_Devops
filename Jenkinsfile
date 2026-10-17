pipeline {
    agent any

    environment {
        PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Source code checked out from GitHub'
            }
        }

        stage('Docker Build') {
            steps {
                echo 'Building EmoJudge Docker images'
                sh 'docker compose build'
            }
        }

        stage('Docker Run') {
            steps {
                echo 'Starting EmoJudge containers'
                sh 'docker compose down || true'
                sh 'docker compose up -d'
            }
        }

        stage('Verify Containers') {
            steps {
                echo 'Checking EmoJudge containers'
                sh 'docker compose ps'
            }
        }

        stage('Health Check') {
            steps {
                echo 'Checking EmoJudge services'
                sh '''
                    sleep 10
                    curl -f http://127.0.0.1:5000/health
                    curl -f http://127.0.0.1:8000/health
                '''
            }
        }
    }

    post {
        success {
            echo 'EmoJudge Week-7 Jenkins pipeline completed successfully!'
        }

        failure {
            echo 'Pipeline failed. Check Jenkins console output.'
        }
    }
}