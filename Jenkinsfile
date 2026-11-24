pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 10, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        APP_PORT = '3002'
    }

    stages {
        stage('Checkout') {
            steps {
                echo '=== CHECKOUT: ดึงโค้ดล่าสุดจาก GitHub ==='
                checkout scm
                sh 'git log -1 --pretty="%h %an: %s"'
            }
        }

        stage('Setup Python') {
            steps {
                echo '=== SETUP PYTHON: สร้าง venv และติดตั้ง dependency ==='
                sh '''
                    python3 --version
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                echo '=== LINT: ตรวจสไตล์โค้ดด้วย flake8 ==='
                sh '''
                    . .venv/bin/activate
                    flake8 .
                '''
            }
        }

        stage('Test') {
            steps {
                echo '=== TEST: รัน unit test + API test ==='
                sh '''
                    . .venv/bin/activate
                    pytest -v --junitxml=test-results.xml
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('Build') {
            steps {
                echo '=== BUILD: คอมไพล์ตรวจ syntax และแพ็กโค้ด ==='
                sh '''
                    . .venv/bin/activate
                    python -m py_compile todo.py storage.py app.py server.py
                '''
            }
        }

        stage('Deploy') {
            steps {
                echo '=== DEPLOY: จำลองการ deploy เว็บไปที่โฟลเดอร์ deploy/ ==='
                sh '''
                    rm -rf deploy && mkdir -p deploy/static
                    cp todo.py storage.py app.py server.py deploy/
                    cp static/index.html deploy/static/

                    cd deploy
                    # เปิดเซิร์ฟเวอร์จริงชั่วคราวเพื่อทำ smoke test
                    python3 server.py --port "$APP_PORT" --host 127.0.0.1 --file smoke.json > server.log 2>&1 &
                    echo $! > server.pid
                    ok=0
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fs "http://127.0.0.1:$APP_PORT/health" > health.json; then ok=1; break; fi
                        sleep 1
                    done
                    if [ "$ok" != "1" ]; then cat server.log; kill $(cat server.pid) || true; exit 1; fi
                    cat health.json; echo

                    curl -fs -X POST -H 'Content-Type: application/json' \
                         -d '{"title":"smoke test","priority":"high"}' \
                         "http://127.0.0.1:$APP_PORT/api/tasks"; echo
                    curl -fs "http://127.0.0.1:$APP_PORT/api/stats"; echo

                    kill $(cat server.pid) || true
                    rm -f server.pid smoke.json
                    cd ..
                    tar czf todo-app.tar.gz -C deploy .
                '''
                archiveArtifacts artifacts: 'todo-app.tar.gz', fingerprint: true
            }
        }
    }

    post {
        success { echo 'Pipeline สำเร็จ: Build, Test, Deploy ผ่านทั้งหมด' }
        failure { echo 'Pipeline ล้มเหลว: ดู Console Output เพื่อตรวจสอบ' }
        always  { sh 'rm -rf .venv || true' }
    }
}
